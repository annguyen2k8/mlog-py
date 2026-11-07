# ADR-003: P6 Control-Flow Preservation and Recursion Contracts

- **Status**: Accepted
- **Date**: 2026-11-04
- **Deciders**: mlog-py Compiler Team
- **Target Engine**: Mindustry v160.7

---

## 1. Context

The P6 audit found four defects that either changed program semantics or
silently produced invalid bytecode:

1. **Dropped unconditional jumps.** `CFGStructurer._structure_range()` treated
   every jump to `target >= stop_address` as a structured merge fallthrough and
   consumed it. Program terminators, branch-boundary jumps, and loop-latch jumps
   were therefore lost. The recompiled program executed unreachable code or
   exited a loop incorrectly.
2. **Discarded function results.** `Compiler.compile_call()` returned the
   literal `"0"` when a user-function call had no explicit destination. The
   call protocol already writes the result to `__retval_<fn>`, but expression
   contexts never read it.
3. **Inconsistent jump formatting.** The plain decompiler formatted raw jump
   operands semantically, while `SourceMapEmitter` used `repr()`. Source-map
   output such as `jump('5', 'greaterThan', 'a', '0')` changed addresses and
   variables into strings and altered runtime behavior.
4. **Unbounded recursion.** The compiler has one scalar return-address register
   per function (`__ret_<fn>`). Recursive calls overwrite the caller's return
   address and loop until the instruction limit.

P6-CRIT-01, P6-CRIT-02, and P6-CRIT-03 are correctness defects. P6-HIGH-01
requires a durable language-level decision because the current calling
convention cannot represent a call stack.

---

## 2. Decision

### 2.1 Preserve every unconditional jump edge

The structurer must never silently drop an unconditional jump. It classifies the
edge as follows:

- `target >= n_instructions`: emit an explicit `end()` instruction. This is a
  program terminator, not a fallthrough.
- `target == stop_address` **and** the jump is the final instruction of the
  range: consume it as a structured fallthrough.
- Jump to the innermost loop header or to a latch whose final instruction is an
  unconditional `jump <header>`: emit `continue`.
- Any other jump crossing the enclosing scope boundary: preserve the original
  instruction in an `UnstructuredNode`. Do not guess a merge, break, or
  fallthrough.

**Rationale:** the zero-guessing contract requires semantic equivalence. When a
jump edge cannot be proven to be a structured equivalent, preserving the raw
branch is always safe and keeps the instruction reachable in the source map.

### 2.2 Capture user-function results in value contexts

When a user-function call is used as a value (`target_dest is None` and
`is_statement is False`), copy `__retval_<fn>` into a fresh temporary and return
that temporary to the expression. Keep the existing direct copy when a target
destination is supplied. A call used only as a statement must not allocate a
capture register.

**Rationale:** the calling convention is unchanged and no extra register is
allocated for side-effect-only calls. This also makes nested calls and
`return call(...)` well-defined without a separate expression protocol.

### 2.3 Use one semantic formatter for raw jumps

`format_jump_arguments()` in `structured_ir.py` is the single source of truth
for rendering `UnstructuredNode` jump operands. Both the plain decompiler and
`SourceMapEmitter` must call it.

**Rationale:** duplicated formatting logic caused the source-map path to drift
from the plain path. Jump operands have mixed roles (address, condition token,
numeric/string literal, variable), so only metadata-driven semantic formatting
is valid.

### 2.4 Reject recursion until a software stack exists

Detect direct and indirect cycles on the user-function call graph after constant
folding and raise `CompileError` at the offending call site with the complete
cycle path. Do not emit bytecode for a recursive program.

**Rationale:** the current convention cannot preserve more than one return
address per function. Rejecting recursion is preferable to silently generating
a non-terminating program. Supporting recursion later requires an explicit
software stack (a frame array in memory or an equivalent mechanism) and a new
ADR for the calling convention.

---

## 3. Consequences

- Unreachable instructions remain visible in decompiled output and in the source
  map instead of being silently folded away.
- `end()` is now part of the decompiler's output vocabulary for terminator
  jumps. It compiles to the native `end` instruction.
- The function calling convention remains register-based and non-reentrant.
  Recursive programs fail fast with an actionable diagnostic.
- Corpus programs that rely on recursion now assert the rejection contract. This
  is an intentional contract change, not a reduction in coverage.
- Loop-exit gap reachability (P6-HIGH-02) was a pre-existing limitation that
  P7 fixed by making the recorded loop exit address authoritative. See
  `docs/adr/0004-p7-decompiler-fidelity-contracts.md`.

---

## 4. Verification

- `tests/test_p6_remediation.py`: 21 pure-Python tests covering program
  terminators, branch boundaries, latch `continue`, structured fallthroughs,
  return-value capture in expressions/nested/multiple calls, statement-only
  calls, source-map formatting, and direct/indirect recursion rejection.
- `tests/test_p6_remediation_jvm.py`: 11 Mindustry v160.7 tests proving runtime
  state equivalence for all four findings.
- `python run_tests.py --fast`: 850/850 passed.
- `python run_tests.py --jvm`: 618/618 passed.
- `python run_tests.py --all`: 1468/1468 passed.
- Corpus metrics: byte-for-byte 16/32 -> 17/32, normalized 16/32 -> 17/32,
  source-map coverage mean 0.9836 -> 0.9884, JVM final-state equivalence
  29/32 -> 30/32 (2 recursion files rejected by design, `flare_miner.mlog`
  invalid in both engine runs).

Detailed evidence is preserved in git history (commit 54179b5).
