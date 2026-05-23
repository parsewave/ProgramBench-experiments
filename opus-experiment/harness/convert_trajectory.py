#!/usr/bin/env python3
"""
convert_trajectory.py -- LOSSY adapter from Claude Code's stream-json
`trajectory.jsonl` (one event per line) to a mini-swe-agent-shaped
`trajectory.json` ({"info": {...}, "messages": [...]}).

Purpose
-------
Downstream analysis tools written for the Kimi K2.6 trace-gen pipeline
(`filter_traces.py`, `behavior_flags.py`, ...) expect mini-swe-agent's
nested `trajectory.json` layout. The CC harness writes line-delimited
stream-json instead. Rather than rewrite every analysis tool, this script
emits a minimally-shaped `trajectory.json` next to the jsonl so that
`find ... -name trajectory.json` succeeds and analysis scripts don't crash
on missing files.

Caveats / what is lost
----------------------
This is NOT a faithful conversion. Many things are simplified or dropped:
- Tool-result truncation rules, exact step boundaries, and the
  mini-swe-agent-specific `step_idx` numbering are best-effort.
- The system prompt is not reconstructed (CC streams it differently than
  mini does; we leave it as an empty string in `info`).
- Tool-call arguments and tool-result content are passed through as JSON
  blobs; mini's analysis tools may stringify them differently.
- Cost / token-usage fields from CC are surfaced into `info` when present
  but the schema does not match mini's exactly.

A proper converter is future work. Treat the produced JSON as
"good enough so downstream scripts run, not good enough to do real
trajectory analysis on".

Usage
-----
    convert_trajectory.py <input.jsonl> <output.json>

Always exits 0 (best-effort); writes a stub with `{"info": {"error": ...},
"messages": []}` if the input is unreadable so the file at least exists.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def _content_to_str(content: Any) -> Any:
    """Pass content through. CC content is sometimes a string, sometimes a
    list of typed blocks (text/tool_use/tool_result). Mini expects strings
    for simple messages and lists for tool messages; passing through
    preserves enough structure for the analysis tools we care about."""
    return content


def convert(input_path: Path, output_path: Path) -> None:
    info: dict[str, Any] = {
        "source": "claude-code-stream-json",
        "converter": "convert_trajectory.py (lossy)",
        "input_file": str(input_path),
    }
    messages: list[dict[str, Any]] = []

    if not input_path.exists():
        info["error"] = f"input file not found: {input_path}"
        output_path.write_text(json.dumps({"info": info, "messages": messages}, indent=2))
        return

    try:
        raw_lines = input_path.read_text(errors="replace").splitlines()
    except OSError as e:
        info["error"] = f"could not read input: {e}"
        output_path.write_text(json.dumps({"info": info, "messages": messages}, indent=2))
        return

    init_event: dict[str, Any] | None = None
    result_event: dict[str, Any] | None = None

    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            # skip malformed events rather than abort
            continue

        ev_type = ev.get("type")

        if ev_type == "system" and ev.get("subtype") == "init":
            init_event = ev
            continue

        if ev_type == "result":
            result_event = ev
            continue

        if ev_type in ("assistant", "user"):
            inner = ev.get("message") or {}
            role = inner.get("role") or ev_type
            content = inner.get("content")
            msg: dict[str, Any] = {
                "role": role,
                "content": _content_to_str(content),
            }
            # Surface tool_calls / tool_use shape if present for analyzers
            # that look for it.
            if isinstance(content, list):
                tool_calls = [
                    b for b in content
                    if isinstance(b, dict) and b.get("type") == "tool_use"
                ]
                if tool_calls:
                    msg["tool_calls"] = tool_calls
            messages.append(msg)
            continue

        # Any other event type -- skip silently. (CC emits a "stream_event"
        # type for partial deltas which we don't want in messages.)

    if init_event is not None:
        info["init"] = {
            "model": init_event.get("model"),
            "session_id": init_event.get("session_id"),
            "cwd": init_event.get("cwd"),
            "tools": init_event.get("tools"),
        }
    if result_event is not None:
        info["result"] = {
            "subtype": result_event.get("subtype"),
            "is_error": result_event.get("is_error"),
            "num_turns": result_event.get("num_turns"),
            "duration_ms": result_event.get("duration_ms"),
            "total_cost_usd": result_event.get("total_cost_usd"),
            "usage": result_event.get("usage"),
            "result": result_event.get("result"),
        }
        # Common mini-swe-agent field names some analyzers look for:
        info["exit_status"] = "submitted" if not result_event.get("is_error") else "error"
        info["n_steps"] = result_event.get("num_turns")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"info": info, "messages": messages}, indent=2))


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        convert(Path(sys.argv[1]), Path(sys.argv[2]))
    except Exception as e:  # noqa: BLE001 -- best-effort
        # Even if conversion fully fails, leave a stub file so downstream
        # tools don't trip over a missing trajectory.json.
        try:
            Path(sys.argv[2]).write_text(json.dumps({
                "info": {"error": f"converter crashed: {e!r}"},
                "messages": [],
            }))
        except OSError:
            pass
        # Still return 0 -- this is a best-effort step in run_task.sh.
    return 0


if __name__ == "__main__":
    sys.exit(main())
