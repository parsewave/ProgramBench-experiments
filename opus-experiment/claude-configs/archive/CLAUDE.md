# ProgramBench

Reimplement a closed-source binary from observed behavior. Reference: `/workspace/executable` (read+execute only). Source: `/work/work/`. `compile.sh` must produce `executable` matching the reference's behavior on a hidden test suite. Per-test grading across multiple variants. **One submission. 4-hour budget. Use it.**

---

## Phase 0 — Sizing

```bash
wc -c /workspace/executable
/workspace/executable --help 2>&1 | wc -l
/workspace/executable --help 2>&1 | grep -cE '^\s+[a-z][a-z0-9-]+ '   # subcommand count
strings /workspace/executable | grep -cE '^(--|-)[a-z]'                # rough flag count
```

- **Small surface** (1–2 subcommands, few dozen flags): full reimpl is feasible. Cover everything.
- **Large surface** (5+ subcommands or 100+ flags): full reimpl in 4h is not. Triage — pick a subset and go depth-first (Phase 3). Five subcommands at 95% beats ten at 30%.

---

## Phase 1 — Discovery

**Produce `/work/work/behavior_map.md` + `/work/work/goldens/` before writing any source.**

### 1.1 Identify

```bash
file /workspace/executable
strings /workspace/executable | grep -iE 'ratatui|crossterm|ncurses|termion|tui-rs|tcell|bubbletea|ftxui|notcurses'
```

If any TUI library matches, this is a **PTY-driven task** — match the source language (Phase 2). Python wrappers return empty bytes under PTY drivers, deterministically failing those tests.

### 1.2 Static analysis

```bash
strings /workspace/executable | grep -E '^(--|-)[a-z]' | sort -u                 # all flag candidates
strings /workspace/executable | grep -iE 'USAGE|Usage|For more'                  # clap v2 (USAGE:) vs v3+ (Usage:)
strings /workspace/executable | grep -iE 'pcre|re2|regex::|boost::regex|onig'    # regex flavor
strings /workspace/executable | grep -iE 'serde_json|nlohmann|simdjson|json-c'   # json flavor
strings /workspace/executable | grep -iE 'glob|fnmatch|wildmatch'                # glob flavor

diff \
  <(/workspace/executable --help 2>&1 | grep -oE '\-\-[a-z][a-z0-9-]+' | sort -u) \
  <(strings /workspace/executable | grep -oE '\-\-[a-z][a-z0-9-]+' | sort -u)

# Bare-token alias candidates. clap's `#[clap(alias = "x")]` and similar
# store aliases as bare strings with no `--` prefix. Pull short lowercase
# identifiers and triage which ones look flag-shaped.
strings /workspace/executable | grep -E '^[a-z][a-z0-9_-]{1,14}$' | sort -u | head -200
```

Flags in `strings` but not `--help` are hidden-but-tested. Include them. From the bare-token list, any short token sitting next to a flag's help text in `strings` (or that you can't account for as a value / system word) — probe it as `--<token>` against the reference. Undocumented aliases are tested.

If `strings` alone doesn't show where validation happens:

```bash
ldd /workspace/executable
nm -D /workspace/executable 2>/dev/null | head
objdump -d /workspace/executable | head -200
strings -a -el /workspace/executable | head        # UTF-16
```

### 1.3 Surface goldens

Capture exact stdout / stderr / exit code for each. These are non-negotiable byte targets — embed them as string literals in your impl, never recompute. `--version` especially: frozen at the reference's build time, never yours.

```bash
mkdir -p /work/work/goldens/text
for CMD in '--help' '--version' '-h' '' '--bogus' 'nonexistent.txt' '/tmp' '- </dev/null'; do
  SAFE=${CMD//[ \/<>]/_}
  /workspace/executable $CMD > /work/work/goldens/text/${SAFE:-noargs}.txt 2>&1
  echo "RC=$?" >> /work/work/goldens/text/${SAFE:-noargs}.txt
done
```

Then check determinism — run a typical probe twice and diff. If outputs vary (timestamps, IDs, nonces, frame headers), byte-match grading fails on the varying fields. Identify which fields vary, reproduce the mechanism or extract stable invariants. Note this in `behavior_map.md`.

### 1.4 Hostile-input sweep

For every flag and every positional, save `# CMD: <command>` + stdout/stderr/rc to `/work/work/goldens/hostile/<flag>_<case>.txt` so the divergence loop can replay them.

```bash
# empties
/workspace/executable <flag> "" 2>&1
echo "" | /workspace/executable <flag> - 2>&1

# multi-char where one is expected (delimiters)
/workspace/executable <flag> "::" 2>&1
/workspace/executable <flag> "ab" 2>&1

# escapes — in input AND in flag values
printf '\t\n\r\\' | /workspace/executable <flag> 2>&1
/workspace/executable <flag> $'\t' 2>&1
/workspace/executable <flag> '\xff' 2>&1
/workspace/executable <flag> 'é' 2>&1

# invalid UTF-8 / control bytes
printf '\xff\xfe\x00\x7f' | /workspace/executable <flag> - 2>&1

# integer extremes (for numeric flags)
for N in 0 -1 -9999999 9999999999999999999 2147483648 18446744073709551616 1e308; do
  /workspace/executable <flag> "$N" 2>&1
done

# type mismatches + repeated flag
/workspace/executable <flag> /tmp 2>&1
/workspace/executable <flag> /etc/passwd <flag> /etc/hosts 2>&1

# value-position syntax
/workspace/executable --<flag>=value 2>&1
/workspace/executable --<flag> value 2>&1
/workspace/executable -<short>value 2>&1

# size axis
for SIZE in 0 1 4096 1048576; do
  head -c $SIZE /dev/urandom > /tmp/probe-$SIZE.bin
  /workspace/executable <flag> /tmp/probe-$SIZE.bin 2>&1
done
```

For **structured-format** flags (URL, regex, glob, CSS selector, JSON pointer, version range): derive degenerate forms from the grammar — empty, repeated-separator, escape-missing, prefix/suffix-only, mixed-case keyword. Probe each.

For **filter/select/list** flags: probe with input producing zero results. References print empty, placeholder, fallback, or non-zero. Observe.

### 1.5 Flag-pair interactions

For pairs touching overlapping state, probe:

- **Mode + modifier** — does the modifier still take effect inside the mode?
- **Multiple filters/selectors** — order of application? silent dominance?
- **Conflicting values** — override / error / stack?
- **Keyword casing** — `--format=X` in lower / upper / mixed
- **Argv order** — `-a -b` vs `-b -a`
- **Repeated flag** — `--foo A --foo B` — wins / stacks / errors?

Surprising behavior (silent override, different exit code, order-dependent) is almost certainly tested.

### 1.6 Test-author mindset — axes the sweep doesn't naturally cover

- **Idempotence:** `cmd $(cmd input)` ≟ `cmd input`?
- **Round-trip:** `encode | decode` ≟ input? Holds for any encoder/formatter/transformer.
- **Cross-subcommand consistency:** if `subA --format=X` produces shape Y, does `subB --format=X` produce the same?
- **`-` shorthand:** does `cmd -` mean stdin? `cmd -o -` mean stdout? Many CLIs treat `-` as a positional stdin/stdout sentinel.
- **Signal handling:** SIGINT / SIGTERM mid-run — exit code, output flush, cleanup behavior. Probe with `timeout` or by sending signals via `kill`.
- **`--` separator:** does `cmd -- -looking-like-flag` treat the rest as positionals?
- **Flag-alias byte equivalence:** long-form output ≟ short-form output, byte-for-byte?
- **Repeated invocation state:** does the binary write config / lock / cache files between runs?
- **Empty-after-nonempty:** content run, then empty run — same exit code, same shape?
- **Collection semantics:** any flag taking a list or repeating (`--foo a,b`, `--foo a --foo b`, `-f 1,1-3`) — characterize duplication / dedupe / ordering on overlapping or repeated values. Don't assume dedupe.
- **Combination ordering principle:** when 2+ flags affect the same output dimension via mixed keys (e.g., header-name + column-index, regex + literal), identify which principle governs ordering — CLI-spec, source-order, name-order, ... Argv order isn't always the answer.
- **Bi-directional library probing:** for any embedded library (regex, parser, glob), probe BOTH more-sophisticated constructs (lookarounds, POSIX classes, named groups, ...) AND less-sophisticated ones (basic classes, literal chars). Find where the reference's flavor draws the line — it may be less capable than what you'd default to.

Probe each that applies. Add findings to `behavior_map.md`.

### 1.7 Behavior map

`/work/work/behavior_map.md`: one section per flag, subcommand, error path. Each section records the observed bytes — nominal behavior, hostile behavior, interactions, value-position syntaxes accepted. Paste observed output verbatim; do not paraphrase.

Do not write source until this covers every flag (including hidden), every subcommand, every error path.

---

## Phase 2 — Language selection

| `file` says | Language | Build |
|---|---|---|
| Rust binary, `panicked at` strings | Rust | `cargo build --release --offline` (only with vendored deps) |
| Go runtime strings | Go | `go build -o executable .` (only with zero external imports) |
| ELF C/C++ | C/C++ | `gcc -O2 -o executable main.c` or `g++` |
| Python script | Python | `cp main.py executable && chmod +x executable` |

- **PTY/TUI tasks:** match the source language. Python wrappers fail under PTY drivers.
- **Plain CLI tasks:** Python is the default unless there's a concrete reason against.
- **No network in the build sandbox.** `cargo build` without vendoring and `go mod download` fail. Use stdlib / system libs.
- **Do not implement from training-data memory.** If the binary looks like a well-known CLI tool, the reference may be an older version, a fork, or a patched build. The only ground truth is `/workspace/executable`.
- **Match the reference's library flavor** for regex / JSON / glob / datetime. PCRE vs RE2, named-group syntax, glob `**` rules vary. Pick the impl library that matches the reference, not what's convenient.

**Prohibitions:**

- No Python wrappers for native TUI / PTY-driven binaries.
- No stub implementations that just print error strings.
- For intractable TUI tasks: implement headless equivalents for non-TUI subcommands — they're graded independently, and partial credit on TUI branches plus full credit elsewhere beats zero everywhere.

---

## Phase 3 — Implementation

Priority order:

1. Every flag from `--help` ∪ `strings`. Each needs a real handler — parsed-but-ignored config fields fail tests.
2. Every subcommand.
3. Every error path from §1.3 and §1.4. Match exact text, exact stream, exact exit code.
4. Cross-subcommand data flow.
5. Edge inputs (already covered in `goldens/hostile/`).

### Behavioral parity, not algorithmic correctness

Goal: byte-identical to the reference, even where the reference is counterintuitive. If your impl looks "cleaner" than the reference — nicer output, more graceful edge handling, dedupes where reference duplicates, encodes where reference passes through raw — that's a divergence, not an improvement. Reference quirks and bugs are part of the grading target.

### Depth-first for large surfaces

If Phase 0 said large: pick the subcommand with the most testable surface (most flags, most error paths, most input types). Implement to 100% local pass rate. Then expand outward. Each completely-shipped subcommand is a guaranteed pass-rate floor for its test branch.

### Match the reference's error stage

When the reference rejects an input, observe at what stage:

- **Parse-time:** message about input shape, no I/O happened ("delimiter cannot be empty").
- **Pre-work validation:** message about a resource, early bail ("file not found").
- **Mid-work:** message mentions partial state ("after processing 3 of 5...").

Your impl must reject at the same stage. Different stage = different message = failed test.

### Build-health budget

If >15% of your first 20 compiles fail, stop adding code. Diagnose: toolchain unavailable in sandbox? `compile.sh` referencing files that don't exist? Real compiler errors? Drive failure rate below 5% before any new feature code.

---

## Phase 4 — diff_probe loop (the gate)

```bash
# /work/work/diff_probe.sh
set -u
REF=/workspace/executable
OURS=/work/work/executable
N=0; FAIL=0
for case in /work/work/goldens/hostile/*.txt /work/work/goldens/nominal/*.txt; do
  CMD=$(head -1 "$case" | sed 's/^# CMD: //')
  R=$(eval "$REF $CMD" 2>&1; echo "RC=$?")
  O=$(eval "$OURS $CMD" 2>&1; echo "RC=$?")
  N=$((N+1))
  if [ "$R" != "$O" ]; then
    FAIL=$((FAIL+1))
    echo "=== DIVERGE: $case ==="
    diff <(echo "$R") <(echo "$O") | head -20
  fi
done
echo "Ran $N cases, $FAIL diverged."
```

- Need ≥50 cases. Use the full hostile sweep.
- Every divergence: fix in source, OR write a one-line rationale in `divergence_notes.md` explaining why expected.
- **After any fix, re-run the full loop.** Fixes for one case routinely break previously-passing cases.

---

## Submission gate

All must be true:

- [ ] Past turn 15. Earlier submissions are stubs.
- [ ] `file` and `strings` were run; impl language matches.
- [ ] `behavior_map.md` covers every flag, subcommand, error path, and §1.5 interactions.
- [ ] `goldens/hostile/` populated; every flag has ≥1 hostile-input golden.
- [ ] `--help`, `--version`, `--bogus` byte-diff against reference is empty.
- [ ] Every flag in `--help` diff-tested individually.
- [ ] `diff_probe.sh` ran over ≥50 cases with `FAIL=0` (or every residual rationalized).
- [ ] No forbidden phrase appears in your reasoning.
- [ ] **Coverage self-report:** state "I implemented N of M flags, A of B subcommands, C of D error paths. Estimated ceiling ≈ A/B × N/M = X%." If X<70%, do not submit — implement more.
- [ ] **Senior-engineer review:** answer "What would a senior engineer reviewing this for 10 minutes catch first?" If non-trivial, fix it.
- [ ] **Grader simulation:** state your honest pessimistic estimate of % of hidden tests you'd pass. If <80%, you are not done.

**compile.sh file-existence check:**

```bash
grep -oE '[a-zA-Z0-9_./-]+\.(py|c|cpp|go|rs|sh|txt)' /work/work/compile.sh | sort -u \
  | while read f; do [ -e "/work/work/$f" ] || echo "MISSING: $f"; done
```

Must print nothing.

**Submission-tree cleanup:**

```bash
ls -d /work/work/.git /work/work/target /work/work/__pycache__ 2>/dev/null
ls /work/work/Cargo.toml /work/work/go.mod /work/work/src/main.rs 2>/dev/null
echo "files: $(find /work/work -type f -not -path '*/.git/*' | wc -l)"
```

Delete fossils from abandoned attempts (`Cargo.toml` / `go.mod` / `src/` / `.git/`) if `compile.sh` doesn't reference them. The tarball includes everything under `/work/work/` — keep it lean.

---

## Forbidden phrases — stop and run the coverage self-report

**Hard abandonment:**

- "impractical" / "infeasible" / "not feasible" / "out of scope"
- "I'll skip" / "I'll fake" / "Let me move on"
- "complete reimplementation is impossible" / "cannot be reimplemented"
- "best-effort" / "too complex to reimplement"

**Soft abandonment (same family, quieter):**

- "I think this covers the main cases"
- "the remaining are edge cases"
- "this is good enough for the common path"
- "I'll prioritize what's most likely tested"
- "this is comprehensive enough" / "the core functionality is implemented"
- "the rest are nice-to-have"

If you genuinely cannot implement a feature: ship the **minimum viable** version that makes ONE test pass, not zero.

---

## When you feel finished — the most dangerous moment

Voluntary early submission costs the most points. You have 1M+ tokens of context. Capacity isn't the constraint; persistence is.

Before submitting, run this forced exercise:

1. **Enumerate 10 specific test failure modes you have NOT yet probed.** Not categories — concrete inputs. If you can't think of 10, you haven't probed enough.
2. **Probe each against `/workspace/executable`.**
3. **For any divergence, fix and re-run `diff_probe.sh`.**
4. **Repeat until: all 10 match, OR 3 cycles complete with no new divergences.**

If you still have unresolved failing diffs:

1. `strings` with broader filters: `strings -a /workspace/executable | grep -E '[A-Z][a-z]+Error'`
2. Diff stderr character-by-character — sometimes it's a single trailing newline.
3. `od -c` both outputs to spot invisible-byte differences.

Then — and only then — submit.
