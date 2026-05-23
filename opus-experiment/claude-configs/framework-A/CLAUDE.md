# framework-A — `/goal`-anchored, surface-derived probing

Task contract (do not delete):

- Reference: `/workspace/executable` (read + execute only)
- Source: write to `/work/work/`
- Build: `/work/work/compile.sh` must produce `/work/work/executable`
- Grading: per-test pass rate across a hidden test suite, multiple test-variant tarballs
- Budget: 4 hours wall-clock per task. One submission.

## Approach (20-second skim)

Your goal is a **behavioral twin** of the reference — a binary indistinguishable from it on every observable input. Anchor with `/goal`, map the reference's *full* surface (every flag the binary contains, not just what `--help` documents), golden every flag/value/alias/subcommand/composition plus a generic edge floor, build until your twin matches every golden, then differential-fuzz until two batches in a row find nothing new. `/goal` keeps the session alive until you've genuinely converged — not until the clock runs out.

## Never kill processes

Every reference call is wrapped in `timeout`, and the harness reaps any reference process older than 120s — you never need to kill anything. Do NOT run `pkill`, `kill`, `killall`, or `pgrep … | kill`. Your own session is a process whose command line contains the substrings `/workspace/executable`, `workspace`, and `executable` (from the initial prompt) — any cmdline-pattern filter matching those tokens WILL end your run. Process filtering by command-line content is fundamentally unsafe here. If something seems stuck, the watchdog handles it — do nothing.

## Step 1 — anchor

First action of the session:

```
/goal My binary is a behavioral twin of /workspace/executable. /work/work/SUBMIT_READY exists, created only after (1) diff_probe.sh prints "0 missed" over goldens covering every flag the binary contains (not just --help), every value/missing-value/alias/subcommand/composition, plus the generic edges, and (2) a differential-fuzz pass surfaces no observable difference from the reference.
```

## Step 2 — map the surface, then golden it

Read `--help` and each subcommand's `--help` — then go past them. `--help` is not the full surface: binaries frequently contain undocumented flags and aliases buried in the binary itself. Extract every flag-shaped token from the reference and treat the union of (documented ∪ extracted) as your real flag inventory. Capture goldens — each call wrapped in `timeout 10`:

```bash
mkdir -p /work/work/goldens
REF=/workspace/executable
P(){ local n=$1; shift; { echo "# CMD: $*"; timeout 10 bash -c "$*" 2>&1; echo "RC=$?"; } > /work/work/goldens/$n.txt; }

# Full flag inventory: --help PLUS every flag-shaped token in the binary itself.
{ timeout 10 "$REF" --help 2>&1; timeout 10 "$REF" -h 2>&1; strings "$REF"; } \
  | grep -oE '(^|[^a-zA-Z0-9_])(--[a-z][a-z0-9_-]*|-[a-zA-Z])' \
  | grep -oE '\-\-?[a-zA-Z][a-zA-Z0-9_-]*' | sort -u > /work/work/flags.txt
# Triage flags.txt and probe every entry against the reference, documented or not.
```

Golden, at minimum:

- **Every flag in `flags.txt`** (documented or not) — alone, with each value it accepts, AND with its value *missing* (characterize byte-for-byte how the reference rejects "no value" — exit code, exact stderr, which stream).
- **Each subcommand** alone, and with each of its flags.
- **Aliases**: long vs short vs documented synonym — capture all and confirm byte-identical behavior, both alone AND inside combinations (`-l -c` must match `--long --count`).
- **Compositions** — test how the surface combines, not just each piece alone:
  - every flag pair (and 3-way for flags that clearly interact);
  - every subcommand × each of its flags, and any subcommand-to-subcommand sequence the tool supports;
  - overlapping/conflicting pairs (two filters, two outputs, mode + modifier) — record which wins, the order applied, the exit code;
  - **keyword values across cases** — when a flag accepts a keyword (`--format X`, `--style X`, `--encoding X`), golden the same keyword in lower, upper, and mixed case to characterize whether the reference is case-sensitive.
  Combinations rarely behave like either piece alone; that's where the surface's real behavior lives.
- **Generic edges** (floor): no args, `-`, `--`, `-- -lookalike`, `--bogus`, empty/NUL/invalid-UTF-8/mixed-line-ending stdin, dir-as-file, missing file, huge stdin, closed stdout, broken pipe, SIGINT/SIGTERM mid-run.

**Invariant goldens for non-deterministic output.** If a probe's output changes between two identical runs (timestamps, PIDs, RTT, addresses, animation frames), do NOT byte-match and do NOT discard the golden. Golden the invariant instead — exit code, which stream was used, line/field count, structural shape, stable substrings — and compare on that projection. A golden you can't reproduce is a real gap; never delete one to make the gate pass.

## Step 3 — implement

Write source + `compile.sh` under `/work/work/`. Default to Python (stdlib only — the build sandbox has no network). Match the reference's source language only if it uses a PTY/TUI library or there's a concrete reason.

**Match the reference exactly, including where it looks wrong.** A "cleaner" result — nicer formatting, dedup where it duplicates, graceful where it errors, normalized where it passes input through raw — is a divergence, not an improvement.

**What looks dynamic may be frozen.** Timestamps, version banners, build info, embedded hashes, hostnames, and other values that suggest "generated at runtime" are often baked into the reference at *its* build time — the reference prints the same bytes on every invocation. Before regenerating such a value from your own runtime or build state, run the reference twice and check whether the value actually varies. If it doesn't vary, it's a literal — capture the exact bytes from the reference, don't re-derive them.

## Step 4 — gate, then fuzz the remaining budget

```bash
cat > /work/work/diff_probe.sh <<'SH'
#!/usr/bin/env bash
set -u; OURS=/work/work/executable; miss=0; ran=0
for g in /work/work/goldens/*.txt; do
  CMD=$(head -1 "$g" | sed 's|^# CMD: ||; s|/workspace/executable|/work/work/executable|g')
  EXP=$(tail -n +2 "$g"); ACT=$( { timeout 10 bash -c "$CMD" 2>&1; echo "RC=$?"; } )
  ran=$((ran+1)); [ "$EXP" = "$ACT" ] || { miss=$((miss+1)); echo "MISS: $(basename "$g")"; }
done
echo "Ran $ran, $miss missed"
SH
chmod +x /work/work/diff_probe.sh
```

Run it after every change; resolve every miss in source (for invariant goldens, compare the projection, not raw bytes). Once it prints `0 missed`, fuzz in **batches**: generate a fresh batch of random + structured inputs, run both binaries, fix every divergence. Each batch must be newly generated — never re-run the same inputs in a loop. When **two consecutive batches surface no new divergence**, you have converged: `touch /work/work/SUBMIT_READY` and stop. Do not keep fuzzing a clean binary to fill time, and do not chase a divergence you've already rationalized as a non-deterministic invariant.
