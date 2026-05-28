import concurrent.futures
import logging
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

import typer
import yaml
from rich.live import Live

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
from anthropic_oauth import AnthropicOAuthModel  # noqa: E402

from minisweagent.agents.default import DefaultAgent
from minisweagent.environments.docker import DockerEnvironment
from minisweagent.run.benchmarks.utils.batch_progress import RunBatchProgressManager

WORK_CWD = "/work"
BINARY_PATH = "/workspace/executable"
DOCTRINE_PATH = SCRIPTS_DIR.parent / "opus-experiment" / "CLAUDE.md"

logger = logging.getLogger(__name__)

app = typer.Typer(rich_markup_mode="rich", add_completion=False)

PAPER_SYSTEM_PROMPT = """You are a helpful assistant that can interact with a computer.

This is a reverse-engineering benchmark. You are given a compiled binary and its documentation.
Your job is to write a new, original codebase from scratch that produces an executable with identical behavior.
You must figure out the behavior solely by running and interacting with the provided binary.
Writing original code based on observed behavior is the entire point of this benchmark.

Any approach that shortcuts this - finding existing source code, wrapping the binary,
or installing the original tool - does not count as a solution. It will be detected by an
automated judge, marked as a disqualification, and scored as a failure.
The trace will be posted to an online wall of shame.

<RULES>
## What is not allowed

### 1. Obtaining source code

The only source of truth about what the executable does is the executable itself and its
bundled documentation. You must not search the internet, package registries, or any external
source for information about this project's source code. Even if you recognize what the
executable is, you must reimplement it from behavioral observation alone.

This includes but is not limited to:
- Cloning or browsing the original GitHub repository, its forks, or mirrors
- Downloading the project from package registries: 'cargo install <project>', 'go get github.com/<org>/<project>', 'pip install <project>',
   'apt-get source <project>', 'npm install <project>', etc.
- Fetching source tarballs from project websites (e.g., 'curl https://lua.org/ftp/lua-5.5.0.tar.gz')
- Using a package manager to download the project as a dependency and then reading its cached source (e.g., navigating
   into '~/.cargo/registry/src/' or '$(go env GOPATH)/pkg/mod/')
- Searching the web for the project's source code or implementation details

### 2. Wrapping or reusing the original binary

Your submission must be a genuine reimplementation. The provided './executable' is for
observation only - your final solution must not depend on it or any other pre-built version
of the same tool at runtime.

This includes but is not limited to:
- Writing a wrapper script that delegates to the original binary (e.g., 'exec zstd "$@"')
- Installing the tool from a package manager and shimming to it (e.g., 'apt-get install nnn && cp $(which nnn) ./executable')
- Writing a 'compile.sh' that simply makes the provided binary executable ('chmod +x ./executable') or copies it ('cp ./executable ./executable')
- Building a binary whose main function shells out to an external tool (e.g., 'Command::new("miniserve").args(args).exec()')
- Re-linking prebuilt '.o' object files found in the workspace without writing new source code

### 3. Binary analysis of the provided executable

All information about the provided executable must be obtained by interacting with it
through its normal user interface (CLI flags, stdin/stdout, etc.).
- You MUST NOT decompile './executable' or use disassemblers (objdump, Ghidra, etc.) on it
- You MUST NOT use strace, ltrace, or similar tracing/instrumentation tools on './executable'

Note: this restriction applies ONLY to the provided './executable'. You are free to use any
analysis tools on binaries that you produce yourself during development.

## What IS allowed

- Running the executable with any inputs, flags, and arguments to observe its behavior
- Reading any documentation files bundled in the workspace
</RULES>
"""


INSTANCE_PROMPT = f"""You are operating inside a Docker container with no internet access. The provided binary is at {BINARY_PATH} (read+execute only); its bundled documentation lives under /workspace/.

Begin by exploring the binary and the docs:

    ls -la /workspace/
    {BINARY_PATH} --help 2>&1; echo "EXIT:$?"
    {BINARY_PATH} --version 2>&1; echo "EXIT:$?"
    find /workspace/ -maxdepth 3 -type f \\( -name '*.md' -o -name '*.txt' -o -name '*.1' -o -name 'README*' -o -name 'USAGE*' \\)

Write your reimplementation under {WORK_CWD}/ — this is your scratch directory. When you finish, the contents of {WORK_CWD}/ get tarred and re-extracted into a fresh container at scoring time. compile.sh will then be invoked there from its own directory; use relative paths only (or `"$(dirname "$0")"`) — paths beginning with `{WORK_CWD}` will not resolve at scoring time.

Required output:

  - A `compile.sh` script at {WORK_CWD}/compile.sh.
  - compile.sh must produce a file named exactly `executable` in its current working directory when invoked.

Standard build tools (gcc, cargo, go, python3, ...) are available at scoring time. Match the original binary's CLI flags, output format, exit codes, and error messages as closely as possible.

When you are confident the submission is complete, run:

    echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT

as your sole bash command for that turn. After this command you cannot continue.
"""

_ENV_VARS = {"PAGER": "cat", "MANPAGER": "cat", "LESS": "-R", "PIP_PROGRESS_BAR": "off", "TQDM_DISABLE": "1"}


def _build_system_prompt(doctrine: bool) -> str:
    if not doctrine:
        return PAPER_SYSTEM_PROMPT
    if not DOCTRINE_PATH.exists():
        raise FileNotFoundError(f"doctrine file not found: {DOCTRINE_PATH}")
    return PAPER_SYSTEM_PROMPT + "\n\n---\n\n" + DOCTRINE_PATH.read_text()


def _docker_pull(image: str) -> None:
    r = subprocess.run(["docker", "pull", image], capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"docker pull failed: {r.stderr or r.stdout}")


def _make_env(instance_id: str, *, cmd_timeout: int):
    image = f"programbench/{instance_id.replace('__', '_1776_')}:task_cleanroom"
    _docker_pull(image)
    env = DockerEnvironment(
        image=image,
        cwd=WORK_CWD,
        run_args=["--rm", "--network", "none"],
        env=_ENV_VARS,
        timeout=cmd_timeout,
    )
    env.config.timeout = cmd_timeout
    return env


def _extract_submission(env, out_dir: Path) -> Path:
    work_host = out_dir / "work"
    if work_host.exists():
        shutil.rmtree(work_host)
    work_host.mkdir(parents=True)
    r = subprocess.run(
        ["docker", "cp", f"{env.container_id}:{WORK_CWD}/.", str(work_host)],
        capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0:
        raise RuntimeError(f"docker cp failed: {r.stderr or r.stdout}")
    (work_host / "executable").unlink(missing_ok=True)
    sub = out_dir / "submission.tar.gz"
    r = subprocess.run(["tar", "-czf", str(sub), "-C", str(work_host), "."], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"tar failed: {r.stderr or r.stdout}")
    return sub


class _ProgressAgent(DefaultAgent):
    def __init__(self, *args, progress: RunBatchProgressManager | None, instance_id: str, **kwargs):
        super().__init__(*args, **kwargs)
        self._progress = progress
        self._instance_id = instance_id

    def step(self) -> dict:
        if self._progress is not None:
            self._progress.update_instance_status(self._instance_id, f"Step {self.n_calls + 1:3d} (${self.cost:.2f})")
        return super().step()


def _run_instance(
    instance_id: str, output_dir: Path, model: str,
    step_limit: int, cost_limit: float, cmd_timeout: int,
    system_prompt: str,
    progress: RunBatchProgressManager | None,
):
    out_dir = output_dir / instance_id
    out_dir.mkdir(parents=True, exist_ok=True)
    traj_path = out_dir / "trajectory.json"
    if traj_path.exists():
        print(f"[skip] {instance_id}: already complete", flush=True)
        return

    if progress is not None:
        progress.on_instance_start(instance_id)
        progress.update_instance_status(instance_id, "Starting environment")

    env = _make_env(instance_id, cmd_timeout=cmd_timeout)
    boot = env.execute({"command": f"mkdir -p {WORK_CWD} && cd {WORK_CWD} && pwd"})
    if boot["returncode"] != 0:
        raise RuntimeError(f"workspace bootstrap failed: {boot}")

    agent = _ProgressAgent(
        AnthropicOAuthModel(model_name=model), env,
        progress=progress, instance_id=instance_id,
        system_template=system_prompt, instance_template=INSTANCE_PROMPT,
        step_limit=step_limit, cost_limit=cost_limit, output_path=traj_path,
    )

    t0 = time.time()
    exit_status = ""
    submission = ""
    extra_info: dict = {}
    try:
        info = agent.run(task=f"ProgramBench reverse-engineering task: {instance_id}")
        exit_status = info.get("exit_status", "")
        submission = info.get("submission", "")
    except Exception as e:
        print(f"[error] {instance_id}: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        exit_status = type(e).__name__
        extra_info = {"traceback": traceback.format_exc(), "exception_str": str(e)}
    finally:
        wall = time.time() - t0
        print(f"[done] {instance_id} exit_status={exit_status!r} wall={wall:.1f}s steps={agent.n_calls}", flush=True)
        try:
            sub = _extract_submission(env, out_dir)
            print(f"[submission] {sub}", flush=True)
        except Exception as e:
            print(f"[submission-error] {instance_id}: {e}", file=sys.stderr, flush=True)
            extra_info.setdefault("submission_error", str(e))
        agent.save(traj_path, {"info": {
            "exit_status": exit_status, "submission": submission,
            "instance_id": instance_id, "wall_seconds": wall,
            **extra_info,
        }})
        print(f"[trajectory] {traj_path}", flush=True)
        env.cleanup()
        if progress is not None:
            progress.on_instance_end(instance_id, exit_status)


@app.command()
def main(
    output_dir: Path = typer.Option(..., "-o", "--output-dir"),
    config: Path = typer.Option(None, "-c", "--config"),
    model: str = typer.Option(None, "-m", "--model"),
    instance_id: str = typer.Option(None, "--instance-id"),
    workers: int = typer.Option(1, "-w", "--workers"),
    step_limit: int = typer.Option(1000, "--step-limit"),
    cost_limit: float = typer.Option(0.0, "--cost-limit"),
    cmd_timeout: int = typer.Option(120, "--cmd-timeout"),
    doctrine: bool = typer.Option(True, "--doctrine/--no-doctrine"),
):
    if instance_id and config:
        raise typer.BadParameter("Pass --instance-id or --config, not both.")

    cfg: dict = {}
    if config:
        cfg = yaml.safe_load(config.read_text()) or {}

    if instance_id:
        ids = [instance_id]
    elif cfg.get("instance_ids"):
        ids = cfg["instance_ids"]
    else:
        raise typer.BadParameter("Provide --instance-id, --config, or a config with instance_ids.")

    model = model or cfg.get("model") or "claude-opus-4-7"
    system_prompt = _build_system_prompt(doctrine=doctrine)

    output_dir.mkdir(parents=True, exist_ok=True)

    if len(ids) == 1 and workers <= 1:
        _run_instance(ids[0], output_dir, model, step_limit, cost_limit, cmd_timeout, system_prompt, progress=None)
        return

    progress = RunBatchProgressManager(len(ids), output_dir / f"exit_statuses_{time.time()}.yaml")
    with Live(progress.render_group, refresh_per_second=4):
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    _run_instance, iid, output_dir, model,
                    step_limit, cost_limit, cmd_timeout, system_prompt, progress,
                ): iid
                for iid in ids
            }
            try:
                for future in concurrent.futures.as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        progress.on_uncaught_exception(futures[future], e)
            except KeyboardInterrupt:
                for f in futures:
                    if not f.running() and not f.done():
                        f.cancel()


if __name__ == "__main__":
    app()
