"""mini-swe-agent model class that authenticates via Claude Code OAuth bearer token."""

import json
import logging
import os
import time
from typing import Any, Literal

import requests
from pydantic import BaseModel

from minisweagent.models import GLOBAL_MODEL_STATS
from minisweagent.models.utils.actions_toolcall import (
    BASH_TOOL,
    format_toolcall_observation_messages,
    parse_toolcall_actions,
)
from minisweagent.models.utils.openai_multimodal import expand_multimodal_content

# ~16K tokens at ~4 chars/token
MAX_TOOL_OUTPUT_CHARS = 64_000
TOOL_OUTPUT_TOO_LARGE_WARNING = (
    "[WARNING] Tool output too large (exceeded {n_chars} characters). "
    "The output has been suppressed to avoid blowing up the context window. "
    "Please try a different approach that produces less output — "
    "for example, redirect to a file and inspect only the parts you need, "
    "or use head/tail/grep to limit the output."
)
from minisweagent.models.utils.retry import retry

logger = logging.getLogger("anthropic_oauth_model")

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_BETA_OAUTH = "oauth-2025-04-20"
CLAUDE_CODE_IDENTITY = "You are Claude Code, Anthropic's official CLI for Claude."


class AnthropicOAuthModelConfig(BaseModel):
    model_name: str
    model_kwargs: dict[str, Any] = {}
    cost_tracking: Literal["default", "ignore_errors"] = "ignore_errors"
    format_error_template: str = "{{ error }}"
    observation_template: str = (
        "{% if output.exception_info %}<exception>{{output.exception_info}}</exception>\n{% endif %}"
        "<returncode>{{output.returncode}}</returncode>\n<output>\n{{output.output}}</output>"
    )
    multimodal_regex: str = ""
    max_tokens: int = 16384
    anthropic_version: str = "2023-06-01"
    set_cache_control: Literal["default_end"] | None = None  # accepted+ignored — for compat with get_model defaults


class AnthropicOAuthAuthError(Exception):
    pass


class AnthropicOAuthAPIError(Exception):
    pass


class AnthropicOAuthContextError(Exception):
    """Non-retryable: prompt too long or request too large."""
    pass


class _DictToObj:
    """Duck-type wrapper so `parse_toolcall_actions` (which expects OpenAI-shape
    `tc.function.name` / `tc.function.arguments`) accepts our reshaped tool calls."""

    def __init__(self, d: dict):
        self.id = d.get("id")
        self.function = _DictToObj(d["function"]) if isinstance(d.get("function"), dict) else None
        self.name = d.get("name")
        self.arguments = d.get("arguments")


def _flatten_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
    return str(content)


def _to_anthropic_request(messages: list[dict]) -> tuple[str, list[dict]]:
    """Convert OpenAI-shape messages -> (system_text, anthropic_messages)."""
    system_text = ""
    out: list[dict] = []
    for m in messages:
        role = m.get("role")
        content = m.get("content", "")
        if role == "system":
            system_text = _flatten_content(content)
            continue
        if role == "tool":
            block = {
                "type": "tool_result",
                "tool_use_id": m["tool_call_id"],
                "content": _flatten_content(content),
            }
            if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list):
                out[-1]["content"].append(block)
            else:
                out.append({"role": "user", "content": [block]})
            continue
        if role == "user":
            out.append({"role": "user", "content": _flatten_content(content)})
            continue
        if role == "assistant":
            blocks: list[dict] = []
            text = _flatten_content(content)
            if text:
                blocks.append({"type": "text", "text": text})
            for tc in m.get("tool_calls") or []:
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "input": json.loads(tc["function"]["arguments"]),
                    }
                )
            out.append({"role": "assistant", "content": blocks if blocks else ""})
    return system_text, out


def _from_anthropic_response(data: dict) -> dict:
    """Convert an Anthropic Messages API response into OpenAI-shape dict."""
    text_parts = []
    tool_calls = []
    for block in data.get("content", []):
        if block.get("type") == "text":
            text_parts.append(block.get("text", ""))
        elif block.get("type") == "tool_use":
            tool_calls.append(
                {
                    "id": block.get("id"),
                    "type": "function",
                    "function": {
                        "name": block.get("name"),
                        "arguments": json.dumps(block.get("input", {})),
                    },
                }
            )
    msg = {"role": "assistant", "content": "\n".join(text_parts), "tool_calls": tool_calls}
    return {"choices": [{"message": msg}], "usage": data.get("usage", {})}


def _bash_tool_anthropic() -> list[dict]:
    """Single-tool surface in Anthropic's input_schema format (bash only)."""
    return [{
        "name": BASH_TOOL["function"]["name"],
        "description": BASH_TOOL["function"]["description"],
        "input_schema": BASH_TOOL["function"]["parameters"],
    }]


class AnthropicOAuthModel:
    abort_exceptions: list[type[Exception]] = [AnthropicOAuthAuthError, AnthropicOAuthContextError, KeyboardInterrupt]

    def __init__(self, *, config_class: type = AnthropicOAuthModelConfig, **kwargs):
        self.config = config_class(**kwargs)
        primary = os.getenv("CLAUDE_CODE_OAUTH_TOKEN", "").strip()
        if not primary:
            raise AnthropicOAuthAuthError(
                "CLAUDE_CODE_OAUTH_TOKEN env var is empty; expected the accessToken from "
                "~/.claude/.credentials.json. Refresh with `claude -p ok` if expired."
            )
        fallback_str = os.getenv("CLAUDE_CODE_OAUTH_TOKEN_FALLBACK", "").strip()
        fallbacks = [t for t in (t.strip() for t in fallback_str.split(",")) if t]
        # _tokens[0] is always the active token; rotate on 401.
        self._tokens: list[str] = [primary] + fallbacks
        self._token_idx: int = 0
        self._token: str = primary

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "anthropic-version": self.config.anthropic_version,
            "anthropic-beta": ANTHROPIC_BETA_OAUTH,
        }

    def _query(self, messages: list[dict], **kwargs) -> dict:
        system_text, anthropic_messages = _to_anthropic_request(messages)
        # OAuth requires the Claude Code identity as the FIRST system block; the task's
        # actual system content goes in a second block.
        system_blocks = [{"type": "text", "text": CLAUDE_CODE_IDENTITY}]
        if system_text:
            system_blocks.append({"type": "text", "text": system_text})
        payload = {
            "model": self.config.model_name,
            "max_tokens": self.config.max_tokens,
            "system": system_blocks,
            "messages": anthropic_messages,
            "tools": _bash_tool_anthropic(),
            **(self.config.model_kwargs | kwargs),
        }
        try:
            # LAUNCHPAD_INSECURE=1 skips TLS verification (e.g. corporate proxies
            # with a self-signed CA). Also silences the InsecureRequestWarning.
            verify = not bool(os.getenv("LAUNCHPAD_INSECURE"))
            if not verify:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            r = requests.post(ANTHROPIC_API_URL, headers=self._headers(), data=json.dumps(payload), timeout=180, verify=verify)
        except requests.exceptions.RequestException as e:
            raise AnthropicOAuthAPIError(f"Request failed: {e}") from e
        if r.status_code == 401:
            next_idx = self._token_idx + 1
            if next_idx < len(self._tokens):
                self._token_idx = next_idx
                self._token = self._tokens[next_idx]
                logger.warning(
                    "401 on token[%d]; rotating to token[%d] of %d",
                    next_idx - 1, next_idx, len(self._tokens),
                )
                return self._query(messages, **kwargs)
            raise AnthropicOAuthAuthError(
                f"401 from Anthropic (all {len(self._tokens)} token(s) exhausted): {r.text[:400]}"
            )
        if r.status_code in (400, 413):
            raise AnthropicOAuthContextError(f"HTTP {r.status_code}: {r.text[:800]}")
        if r.status_code >= 400:
            raise AnthropicOAuthAPIError(f"HTTP {r.status_code}: {r.text[:800]}")
        return _from_anthropic_response(r.json())

    def _prepare_messages_for_api(self, messages: list[dict]) -> list[dict]:
        return [{k: v for k, v in m.items() if k != "extra"} for m in messages]

    def query(self, messages: list[dict], **kwargs) -> dict:
        for attempt in retry(logger=logger, abort_exceptions=self.abort_exceptions):
            with attempt:
                response = self._query(self._prepare_messages_for_api(messages), **kwargs)
        cost = 0.0
        GLOBAL_MODEL_STATS.add(cost)
        message = dict(response["choices"][0]["message"])
        message["extra"] = {
            "actions": self._parse_actions(response),
            "response": response,
            "cost": cost,
            "timestamp": time.time(),
        }
        return message

    def _parse_actions(self, response: dict) -> list[dict]:
        tool_calls = response["choices"][0]["message"].get("tool_calls") or []
        return parse_toolcall_actions(
            [_DictToObj(tc) for tc in tool_calls],
            format_error_template=self.config.format_error_template,
        )

    def format_message(self, **kwargs) -> dict:
        return expand_multimodal_content(kwargs, pattern=self.config.multimodal_regex)

    def format_observation_messages(
        self, message: dict, outputs: list[dict], template_vars: dict | None = None
    ) -> list[dict]:
        for output in outputs:
            text = output.get("output", "")
            if len(text) > MAX_TOOL_OUTPUT_CHARS:
                output["output"] = TOOL_OUTPUT_TOO_LARGE_WARNING.format(n_chars=len(text))
        actions = message.get("extra", {}).get("actions", [])
        return format_toolcall_observation_messages(
            actions=actions,
            outputs=outputs,
            observation_template=self.config.observation_template,
            template_vars=template_vars,
            multimodal_regex=self.config.multimodal_regex,
        )

    def get_template_vars(self, **kwargs) -> dict[str, Any]:
        return self.config.model_dump()

    def serialize(self) -> dict:
        return {
            "info": {
                "config": {
                    "model": self.config.model_dump(mode="json"),
                    "model_type": f"{self.__class__.__module__}.{self.__class__.__name__}",
                },
            }
        }
