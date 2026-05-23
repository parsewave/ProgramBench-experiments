# framework-D — test-driven reimplementation

Task contract:

- Reference: `$REF_BIN` (reference binary path, provided in the environment;
  read + execute only)
- Source: write to `/work/work/`
- Build: `/work/work/compile.sh` must produce `/work/work/executable`
- Grading: per-test pass rate over a hidden test suite
- Budget: 4 hours per task, one submission

---

## Approach

Reimplement by Test-Driven Development (Beck, *Test-Driven Development:
By Example*, 2002), using the reference binary as the oracle (differential
testing — McKeeman, *Digital Technical Journal* 1998).

Your central artifact is an executable test suite under `/work/work/tests/`
that pins the reference's observed behavior. The implementation exists only
to make that suite pass. The test suite IS the specification.

Two consequences follow:

- Any behavior the reference exhibits but your suite does not assert is
  unspecified and will regress silently — so every behavior you observe
  becomes a test before it becomes code.
- Do not assume a behavior is out of scope or untested. If the reference
  does it, pin it — including behaviors whose output is unstable, which you
  assert structurally (see Coverage).

---

## The cycle

First, write a minimal `compile.sh` + skeleton source that builds a
placeholder `/work/work/executable`, so tests can run and fail meaningfully
instead of erroring on a missing binary.

Then repeat red → green → refactor:

1. **Observe.** Run `$REF_BIN` on an input you have not yet pinned. Capture
   the full triple: exit code, stdout bytes, stderr bytes. (While exploring,
   you may compare reference and executable directly with
   `diff <($REF_BIN ...) <(./executable ...)`; freeze a value as a test only
   once you understand the behavior.)
2. **Red.** Add a test under `/work/work/tests/` asserting your executable
   reproduces that exact triple. Run it — confirm it fails first.
3. **Green.** Write the minimal source to pass it.
4. **Refactor.** Tidy the source while tests stay green.
5. **Expand.** Take the next uncovered behavior and repeat.

Rebuild and re-run the suite once per green step, not per edit; on
slow-building languages, batch related edits before rebuilding. A fix for
one test routinely breaks another, so the green step always runs the whole
suite. Capture reference outputs as frozen expected values (inline literals
for small outputs, golden files for large *stable* outputs; structural
assertions for unstable ones — see Coverage). Never recompute an expected
value at test time.

---

## Coverage — the suite needs a test for each

Select cases by equivalence partitioning and boundary value analysis
(Myers, *The Art of Software Testing*, 1979):

- Every flag from `--help` and from `strings $REF_BIN`, individually.
- Every flag-syntax variant the parser accepts: `--flag=value` vs
  `--flag value`, short-flag bundling (`-abc`), `--` end-of-options.
- Every subcommand and every positional-argument shape.
- Every error path — bad flag, missing required value, type mismatch,
  conflicting flags — asserting exact stderr text AND exit code. Pin the
  full exit-code spectrum the reference uses, not just 0/1.
- Boundary values on every numeric/length input: {min−1, min, min+1,
  max−1, max, max+1}.
- Hostile inputs: empty, only `--`, only `-`, repeated flag, NUL / BOM /
  CRLF / invalid-UTF-8 / control bytes on stdin.
- Each environment variable the reference reads, exercised on its own,
  independent of the CLI flags.
- A pairwise sample of flag×flag and flag×environment interactions —
  enough to catch order-dependence and silent overrides without the full
  cross-product (Kuhn, Kacker, Lei — NIST SP 800-142, 2010).
- Filesystem side effects: files the reference reads or writes, output-path
  flags, overwrite/refuse behavior, and file modes — assert these as
  exactly as stdout.
- The I/O environment a user supplies: cases that run the reference under
  an attached terminal and an interactive stdin, not only redirected files
  and pipes. Pin the process model (one-shot, blocking on input, streaming,
  runs-until-signaled) and its behavior when the output consumer closes
  early. Distinguish closed-stdin / empty-stdin / blocked-stdin.
- Behaviors whose exact bytes are unstable (progress indicators, streaming
  output, timestamps, randomized fields): assert structurally — produces
  output / how much / what shape / terminates-or-not — never omit them.

---

## Submission gate

Coverage is complete when every item above has at least one test and the
pairwise interaction sample passes. At that point, draw 10 fresh randomly
sampled probes over the discovered surface; if your executable matches the
reference on all 10, that is the certification — submit immediately and do
not expand coverage further. Submitting before completion ships unpinned
behavior; verifying or fuzzing past a clean 10-probe sample does not raise
the score and only forfeits budget.

Before submitting: `compile.sh` must rebuild `/work/work/executable` from a
clean tree (remove build artifacts first, then build) and must not depend on
`tests/` — the suite is your development artifact, not part of the build.

---

## Tactics

- `file $REF_BIN` — identify language/runtime. Prefer the reference's
  implementation language when cross-language differences in runtime
  behavior (buffering, locale, terminal handling) would be observable.
- `strings $REF_BIN | grep -i <pattern>` — uncover hidden flags, version
  strings, error templates, embedded library identifiers.
- `od -c` / `hexdump -C` on any failing diff — catch invisible-byte
  differences (trailing newline, NUL, CRLF, BOM, ANSI escapes).
- For terminal/interactive cases, give the reference a real TTY when
  observing and in tests: `script -qec '<cmd>' /dev/null`, or
  `python3 -c 'import pty,sys; pty.spawn(sys.argv[1:])' $REF_BIN ...`, or
  `pexpect`. Wrap any invocation that may stream, block, or run until
  signaled in `timeout <seconds>` so a probe or test never hangs the suite.
- Determinism check: run the reference twice on the same input; if it
  varies, pin the stable invariant, not the volatile bytes.
