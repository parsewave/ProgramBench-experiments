# framework-B — multi-agent probe → adversarial review → implement → verify

Task contract:

- Reference: `/workspace/executable` (read + execute only)
- Source: write to `/work/work/`
- Build: `/work/work/compile.sh` must produce `/work/work/executable`
- Grading: per-test pass rate over a hidden test suite
- Budget: 4 hours per task, one submission

## Mandate

You are not writing good software. You are producing a **behavioral twin** of the reference. Its observable behavior — every byte of output, every exit code, every response to signals, closed pipes, and malformed input, every quirk that looks like a bug — is the specification. When your engineering instinct ("handle this gracefully", "this output is cleaner", "this edge case should error", "this feature isn't worth implementing") conflicts with what the reference actually does, the reference wins. Never ship a stub: if the reference does something, you do it too.

Do NOT write source until Phase 3 finishes.

---

## Phase 1 — Probe (3–5 parallel subagents, single message)

Spawn via multiple `Agent` tool calls in one response (concurrent). Distinct axes, no overlap. Each agent observes through **the same channel the grader will use for its axis** — not just plain stdout capture:

- **surface** — `--help`, `--version`, `--bogus`, no-args, subcommands; every flag's error text + exit code. If `strings /workspace/executable | grep -iE 'ratatui|crossterm|ncurses|tcell|bubbletea|ftxui|notcurses'` is non-empty, the binary drives a terminal. PTY-byte-capture and tmux-pane-capture are **different channels**: the byte stream contains every cursor move and SGR code, while the pane is what those bytes resolve to after the terminal interprets them. A byte stream that produces output under PTY may still resolve to nothing visible in a pane. When the binary drives a terminal, observe what the pane shows after warmup — char density, glyph set, color distribution, change over time — and treat that as part of the spec, not just the bytes on the wire.
- **input** — stdin (empty / EOF / binary / large), file inputs (missing / dir / FIFO / symlink), encoding (invalid UTF-8, BOMs, mixed line endings, null bytes)
- **lifecycle** — drive the actual conditions: send SIGINT / SIGTERM mid-run; pipe stdout into a reader that closes early (`cmd | head -1`) and record the exit code; `/dev/full`; repeated invocations. Record exit codes precisely — they are graded.
- **flag-combinations** — pairs and triples sharing an output dimension; argv order; case-sensitivity of keyword values; conflicting flags (does the reference reject, and with what exact usage text + rc?). The help text is not the spec — the argument parser is. Help text lists what the author chose to document; the parser accepts whatever the author wired up, which is often a strict superset. Probe the parser directly rather than trusting the help: enumerate single-letter short flags, prefix-truncated long flags, and near-miss spellings, and read whatever the parser emits back (error text, hints, suggestions) as a window into flags it knows about but didn't advertise. Hidden flags and aliases get graded too.
- **structured-input** — for every flag taking a URL / regex / glob / JSON pointer / path: pathological forms of that grammar

Each subagent gets:

- `/workspace/executable` is read+execute-only
- One axis (no overlap), observed through the grader's channel for that axis
- Report format: markdown table `| Feature | Inputs probed | Observed reference output (verbatim, incl. exit code) | Notes |`
- ≤ 500 lines
- Must NOT write to `/work/work/`

**Environment matters.** The grader executes the gold binary in a specific runtime environment — network reachability, DNS resolution, terminal dimensions, locale, filesystem layout, available system binaries, env vars. A probe's outcome can depend on any of these, and a result captured in one environment may not reproduce in another. When a row's behavior could plausibly depend on the environment, identify which dimension matters, re-probe the gold in the same container configuration the grader will use, and pin the spec to that result. Note the environmental dependency in the row so it isn't silently re-broken later.

---

## Phase 2 — Build the behavior table

Merge all reports into `/work/work/behavior_table.md`. Same schema, deduped, sorted by axis. Reference output verbatim — never paraphrase. Record exit codes alongside output.

Classify each row by determinism mode:
- **byte-deterministic** — same input produces the same bytes every run; check via byte-equality.
- **structurally-deterministic** — same input produces bytes that vary (PRNG-driven content, timestamps, animation frames, ordering of unordered collections, address-dependent identifiers) but the *structure* is stable. For these rows, record the invariants that ARE stable: length range, char/glyph set, distribution, monotonicity, presence/absence of features, schema. The verifier checks invariants, not bytes.

Structurally-deterministic rows stay in the table. Do not drop them — dropping loses coverage on the very behaviors that distinguish a real reimplementation from a stub.

---

## Phase 3 — Adversarial review (2–3 anti-agents in parallel)

Spawn 2–3 anti-agents in one message. Each gets the table and this brief:

> Find gaps, ambiguities, and implementation traps. Specifically: (a) rows where two correct-seeming impls would diverge; (b) edge cases adjacent to covered ones that are missing; (c) behaviors named but not pinned to exact bytes / exit code; (d) **rows where a clean, idiomatic implementation would behave DIFFERENTLY from the reference — i.e. places the reference does something surprising, buggy, or non-idiomatic that we'd "accidentally fix"**. Return a numbered list of weaknesses, each with a concrete patch (additional probe to run, or row text to tighten).

For each weakness: run the additional probe, tighten the row, or add new rows. Re-spawn anti-agents until they report no critical gaps.

---

## Phase 4 — Implement

Write source under `/work/work/` + `compile.sh` producing `/work/work/executable`.

- Default: Python, stdlib only (no network in build sandbox)
- Match the reference's source language if it drives a terminal (the `strings` grep above) or has another concrete reason
- Reproduce the reference's behavior exactly — including behaviors the table flagged as surprising or buggy. Do not "improve" on them. Do not stub anything the reference actually does.
- **Match dependencies, not just outputs.** When the reference uses a third-party library for any observable output — tables, JSON/CSV formatters, color/styling, terminal widgets, hash functions, regex engines, sort/locale handlers — the library's quirks (separator chars, alignment rules, quoting, escape behavior, padding, locale-sensitivity, error templates) are part of the spec. Reimplementing a library by eye produces close-looking output that fails byte-level differential tests. Identify the dependency via `strings`, `ldd`, `file`, version banners, error-template fingerprints; then either link the same dependency in your build, or reproduce its exact behavior.

After every meaningful change: sanity-diff the most-recently-touched rows against the reference. If you discover new behavior, add a row.

---

## Phase 5 — Final verification (worker agent)

Spawn ONE worker agent:

> Spec is `/work/work/behavior_table.md`. For every row, run the input against both `/workspace/executable` (gold) and `/work/work/executable` (ours), through the same channel the row was observed on (PTY-bytes / tmux-pane / pipe / signal / plain). Apply the equality check appropriate to the row's determinism mode: byte-equality for byte-deterministic rows, invariant-checking for structurally-deterministic rows. For rows observed via tmux-pane, also diff the rendered pane content (non-space char count, glyph set, change-over-time) after a warmup. If the byte stream matches but the pane is empty (or vice versa), that is a divergence — channels are not interchangeable. Exercise the error / signal / broken-pipe paths, not just nominal inputs. Write divergences to `/work/work/final_diff_report.md`. Do not modify source. Do not submit.

Read `final_diff_report.md`:

- Zero divergences → `touch /work/work/SUBMIT_READY` and submit
- Otherwise → fix, re-run worker, loop

Do not submit until `SUBMIT_READY` exists.

---

## Notes

- Subagents have independent context windows. They coordinate only via the orchestrator's reads/writes of `behavior_table.md`.
- Always spawn parallelizable subagents in a SINGLE message.
- Subagent type: `general-purpose` for all phases.
- Behaviors that have no stable structure to invariant-check (and so can't be matched in any form): record in `/work/work/divergence_notes.md` with the reason, then remove from the table. This should be rare — most "non-deterministic" output still has stable invariants worth checking.
- Do not `pkill -f` any pattern that could match your own driver process; target exact PIDs when you need to clean up reference processes.
