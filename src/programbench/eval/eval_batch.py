# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""Batch evaluation of instances.

IMPORTANT NOTE FOR AI AGENTS
THIS IS A very delicate file.
You need to be extremely conservative and careful about testing logic.
The worst case to avoid here is that there are issues with testing but the result
still indicates that the solution is correct. This might for example happen if you
skip something because of some error condition and only show a warning, but it's not apparent
from the output file that something went wrong.
It's always better to clearly mark a failure in the output file than to silently skip something.
Be extremely proactive with the user about clearing up details and intricacies with how to handle
something here. Ask a lot of questions and don't be afraid to ask for clarification.
Do not remove this notice.
"""

import json
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, computed_field
from rich.console import Console, Group
from rich.table import Table
from rich.text import Text
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from programbench.constants import DOCKER_CPUS
from programbench.eval.eval import EvaluationResult, Evaluator
from programbench.utils.instance_filters import filter_instances

log = logging.getLogger(__name__)


def _round_seconds(value: float) -> float:
    return round(value, 3)


def _timing_summary_from_result(instance_id: str, result: EvaluationResult) -> dict:
    by_step: dict[str, float] = defaultdict(float)
    counts_by_step: dict[str, int] = defaultdict(int)
    by_branch: dict[str, float] = defaultdict(float)

    total = 0.0
    for entry in result.log:
        wall_time = entry.get("wall_time")
        if not isinstance(wall_time, (int, float)):
            continue
        wall_time = float(wall_time)
        step = str(entry.get("step") or "unknown")
        total += wall_time
        by_step[step] += wall_time
        counts_by_step[step] += 1
        branch = entry.get("branch")
        if branch:
            by_branch[str(branch)] += wall_time

    slowest_branches = sorted(
        ({"branch": branch, "wall_time": _round_seconds(wall)} for branch, wall in by_branch.items()),
        key=lambda item: item["wall_time"],
        reverse=True,
    )
    return {
        "instance_id": instance_id,
        "score": result.score,
        "error_code": result.error_code,
        "test_branch_errors": {
            branch: [error.error_code for error in errors] for branch, errors in result.test_branch_errors.items()
        },
        "n_tests": len(result),
        "n_resolved": result.n_resolved,
        "total_logged_wall_time": _round_seconds(total),
        "by_step": {step: _round_seconds(by_step[step]) for step in sorted(by_step)},
        "counts_by_step": dict(sorted(counts_by_step.items())),
        "slowest_branches": slowest_branches[:10],
    }


def _write_timing_summary(target_dir: Path, summaries: list["InstanceEvalSummary"]) -> Path | None:
    instance_summaries: list[dict] = []
    overall_by_step: dict[str, float] = defaultdict(float)
    overall_counts_by_step: dict[str, int] = defaultdict(int)

    for summary in sorted(summaries, key=lambda s: s.instance_id):
        eval_json = target_dir / summary.instance_id / f"{summary.instance_id}.eval.json"
        if not eval_json.exists():
            continue
        try:
            result = EvaluationResult.model_validate_json(eval_json.read_text())
        except Exception:
            log.warning("Skipping timing summary for malformed eval JSON: %s", eval_json, exc_info=True)
            continue
        timing = _timing_summary_from_result(summary.instance_id, result)
        instance_summaries.append(timing)
        for step, wall_time in timing["by_step"].items():
            overall_by_step[step] += float(wall_time)
        for step, count in timing["counts_by_step"].items():
            overall_counts_by_step[step] += int(count)

    if not instance_summaries:
        return None

    total = sum(float(item["total_logged_wall_time"]) for item in instance_summaries)
    payload = {
        "target_dir": str(target_dir),
        "instances": len(instance_summaries),
        "total_logged_wall_time": _round_seconds(total),
        "overall_by_step": {step: _round_seconds(overall_by_step[step]) for step in sorted(overall_by_step)},
        "overall_counts_by_step": dict(sorted(overall_counts_by_step.items())),
        "slowest_instances": sorted(
            (
                {
                    "instance_id": item["instance_id"],
                    "total_logged_wall_time": item["total_logged_wall_time"],
                    "score": item["score"],
                    "error_code": item["error_code"],
                }
                for item in instance_summaries
            ),
            key=lambda item: item["total_logged_wall_time"],
            reverse=True,
        ),
        "per_instance": instance_summaries,
    }
    path = target_dir / "eval-timing-summary.json"
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path


class InstanceEvalSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instance_id: str
    score: float
    n_resolved: int
    n_tests: int
    error_code: str | None = None
    test_branch_errors: dict[str, list[str]] = {}
    n_system_errors: int = 0
    n_warnings: int = 0
    solution_branch: str | None = None
    test_branches: list[str] = []

    @classmethod
    def from_eval_result(cls, instance_id: str, result: EvaluationResult) -> Self:
        return cls(
            instance_id=instance_id,
            score=result.score,
            n_resolved=result.n_resolved,
            n_tests=len(result),
            error_code=result.error_code,
            test_branch_errors={b: [e.error_code for e in errors] for b, errors in result.test_branch_errors.items()},
            n_system_errors=result.n_system_errors,
            n_warnings=len(result.warnings),
            solution_branch=result.solution_branch,
            test_branches=result.test_branches,
        )


class BatchEvalSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summaries: list[InstanceEvalSummary]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_instances(self) -> int:
        return len(self.summaries)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def average_pass_rate(self) -> float:
        if not self.summaries:
            return 0.0
        return sum(s.score for s in self.summaries) / len(self.summaries)

    def summary(self) -> Group:
        table = Table(title="Evaluation Summary", show_lines=False, box=None)
        table.add_column("Instance", style="bold")
        table.add_column("Score", justify="right")
        table.add_column("Comment")

        for s in sorted(self.summaries, key=lambda s: s.instance_id):
            score_style = "green" if s.score == 1.0 else "yellow" if s.score > 0 else "red"
            if s.error_code:
                comment = Text(f"ERROR: {s.error_code}", style="bold red")
            elif s.test_branch_errors or s.n_system_errors or s.n_warnings:
                parts = []
                if s.test_branch_errors:
                    parts.append("BRANCH: " + ", ".join(f"{b}: {','.join(e)}" for b, e in s.test_branch_errors.items()))
                if s.n_system_errors:
                    parts.append(f"SYSTEM: {s.n_system_errors}")
                if s.n_warnings:
                    parts.append(f"WARN: {s.n_warnings}")
                comment = Text("ERRORS: " + "; ".join(parts), style="bold red")
            else:
                comment = Text(f"{s.n_tests} tests")
            score_text = (
                Text("✅", style=score_style) if s.score == 1.0 else Text(f"{s.score * 100:.0f}", style=score_style)
            )
            table.add_row(s.instance_id, score_text, comment)

        table.add_section()
        table.add_row(
            "Average",
            Text(f"{self.average_pass_rate * 100:.0f}", style="bold"),
            f"{self.total_instances} instances",
        )
        note = Text(
            "Note: A score of 100 does not mean solved (due to rounding). Only ✅ indicates a solved task.",
            style="dim",
        )
        return Group(table, note)


def _can_reprocess(result: EvaluationResult) -> bool:
    if result.error_code:
        return True
    tagged = {e["branch"] for e in result.log if e.get("step") == "results_read" and "branch" in e}
    non_error_branches = {b for b in result.test_branches if b not in result.test_branch_errors}
    return non_error_branches <= tagged


def _summary_from_existing(
    instance_id: str,
    eval_json: Path,
    ignored: set[str],
    current_branches: list[str] | None = None,
    tests_by_branch: dict[str, list[str]] | None = None,
    ignored_branches: set[str] | None = None,
) -> InstanceEvalSummary:
    """Build an InstanceEvalSummary from an existing eval JSON file."""
    result = EvaluationResult.model_validate_json(eval_json.read_text())
    if tests_by_branch is not None and _can_reprocess(result):
        evaluator = Evaluator(
            tests_branches=result.test_branches,
            tests_by_branch=tests_by_branch,
            ignored_tests=ignored,
            ignored_branches=ignored_branches,
            from_existing=result,
        )
        result = evaluator.run()
        eval_json.write_text(result.model_dump_json(indent=2))
    if current_branches is not None:
        result = result.for_branches(current_branches)
    filtered = result.without_ignored(ignored)
    return InstanceEvalSummary.from_eval_result(instance_id, filtered)


def get_branches_to_eval(
    *,
    eval_json: Path,
    all_test_branches: list[str],
    tests_by_branch: dict[str, list[str]],
    ignored_tests: set[str],
) -> list[str]:
    """Return the list of test branches that need (re-)evaluation."""
    if not eval_json.exists():
        return all_test_branches
    existing = EvaluationResult.model_validate_json(eval_json.read_text())
    if not existing.test_branches or existing.error_code:
        return all_test_branches
    existing_branch_set = set(existing.test_branches)
    needs_eval: list[str] = []
    for branch in all_test_branches:
        if branch not in existing_branch_set or branch in existing.test_branch_errors:
            needs_eval.append(branch)
            continue
        expected = tests_by_branch.get(branch, [])
        active_expected = [t for t in expected if f"{branch}/{t}" not in ignored_tests]
        present = {t.name for t in existing.test_results if t.branch == branch and t.status != "not_run"}
        if any(t not in present for t in active_expected):
            needs_eval.append(branch)
    return needs_eval


def _summarize_instance(
    *,
    instance_id: str,
    instance: dict,
    target_dir: Path,
) -> InstanceEvalSummary | None:
    """Rebuild an InstanceEvalSummary from existing eval results without re-running tests."""
    from programbench.utils.load_data import get_active_branches, get_ignored_branches, get_ignored_tests

    eval_json = target_dir / instance_id / f"{instance_id}.eval.json"
    if not eval_json.exists():
        log.warning("Skipping %s (no eval.json)", instance_id)
        return None
    all_test_branches = get_active_branches(instance)
    branches_data = instance.get("branches", {})
    tests_by_branch = {b: branches_data[b]["tests"] for b in all_test_branches if b in branches_data}
    try:
        return _summary_from_existing(
            instance_id,
            eval_json,
            get_ignored_tests(instance),
            current_branches=all_test_branches,
            tests_by_branch=tests_by_branch,
            ignored_branches=get_ignored_branches(instance),
        )
    except Exception as e:
        log.error("Error summarizing %s: %s", instance_id, e, exc_info=True)
        return InstanceEvalSummary(
            instance_id=instance_id,
            score=0.0,
            n_resolved=0,
            n_tests=0,
            error_code=type(e).__name__,
            test_branches=all_test_branches,
        )


def _evaluate_instance(
    *,
    instance_id: str,
    instance: dict,
    source_dir: Path,
    target_dir: Path,
    force: bool,
    image_tag: str = "task",
    docker_cpus: int = DOCKER_CPUS,
    branch_workers: int = 1,
    branch_retries: int = 1,
) -> InstanceEvalSummary | None:
    """Evaluate a single instance."""
    from programbench.utils.load_data import get_active_branches, get_ignored_branches, get_ignored_tests

    all_test_branches = get_active_branches(instance)
    if not all_test_branches:
        log.warning("Skipping %s (no test_branches configured)", instance_id)
        return None

    ignored = get_ignored_tests(instance)
    ignored_branches = get_ignored_branches(instance)
    eval_json = target_dir / instance_id / f"{instance_id}.eval.json"

    branches_data = instance.get("branches", {})
    all_tests_by_branch = {
        branch: branches_data[branch]["tests"] for branch in all_test_branches if branch in branches_data
    }

    existing_result: EvaluationResult | None = None
    branches_to_eval = all_test_branches

    if not force:
        branches_to_eval = get_branches_to_eval(
            eval_json=eval_json,
            all_test_branches=all_test_branches,
            tests_by_branch=all_tests_by_branch,
            ignored_tests=ignored,
        )
        if not branches_to_eval:
            log.info("Skipping %s (fully evaluated, use --force to re-run)", instance_id)
            return _summary_from_existing(
                instance_id,
                eval_json,
                ignored,
                current_branches=all_test_branches,
                tests_by_branch=all_tests_by_branch,
                ignored_branches=ignored_branches,
            )
        if eval_json.exists():
            existing_result = EvaluationResult.model_validate_json(eval_json.read_text())
            if existing_result.test_branches and not existing_result.error_code:
                log.info(
                    "Evaluating %d branch(es) for %s: %s",
                    len(branches_to_eval),
                    instance_id,
                    branches_to_eval,
                )
            else:
                log.info("Re-evaluating %s from scratch", instance_id)
                existing_result = None

    try:
        submission_archive = source_dir / instance_id / "submission.tar.gz"
        if not submission_archive.exists():
            log.warning("Skipping %s (no submission.tar.gz)", instance_id)
            return InstanceEvalSummary(
                instance_id=instance_id,
                score=0.0,
                n_resolved=0,
                n_tests=0,
                error_code="no_submission",
                test_branches=all_test_branches,
            )

        tests_by_branch = {
            branch: all_tests_by_branch[branch] for branch in branches_to_eval if branch in all_tests_by_branch
        }

        from programbench.utils.blob_store import get_blob_dir

        evaluator = Evaluator(
            image_name=instance["image_name"],
            solution_branch="submission",
            submission_archive=submission_archive,
            blob_dir=get_blob_dir(instance_id),
            tests_branches=branches_to_eval,
            remove_hashes=instance.get("eval_clean_hashes", []),
            image_tag=image_tag,
            tests_by_branch=tests_by_branch,
            ignored_tests=ignored,
            ignored_branches=ignored_branches,
            instance_id=instance_id,
            docker_cpus=docker_cpus,
            branch_workers=branch_workers,
            branch_retries=branch_retries,
        )
        result = evaluator.run()

        if existing_result is not None and not result.error_code:
            wanted = set(all_test_branches)
            new_branch_set = set(result.test_branches)
            merged_branch_errors = {
                b: e for b, e in existing_result.test_branch_errors.items() if b in wanted and b not in new_branch_set
            }
            merged_branch_errors.update(result.test_branch_errors)
            old_warnings = [
                w
                for w in existing_result.warnings
                if not any(f"branch {b}" in w or f"Branch {b}" in w for b in new_branch_set)
            ]
            result = EvaluationResult(
                test_results=[
                    t for t in existing_result.test_results if t.branch in wanted and t.branch not in new_branch_set
                ]
                + list(result.test_results),
                log=existing_result.log + result.log,
                solution_branch=result.solution_branch or existing_result.solution_branch,
                test_branches=all_test_branches,
                test_branch_errors=merged_branch_errors,
                executable_hash=result.executable_hash,
                warnings=old_warnings + result.warnings,
            )

        (target_dir / instance_id).mkdir(parents=True, exist_ok=True)
        eval_json.write_text(result.model_dump_json(indent=2))

        filtered = result.without_ignored(ignored)
        return InstanceEvalSummary.from_eval_result(instance_id, filtered)
    except Exception as e:
        log.error("Error evaluating %s: %s", instance_id, e, exc_info=True)
        return InstanceEvalSummary(
            instance_id=instance_id,
            score=0.0,
            n_resolved=0,
            n_tests=0,
            error_code=type(e).__name__,
            solution_branch=None,
            test_branches=all_test_branches,
        )


def run_eval_batch(
    *,
    sources: list[str | Path],
    force: bool = False,
    filter_spec: str = "",
    slice_spec: str = "",
    workers: int = 1,
    branch_workers: int = 1,
    docker_cpus: int = DOCKER_CPUS,
    summarize_only: bool = False,
    image_tag: str = "task",
    output: str | Path = "",
    branch_retries: int = 1,
) -> None:
    from programbench.utils.load_data import load_all_instances

    all_instances = load_all_instances()
    log.info("Loaded %d instances", len(all_instances))

    all_instances = filter_instances(
        all_instances,
        filter_spec=filter_spec,
        slice_spec=slice_spec,
    )
    instance_lookup = {inst["instance_id"]: inst for inst in all_instances}

    output_root = Path(output) if output else None

    work_items: list[tuple[Path, Path, str]] = []
    target_by_source: dict[Path, Path] = {}
    for source in sources:
        source_dir = Path(source)
        target_dir = output_root / source_dir.name if output_root else source_dir
        target_by_source[source_dir] = target_dir
        log.info("Running in run directory mode: %s -> %s", source_dir, target_dir)
        instance_ids = [
            d.name for d in sorted(source_dir.iterdir()) if d.is_dir() and (d / "submission.tar.gz").exists()
        ]
        instance_ids = [iid for iid in instance_ids if iid in instance_lookup]
        for iid in instance_ids:
            work_items.append((source_dir, target_dir, iid))

    if not work_items:
        log.warning("No instances to evaluate.")
        return

    log.info(
        "Evaluating %d instances across %d source(s) with %d instance worker(s), "
        "%d branch worker(s), %d docker cpu(s) per container",
        len(work_items),
        len(sources),
        workers,
        branch_workers,
        docker_cpus,
    )

    results_by_source: dict[Path, list[InstanceEvalSummary]] = {}
    for source_dir, _, _ in work_items:
        results_by_source.setdefault(source_dir, [])

    with (
        logging_redirect_tqdm(),
        ThreadPoolExecutor(max_workers=workers) as executor,
    ):
        if summarize_only:
            futures = {
                executor.submit(
                    _summarize_instance,
                    instance_id=iid,
                    instance=instance_lookup[iid],
                    target_dir=target_dir,
                ): source_dir
                for source_dir, target_dir, iid in work_items
            }
            desc = "Summarizing"
        else:
            futures = {
                executor.submit(
                    _evaluate_instance,
                    instance_id=iid,
                    instance=instance_lookup[iid],
                    source_dir=source_dir,
                    target_dir=target_dir,
                    force=force,
                    image_tag=image_tag,
                    docker_cpus=docker_cpus,
                    branch_workers=branch_workers,
                    branch_retries=branch_retries,
                ): source_dir
                for source_dir, target_dir, iid in work_items
            }
            desc = "Evaluating"
        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc=desc,
            ncols=100,
            leave=False,
        ):
            summary = future.result()
            if summary:
                results_by_source[futures[future]].append(summary)

    console = Console()
    for source_dir, summaries in results_by_source.items():
        summaries.sort(key=lambda s: s.instance_id)
        batch = BatchEvalSummary(summaries=summaries)

        console.print()
        if len(sources) > 1:
            console.print(f"[bold]{source_dir}[/bold]")
        console.print(batch.summary())
        timing_path = _write_timing_summary(target_by_source[source_dir], summaries)
        if timing_path:
            console.print(f"[dim]Timing summary: {timing_path}[/dim]")
