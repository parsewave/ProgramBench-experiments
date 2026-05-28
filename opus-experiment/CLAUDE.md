# Clean-room reverse engineering

Task contract:

- Reference: `/workspace/executable` (read + execute only)
- Source: write to `/work/work/`
- Build: `/work/work/compile.sh` must produce `/work/work/executable`
- Grading: per-test pass rate over a hidden test suite
- Budget: 4 hours per task, one submission

---

## Approach

Recover the reference binary's behavioral specification by composing four
established black-box methodologies:

- Category-Partition Method (Ostrand & Balcer, *CACM* 1988)
- Equivalence Partitioning + Boundary Value Analysis + Error Guessing
  (Myers, *The Art of Software Testing*, 1979)
- Differential Testing (McKeeman, *Digital Technical Journal* 1998;
  Csmith — Yang et al., *PLDI* 2011)
- Clean-room Software Engineering (Mills, Dyer, Linger,
  *IEEE Software* 1987)

The reference binary IS the oracle. Do not invent properties. Do not
catch errors from the reference — propagate them as spec. Every behavior
the reference exhibits is part of the specification: do not scope a
behavior out on the assumption it will not be exercised. When a behavior's
exact bytes are unstable (animations, streaming output, timestamps,
randomized fields), reproduce it structurally — match whether it produces
output, how much, in what shape, and whether it terminates or runs until
signaled — rather than omitting it.

---

## Procedure

Before writing any reimplementation code:

1. **Surface scan.** Run `B --help`, `B`, `B --version`, `B --bogus`,
   `B -`, `B --`. Record bytes verbatim. Exercise the reference in the
   full I/O environment a user supplies — an attached terminal and an
   interactive stdin, not only redirected files and pipes — since a
   program's behavior can branch on what it is connected to. The process
   model (one-shot, blocking on input, streaming, or running until
   signaled) is part of the spec.
2. **Category-Partition.** List parameters and environment dimensions;
   per dimension list choices including {empty, boundary, hostile,
   invalid-type}; write the constraint list. Treat each environment
   variable the reference reads as its own dimension and probe it
   independently of the CLI flags. Cap probes at ~30 via a pairwise
   covering array (Kuhn, Kacker, Lei — NIST SP 800-142, 2010).
3. **EP / BVA / EG layer.** For every numeric or length range, probe
   {min−1, min, min+1, max−1, max, max+1}. Include the canonical
   black-box probes: empty arg, only `--`, only `-`, repeated flag,
   conflicting flags, missing required, extra positional, NUL / BOM /
   CRLF / invalid-UTF-8 / control bytes on stdin, broken pipe.
4. **Freeze the oracle.** For each probe record the full triple — exit
   code, stdout bytes, AND stderr bytes. Error-message templates on
   stderr and exit codes are first-class byte targets, frozen as exactly
   as stdout. Persist to `/work/work/frames.jsonl`.
5. **Differential loop.** Build the reimplementation; run every frame
   against both binaries; on divergence, shrink (halve stdin, drop
   flags) to a minimal failing frame, fix, re-run the full bank.
6. **Statistical top-up, then stop.** Before submission, sample 10 fresh
   probes from a usage Markov chain (Whittaker & Thomason, *IEEE TSE*
   1994) over the discovered modes. When the reimplementation matches the
   reference on all 10, the spec is certified — submit immediately.
   Re-verification, re-fuzzing, or cleanup after a clean top-up does not
   raise certified reliability and only forfeits budget.

---

## Probing tactics

Standard tooling for black-box CLI investigation, used in service of
the procedure above:

- `file <binary>` — identify binary type and language runtime. Match the
  reference's source language when it links a library whose runtime
  contract a foreign-language reimplementation cannot reproduce.
- `strings <binary> | grep -i <pattern>` — discover embedded library
  identifiers, version strings, error templates, format strings.
- `od -c` or `hexdump -C` on diverging outputs — surface invisible-byte
  differences (trailing newlines, NULs, CRLF, BOM, ANSI escapes).
- `diff <(REF args) <(SUT args)` — single-shot byte comparison; for
  large outputs combine with `head -c N` or `md5sum`.
- Determinism check: run the reference twice on the same input and
  diff. If outputs differ (timestamps, IDs, random padding), reproduce
  the variability mechanism or extract stable invariants before
  freezing the oracle.
- Wrap probes in `timeout <seconds>` for any invocation that may stream,
  block on input, or run until signaled.
