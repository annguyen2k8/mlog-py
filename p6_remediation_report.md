# P6 Remediation Report

- **Date**: 2026-11-04
- **Baseline**: `0896679` (`docs(handoff): update task handoff for P5 remediation completion`)
- **Engine**: Mindustry v160.7 (JVM integration tier)
- **Scope**: P6-CRIT-01, P6-CRIT-02, P6-CRIT-03, P6-HIGH-01
- **Status**: All four requested findings fixed and verified. One out-of-scope
  decompiler limitation is documented in section 8.

> **Post-P7 correction (2026-11-07).** The P6 verification compared final state
> on fixed corpus inputs only. `p7_fidelity_audit.md` re-ran the corpus with
> exact PC traces and found three dropped-else defects and a bare-`@` register
> defect that final-state comparison could not see. It also showed that the
> P6-H02 gap has two ranges (`[20, 22)` and `[33, 36)`), that it is reproducible
> with an operand-only variant, and that the seven function files miss only
> address `0` (the preamble), not function-body addresses. The P6 fixes
> themselves remain valid; the claims in sections 7.2 and 8.1-8.3 below are
> superseded by `p7_remediation_report.md`.

---

## 1. Executive Summary

| Finding | Severity | Failure mode at baseline | Status | Commit |
| --- | --- | --- | --- | --- |
| P6-CRIT-01 | Critical | Unconditional jumps crossing a structured range were dropped, so program terminators and branch boundaries fell through into unreachable code. | Fixed | `90e8139` |
| P6-CRIT-02 | Critical | A user-function call used as an expression operand compiled to the literal `0`; the call protocol result in `__retval_<fn>` was never captured. | Fixed | `e04941c` |
| P6-CRIT-03 | Critical | Source-map emission for `UnstructuredNode` rendered jump operands with `repr()`, quoting addresses and identifiers and producing invalid or inverted jump semantics. | Fixed | `7710605` |
| P6-HIGH-01 | High | Recursive user functions compiled to bytecode that overwrites the single scalar return-address register and loops forever. | Fixed (rejected with a cycle diagnostic) | `f09222a` |

Regression coverage was added in `f817459`: 21 pure-Python tests in
`tests/test_p6_remediation.py` and 11 Mindustry v160.7 JVM tests in
`tests/test_p6_remediation_jvm.py`.

---

## 2. Reproduction Method

Every finding was reproduced against baseline `0896679` before the fix and
re-run on the fixed tree with the same harness. Evidence is captured in:

- `scratch/p6_before_evidence.txt`
- `scratch/p6_after_evidence.txt`
- `scratch/p6_corpus_metrics_before.txt`
- `scratch/p6_corpus_metrics_after.txt`

The harness (`scratch/p6_evidence.py`) decompiles or compiles each case, prints
the generated MLog, and executes both the original and the round-tripped program
in the real Mindustry v160.7 JVM engine. Parser or AST acceptance alone was not
treated as success.

The corpus metrics are computed by `scratch/p6_corpus_metrics.py`:

- **Byte-for-byte**: stripped original and recompiled line sequences are equal.
- **Normalized**: parsed `(opcode, operands)` sequences are equal after numeric
  canonicalization of jump targets.
- **Instruction coverage**: fraction of original MLog addresses referenced by at
  least one source-map mapping.
- **JVM state equivalence**: both programs run successfully and final non-temporary
  variables match. A file rejected identically by the engine is reported
  separately rather than counted as a semantic pass.

---

## 3. P6-CRIT-01 - Unconditional Jumps Across Structured Boundaries

### Root cause

`CFGStructurer._structure_range()` treated every jump whose target was greater
than or equal to the current range's `stop_address` as a structured merge
fallthrough. It consumed the jump without emitting anything. That assumption is
only valid when the jump is genuinely the last instruction of the range. In all
other cases it dropped a real control-flow edge:

- A jump past the final instruction is a program terminator. Dropping it made the
  following unreachable instructions execute sequentially.
- A forward jump that crosses a branch boundary is not a merge. Dropping it made
  dead instructions in the branch execute.
- A jump to an unconditional loop latch is semantically a `continue`. Modeling it
  as a plain fallthrough lost the loop restart.

### Fix

`src/decompiler/structurer.py` and `mlog/decompiler/structurer.py` (identical):

1. A jump with `target >= n_instructions` becomes an explicit `end()`
   instruction node. `end` is a real mlog instruction, so it is emitted and
   recompiled without leaving the documented Python subset.
2. A jump to the exclusive end of the current range is consumed only when it is
   the range's final instruction (`curr_addr == stop_address - 1`).
3. Any other jump crossing the enclosing boundary is preserved as an
   `UnstructuredNode` with the original jump instruction.
4. A jump to a loop latch whose final instruction is an unconditional
   `jump <header>` becomes `ContinueNode` (`continue`).

The new helper `_is_loop_latch_target()` deliberately rejects conditional
latches: a `continue` there would skip the latch condition and change semantics.

### Before / after evidence

**Program terminator**

Original:

```mlog
set a 1
jump 5 always 0 0
set a 2
set a 3
print a
```

| | Decompiled jump | Recompiled execution |
| --- | --- | --- |
| Before | dropped | `RUN_OK:4`, `a=3.0` |
| After | `end()` | `RUN_OK:2`, `a=1.0` |

Before and after original runtime: `RUN_OK:2`, `a=1.0`. The fixed round trip now
matches.

**Branch boundary**

Original:

```mlog
set x 1
jump 4 equal x 0
jump 7 always 0 0
set dead1 99
set y 2
set z 3
set w 4
print y
print z
```

| | Decompiled branch | Recompiled execution |
| --- | --- | --- |
| Before | jump dropped, `dead1 = 99` reachable | `RUN_OK:8`, `dead1=99.0`, `y=2.0` |
| After | `UnstructuredNode` preserving `jump(7, "always", 0, 0)` | `RUN_OK:5`, all variables `null` |

The fixed output matches the original `RUN_OK:5` and final state exactly.

**`base_manager_120.mlog` source map**

- Before: 119/120 addresses mapped. Address 15 (`jump 19 always 0 0`, jumping to
  the loop latch) was lost. Coverage `0.9917`.
- After: 120/120 addresses mapped. Address 15 maps to a `Continue` node at Python
  line 18. The P5-preserved `ubind("@flare")` and
  `u_flag = sensor('@unit', '@flag')` instructions remain present.

**Round-trip corpus effects**

The fix also made `unreachable_dead_code.mlog`, `irreducible_cfgs.mlog`, and
`spaghetti_goto.mlog` byte-for-byte equal. The latter two previously mismatched
at runtime (`z` and `c` respectively); both now match.

### Regression tests

- `test_program_terminator_emits_end`
- `test_jump_to_final_address_stays_a_terminator`
- `test_branch_boundary_jump_is_preserved_not_consumed`
- `test_loop_latch_jump_becomes_continue_and_keeps_gap_code`
- `test_structured_loops_keep_their_shape`
- `test_jump_at_range_end_is_still_fallthrough`
- JVM: `test_crit01_program_terminator_runtime`,
  `test_crit01_branch_boundary_runtime`,
  `test_crit01_base_manager_loop_exit_runtime`

---

## 4. P6-CRIT-02 - User-Function Return Values in Expressions

### Root cause

The user-function calling convention copies the return value into
`__retval_<fn>`. `Compiler.compile_call()` only emitted a capture when an
explicit `target_dest` was supplied. For every other value-producing call it
returned the literal string `"0"`, so the call result was replaced by zero:

```mlog
# res = inc(4) + 1, before
op add res 0 1
```

Nested calls were worse: each call still stored its result in `__retval_inc`,
but the outer expression had already discarded it, so only the last side effect
survived.

### Fix

`src/compiler.py` and `mlog/compiler.py` (identical):

- When `target_dest` is present, behavior is unchanged: the result is copied
  directly to the destination.
- When a call is value-producing and `is_statement` is false, the result is
  copied to a fresh `__tmpN` and that temporary is returned to the expression.
- A call used only as a statement still returns `"0"` without allocating a
  capture register, preserving the previous instruction footprint.

### Before / after evidence

| Case | Before | After |
| --- | --- | --- |
| `res = inc(4) + 1` | `op add res 0 1`, `res=1.0` | `set __tmp1 __retval_inc; op add res __tmp1 1`, `res=6.0` |
| `res = inc(inc(4))` | `res=1.0` (14 steps) | `res=6.0` (15 steps) |
| `res = twice(3) + add(1, 2)` | `op add res 0 0`, `res=0.0` | two captures, `res=9.0` |
| `return inc(inc(x))` | inner results discarded | both inner results captured; outer return intact |
| `bump(3)` as a statement | no capture | still no `set __tmpN __retval_bump` |
| `res = inc(4)` | `set res __retval_inc` | unchanged |

All before values were observed in Mindustry v160.7, not inferred from the
generated text.

### Regression tests

- `test_call_in_binary_expression_captures_retval`
- `test_nested_call_captures_each_result`
- `test_multiple_calls_in_one_expression`
- `test_call_in_return_statement_captures_retval`
- `test_statement_only_call_does_not_allocate_a_capture`
- `test_target_dest_call_is_unchanged`
- JVM: `test_crit02_call_in_expression_runtime`,
  `test_crit02_nested_call_runtime`,
  `test_crit02_multiple_calls_in_expression_runtime`,
  `test_crit02_call_inside_return_runtime`,
  `test_crit02_decompiled_call_expression_recompiles_and_runs`

---

## 5. P6-CRIT-03 - Source-Map Jump Operand Formatting

### Root cause

The plain decompiler formatted `UnstructuredNode` jump operands through the
metadata-driven `format_semantic_argument()` helper. `SourceMapEmitter` had a
separate implementation using `repr()` for every operand:

```python
# res = inc(4) + 1, before
args_repr = ", ".join(repr(a) for a in instr.args)
```

For a jump such as `jump 5 greaterThan a 0`, this produced:

```python
jump('5', 'greaterThan', 'a', '0')
```

The target became a string instead of an address, `a` became a string instead of
a variable, and the comparison operands no longer had numeric semantics. In the
JVM this stopped after 7 steps with `c = null`, whereas the original ran 100
steps with `c = 3.0`.

### Fix

`src/decompiler/structured_ir.py` now exposes `format_jump_arguments()`, which
iterates the jump operands and delegates to `format_semantic_argument("jump", ...)`.
Both `UnstructuredNode.to_python()` and `SourceMapEmitter._emit_node()` (in
`src/decompiler/sourcemap.py`) call it. Duplicate formatting logic can no longer
drift between the two paths.

The resulting output is:

```python
jump(5, "greaterThan", a, 0)
```

- Addresses and numeric literals stay numeric.
- Variables stay bare identifiers.
- Condition tokens stay quoted strings.

### Before / after evidence (`spaghetti_goto.mlog`)

| | Source-map output | Recompile | JVM |
| --- | --- | --- | --- |
| Before | `jump('5', 'greaterThan', 'a', '0')` | not byte-equal | `RUN_OK:7`, `c='null'` |
| After | `jump(5, "greaterThan", a, 0)` | byte-for-byte equal | `RUN_OK:100`, `c=3.0` |

The original program runs 100 steps with `a=1.0, b=2.0, c=3.0, d=4.0`.
The fixed source-map output matches it exactly.

### Regression tests

- `test_unstructured_jump_arguments_are_not_quoted`
- `test_source_map_matches_plain_decompilation`
- `test_source_map_jump_output_recompiles_byte_for_byte`
- `test_debug_source_map_output_parses`
- JVM: `test_crit03_source_map_goto_runtime`

---

## 6. P6-HIGH-01 - Recursive User Functions

### Root cause

The compiler's user-function convention stores a single scalar return address per
function in `__ret_<fn>` and a single result in `__retval_<fn>`. There is no
software call stack. A recursive call overwrites the caller's return address, so
the program returns to the wrong site and loops until the instruction limit.

At baseline, direct recursion (`fact`) and indirect recursion (`ping -> pong ->
ping`) both compiled successfully and ran to the 100-step cap with
`result = null`.

### Fix

`src/compiler.py` and `mlog/compiler.py` (identical):

1. `_collect_function_call_sites()` walks each `FunctionDef` after constant
   folding and records calls whose callee is another user-defined function.
2. `_reject_recursive_functions()` runs a three-color DFS over that call graph.
3. A back edge raises `CompileError` at the offending call site with the complete
   cycle path:
   `recursive user function call is not supported: ping -> pong -> ping
   (mlog has no call stack; recursion would overwrite the return address)`.
4. Nested non-recursive calls still compile and run.

The check is intentionally conservative: recursion is rejected until a software
stack exists, rather than emitting silently broken bytecode.

### Before / after evidence

| Case | Before | After |
| --- | --- | --- |
| Direct `fact(5)` | `RUN_OK:100`, `result=null` | `CompileError` at the recursive call |
| Indirect `ping(3)` / `pong` | `RUN_OK:100`, `result=null` | `CompileError`, cycle path `ping -> pong -> ping` |
| Nested non-recursive `outer(4)` | worked by accident | still compiles; `RUN_OK:15`, `result=9.0` |

The two recursive corpus files now assert this contract in
`tests/test_corpus_hardening.py` instead of requiring a successful recompile.
This is an intentional language-contract change, not a reduction in coverage:
the files still exercise decompilation, AST parsing, and the expected rejection
diagnostic.

### Regression tests

- `test_direct_recursion_is_rejected`
- `test_indirect_recursion_is_rejected`
- `test_three_function_cycle_is_rejected`
- `test_nested_non_recursive_calls_still_compile`
- `test_same_name_calls_to_different_scopes_are_not_cycles`
- JVM: `test_high01_nested_non_recursive_calls_runtime`,
  `test_high01_recursion_never_reaches_the_engine`

---

## 7. Corpus Metrics

The corpus contains 32 MLog programs. The two recursive programs are now
rejected by design at compile time. `flare_miner.mlog` is rejected by the real
v160.7 engine in both the original and recompiled forms because its
`ulocate building container 0 @copper ...` statement is not valid for that engine
build; it is reported separately and is not counted as a semantic pass.

### 7.1 Structural and fidelity metrics

| Metric | Baseline `0896679` | After P6 |
| --- | --- | --- |
| Decompile success | 32/32 | 32/32 |
| AST parse success | 32/32 | 32/32 |
| Recompile success | 32/32 | 30/32 (2 recursion rejected) |
| Byte-for-byte equal | 16/32 (16/32 compilable) | 17/32 (17/30 compilable) |
| Normalized instruction equal | 16/32 (16/32 compilable) | 17/32 (17/30 compilable) |
| Instruction coverage mean | 0.9836 | 0.9884 |
| Instruction coverage 100% | 23/32 | 25/32 |

Byte-for-byte gains were `unreachable_dead_code.mlog`, `irreducible_cfgs.mlog`,
and `spaghetti_goto.mlog`. The two recursion files moved from byte-equal before
the fix to "rejected by design" after the fix, which accounts for the net +1.

Source-map coverage reached 100% for `empty_branches.mlog` (0.8571 -> 1.0) and
`base_manager_120.mlog` (0.9917 -> 1.0). Seven function-heavy files still have
known pre-existing source-map gaps (0.9231-0.9756); they are unchanged by P6 and
are listed in section 8.

### 7.2 Runtime semantic equivalence

| Metric | Baseline `0896679` | After P6 |
| --- | --- | --- |
| JVM state equivalence, corpus | 29/32 | 30/32 (2 rejected, 1 engine-invalid) |
| JVM state equivalence, attempted | 29/32 | 30/30 |
| Both valid and equal | 28/32 | 29/30 |

Baseline JVM mismatches were `base_manager_120.mlog` (`bar_w`, `cell_idx`,
`cell_val`, `reg_100`-`reg_102`), `irreducible_cfgs.mlog` (`z`), and
`spaghetti_goto.mlog` (`c`). After P6, there are zero mismatches among programs
that execute. `flare_miner.mlog` remains invalid in both runs and is excluded
from the "both valid" count.

The full execution-time conformance test suite (618 JVM tests, including the 11
new P6 tests) passes.

---

## 8. Remaining Limitations

### 8.1 15 non-byte-equal programs (pre-P7 classification; see correction at top)

Byte-for-byte fidelity is 17/32. The 15 non-byte-equal files after P6 are:

`arithmetic_dataflow`, `large_compiler_program`, `multi_func_math`,
`recursive_factorial`, `empty_branches`, `short_circuit_ladder`, `recursion`,
`base_manager_120`, `flare_miner`, `reactor_safety`, `turret_radar`,
`computed_jump_counter`, `scale_1000_instr`, `scale_100_instr`,
`scale_500_instr`.

`recursive_factorial` and `recursion` are rejected by design; they were
byte-equal before the recursion contract changed. `flare_miner` is rejected by
the engine in both forms. The other 12 are pre-existing expression
reconstruction and temporary-allocation differences, not P6 regressions: all
programs accepted by the engine produce identical final JVM state.

### 8.2 P6-HIGH-02 - loop-exit gap reachability (fixed in P7)

`base_manager_120.mlog` has two instructions (addresses 20-21: `ubind @flare`
and `sensor u_flag @unit @flag`) between the turret loop exit and the next
branch. The original loop exit jumps to address 22, skipping them; the
recompiled loop exits to address 20, executes the binding and sensor, and then
reaches address 22. Final variable state and messages match in the JVM on this
corpus file, but the static set of executed instructions differs, and binding a
unit is an observable side effect.

This is the pre-existing loop-exit gap reachability issue (P6-HIGH-02), not one
of the four requested findings. It is documented here instead of changing P5's
loop-exit logic without a proven general fix. P7 made the recorded exit address
authoritative and found a second gap at `[33, 36)`; see
`p7_remediation_report.md` section 4.

### 8.3 Preamble source-map gap (corrected in P7)

`large_compiler_program` (0.9756), `multi_func_math` (0.9565),
`recursive_factorial` (0.9375), `func_with_loop` (0.9231), `nested_calls`
(0.9412), `recursion` (0.9524), and `two_functions` (0.9412) still do not map
every original address. P7 established that every function-body address is
mapped and that each file misses only address `0`, the structural function-table
preamble. It is now recorded as a coarse `Preamble` mapping, so address coverage
is 100%; statement-level coverage legitimately excludes address `0`.

### 8.4 Recursion remains unsupported

Recursion is rejected rather than compiled. Supporting it requires a software
call stack (heap/stack memory or an explicit frame array), which is a larger
compiler feature and is outside this remediation.

---

## 9. Commits

| Commit | Message |
| --- | --- |
| `90e8139` | `fix(decompiler): preserve unconditional jumps across structured boundaries` |
| `e04941c` | `fix(compiler): capture user-function return values in expressions` |
| `7710605` | `fix(decompiler): format source-map jump operands semantically` |
| `f09222a` | `feat(compiler): reject recursive user functions with a cycle diagnostic` |
| `f817459` | `test(p6): add pure-Python and JVM regression suites` |

Documentation updates are in `docs/compiler.md`, `docs/decompiler.md`,
`docs/source-mapping.md`, `SKILL.md`, and `docs/adr/0003-p6-control-flow-and-recursion-contracts.md`.

---

## 10. Verification

| Command | Result |
| --- | --- |
| `python -m unittest tests.test_p6_remediation` | 21/21 passed |
| `python -m unittest tests.test_p6_remediation_jvm` | 11/11 passed on Mindustry v160.7 |
| `python run_tests.py --fast` | 850/850 passed |
| `python run_tests.py --jvm` | 618/618 passed |
| `python run_tests.py --all` | 1468/1468 passed |
| `git diff --check` | clean |
| `python -m unittest tests.test_agent_memory` | handoff schema passes |
| `src/` vs `mlog/` synchronization | compiler and decompiler copies identical (only `semantics.py` import style differs, as intended) |

No metadata changed, so `mlog.pyi` and `src/mlog.pyi` were not regenerated.

### Verdict

All four requested P6 findings are fixed, covered by pure-Python and real-engine
regression tests, and verified against the full suite. The remaining fidelity and
source-map gaps are pre-existing, listed above, and do not produce runtime state
differences for programs accepted by the v160.7 engine.
