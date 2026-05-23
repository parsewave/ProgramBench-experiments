# CLAUDE.md changelog

Brief record of changes made to `CLAUDE.md` since the PR #32 baseline. Not consumed by the agent — for human reference only (the bind mount only exposes `CLAUDE.md`).

## Baseline → trimmed core (~514 → 313 lines, -39%)

- Removed "The Five Rules" section — content was restated inline in each phase.
- Removed Phase 4 sub-sections 4.1–4.4 (flag-wiring diff, error-text byte fidelity, subcommand interop, help/version byte-diff). All subsumed by §4.5 `diff_probe.sh` loop.
- Removed standalone "Coverage-gap audit" — items folded into hostile sweep / submission gate.
- Removed standalone "Anti-patterns to avoid" — merged into Forbidden phrases.
- Collapsed Phase 2 Steps A/B/C/D from four headed subsections into one fluid section + table.
- Dropped explanatory/motivational prose ("Once you commit, switching is expensive", "Think carefully at every decision point", etc.). Kept the actionable parts.

## Leakage cleanup (5 spots)

- Removed grader's specific PTY tooling (`tmux capture-pane`, `script`, `unbuffer`) + literal test assertion `assert len(b'') > 0`.
- Softened "30–60% of tests" → "a large fraction" (was a prior-run-derived stat).
- Removed task-specific subsystem examples ("encryption, journal create") from TUI guidance.
- Removed trajectory-specific narrative quoting agent text from prior runs ("now let me write main.py").
- Removed Sonnet/csview-specific observation about "36-file submissions with .git/".

## Sub-70 additions (persistence + decomposition levers)

- **Phase 0 — Sizing.** Four measurements (`wc -c`, help line count, subcommand count, flag count) → small-surface vs large-surface playbook fork.
- **§1.2.5 — Deeper static analysis.** `objdump -d`, `nm -D`, `readelf -a`, `ldd`, `xxd`, UTF-16 strings — for when behavior probing alone doesn't locate where validation happens.
- **§1.3.5 — Output-determinism check.** Run a probe twice, diff. Catches non-byte-matchable tasks (compression, crypto, timestamped output).
- **§1.6 — Test-author mindset axes.** Idempotence, round-trip, cross-subcommand consistency, `-` shorthand, signal handling, `--` separator, alias byte equivalence, stateful invocations, empty-after-nonempty.
- **§2 Step D — Anti-hallucination.** Do not implement from training-data memory; the reference may be an older version / fork / patched build.
- **§3 Depth-first for large surfaces.** If Phase 0 said large: pick the subcommand with the most testable surface, ship it to 100%, then expand. Five at 95% beats ten at 30%.
- **Submission gate persistence checks:**
  - Quantitative coverage self-report: state implemented N/M flags etc.; if A/B × N/M < 70%, do not submit.
  - Senior-engineer review: write what a 10-min reviewer would catch.
  - Grader simulation: honest pessimistic estimate of % of hidden tests passing; if <80%, not done.
- **Forbidden phrases extended.** Added soft-abandonment tier ("I think this covers the main cases", "edge cases", "good enough for the common path", "comprehensive enough", "core functionality is implemented", "the rest are nice-to-have").
- **"When you feel finished" forced exercise.** Enumerate 10 specific unprobed test failure modes, probe each, fix divergences, repeat up to 3 cycles. Reframes the dangerous moment of voluntary early submission. Explicitly notes 1M+ context — capacity isn't the constraint, persistence is.

## Trace-derived axes (from cc-opus-easy5-20260520-063309 study)

Added based on what the easy5 run *missed* (so they're general CLI patterns, not task-specific hints):

- **`-` shorthand** as stdin/stdout sentinel (htmlq missed `test_file_input_dash_means_stdin` and `test_output_dash_means_stdout`).
- **Signal handling** (SIGINT/SIGTERM) — exit code, output flush, cleanup (pingu missed 12 signal-cluster tests).
- **`--` separator** for "treat rest as positionals" (general CLI convention).
- **Collection semantics** — duplication / dedupe / ordering on repeated flags.
- **Combination ordering principle** — when 2+ flags affect the same output dimension via mixed keys.

### Follow-up from easy5 failure analysis (added before cc-opus-20260520-102624 top9 run)

Three more surgical edits driven by deeper root-cause analysis of the easy5 results. ~15 lines total. Still first-principles only — no test-specific hints.

- **Bare-token alias scan** in §1.2. Added a second `strings` pass — `grep -E '^[a-z][a-z0-9_-]{1,14}$' | sort -u | head -200` — to surface candidates that aren't `--`-prefixed. The original `--`-prefixed cross-reference missed csview's `--seq` (1 test from ✅): clap's `#[clap(alias = "seq")]` stores the alias as the bare token `seq` adjacent to `--number`'s help text in `strings`. Generalizes to any clap-style alias buried in a binary.
- **Bi-directional library probing** as a §1.6 axis. For any embedded library (regex, parser, glob), probe BOTH more-sophisticated constructs (lookarounds, POSIX classes, named groups) AND less-sophisticated ones (basic classes, literal chars). Existing Step C "match the reference's library flavor" only pushed *what library to pick*, not *which direction the reference's capability surface might lie*. hck `test_regex_posix_character_class`: agent's regex interpreted `[[:space:]]` as POSIX class (more sophisticated); reference treated it literally as character set `[:space:]`-as-chars (less sophisticated). Bi-directional probe would have surfaced the gap.
- **Behavioral parity, not algorithmic correctness** as a new Phase 3 subsection. Goal is byte-identical to reference even where reference is counterintuitive. If your impl looks "cleaner" — nicer output, more graceful edge handling, dedupes where reference duplicates, encodes where reference passes through raw — that's a divergence, not an improvement. htmlq `test_remove_nodes_all_filtered_out` (reference has an iteration-detach quirk producing empty output; agent's cleaner impl outputs both modified divs) and URL handling (`https://base.com//example.com/path` preserved verbatim by reference; agent stripped to bare `example.com/path`) were the motivating cases. Doctrine never explicitly told the agent that "cleaner" can be wrong.

## Quantitative thresholds (unified at 50)

Originally Rule 5 said `≥50`, §4.3 said `≥200`, §4.5 said `≥20`. Unified to **50** across Rule 5, §4.5 diff_probe minimum, and submission gate.

## Other tweaks

- Phase 3 Go template: added comment "(only with zero external imports — see Phase 2 Step B)" — Step B explains `--network none` sandbox.
- Phase 3 build-health budget: `>15% compile-fail rate over first 20` → stop and diagnose.
- Submission gate: turn-15 minimum, compile.sh file-existence check, submission-tree cleanup check (remove `.git/`, `Cargo.toml`, `go.mod` fossils from abandoned attempts).
