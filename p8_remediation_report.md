# P8 Remediation Report: Redundant `while True` Guard Elimination (P8-REM-01)

- **Date:** 2026-11-07
- **Baseline Commit:** `12580fc1fe296faf7e68a5a9c7c218a59cc1ebcd`
- **Target Engine:** Mindustry v160.7 (official release source tree at `D:\Anzuno\Mindustry-source`)
- **Status:** Complete & Verified

---

## 1. Executive Summary

P8 remediation addresses the primary finding of the P8 fidelity audit ([p8_residual_fidelity_audit.md](p8_residual_fidelity_audit.md)): five of the eight residual non-byte-identical corpus files (`flare_miner`, `turret_radar`, `scale_100_instr`, `scale_500_instr`, `scale_1000_instr`) shared an identical root cause in `compiler.py:compile_while`.

When compiling `while True:` or compile-time constant true loops, the compiler evaluated the condition as a generic expression, emitting an always-false conditional exit guard:
```mlog
jump <while_end> equal true 0
```
Because `true == 0` is always false in Mindustry Logic, this jump was never taken. However, it introduced:
1. An extra instruction (+1 instruction count).
2. Dynamic trace divergence (executing the redundant comparison once per loop iteration).
3. Measurable timing divergence in `turret_radar` (200 ticks reduced to 190 ticks under the 300-step cap because an extra instruction executed before `wait 0.2` yielded each tick).
4. Cascading absolute jump target shifts across all downstream dead-code instructions in `scale_100`, `scale_500`, and `scale_1000` (creating up to 1,610 diff lines).

### Key Remediation Results:
- **Optimization:** Added compile-time constant true detection in `Compiler.compile_while`, suppressing the redundant conditional exit guard.
- **Corpus Byte-Identical:** Increased from **22/30 (73.33%)** to **27/30 (90.00%)** (+5 files, +16.67%).
- **Corpus Trace Equality:** Increased from **22/30 (73.33%)** to **27/30 (90.00%)** (+5 files, +16.67%).
- **Timing Restored:** `turret_radar` tick count at 300 steps is restored from 190 ticks to exactly **200 ticks** (100% match with original).
- **Scale Files Resolved:** `scale_100`, `scale_500`, and `scale_1000` are now 100% byte-identical and trace-equal (diff lines reduced from 113, 815, 1,610 to **0**).
- **Safety:** Dynamic conditions (`while x < 10:`), constant false (`while False:`, `while 0:`), expressions with side effects, and `break`/`continue`/`else` control flow remain 100% preserved.

---

## 2. Root Cause and Implementation

### 2.1 Root Cause
In `src/compiler.py` and `mlog/compiler.py`, `compile_while` handled all loop conditions unconditionally:
```python
# Before
self.instructions.append(IRLabel(name=while_start, loc=loc))
self._loop_stack.append((while_start, while_end))
self.compile_condition(node.test, true_label=None, false_label=while_orelse)
for stmt in node.body:
    self.compile_stmt(stmt)
```
For `while True:`, `compile_condition` lowered `ast.Constant(value=True)` via generic truthiness check, emitting `IRJump(target=while_orelse, cond="equal", a="true", b="0")`.

### 2.2 Fix Implementation
1. Added helper function `_is_constant_true(node: ast.AST) -> bool` in both `src/compiler.py` and `mlog/compiler.py`:
   - Leverages existing `_extract_const_val(node)` to extract compile-time literals without side effects.
   - Returns `True` if `val is True` or if `val` is a non-zero numeric literal (`int` or `float`).
   - Also handles pure logical `not` on constant false/zero literals (`not False`, `not 0`).
   - Rejects strings, `None`, variables, calls, and dynamic expressions.
2. In `compile_while`, gated condition compilation:
   ```python
   # After
   self.instructions.append(IRLabel(name=while_start, loc=loc))
   self._loop_stack.append((while_start, while_end))

   # Compile condition: if false, jump to while_orelse (or while_end if no orelse).
   # When condition is proven pure compile-time constant true, omit the redundant guard.
   if not _is_constant_true(node.test):
       self.compile_condition(node.test, true_label=None, false_label=while_orelse)

   for stmt in node.body:
       self.compile_stmt(stmt)
   ```
3. Kept `src/compiler.py` and `mlog/compiler.py` 100% synchronized (SHA-256 verified).

---

## 3. Regression Test Coverage

Added 24 new regression tests (16 pure unit tests + 8 JVM integration tests):

### 3.1 Pure Compiler Tests (`tests/test_p8_remediation.py`)
- `test_while_true_omits_redundant_guard`: Verifies `while True:\n x = 1` compiles to `["set x 1", "jump 0 always 0 0"]`.
- `test_while_literal_int_non_zero_omits_guard`: Verifies `while 1:` emits no exit guard.
- `test_while_constant_expr_folded_omits_guard`: Verifies `while 1 == 1:`, `while not False:`, `while True and True:`, and `while 1 != 0:` emit no guard.
- `test_while_false_preserves_guard`: Verifies `while False:` compiles to `jump 3 equal false 0` to skip the body.
- `test_while_zero_preserves_guard`: Verifies `while 0:` preserves `jump 3 equal 0 0`.
- `test_while_dynamic_condition_preserves_guard`: Verifies `while x < 10:` preserves condition `jump 3 greaterThanEq x 10`.
- `test_while_true_break_semantics`: Verifies `break` jumps past the loop without instruction count off-by-one.
- `test_while_true_continue_semantics`: Verifies `continue` jumps directly back to address 0 (`while_start`).
- `test_nested_while_loops`: Verifies loop stack labels and targets for nested while loops.
- `test_while_true_with_else_block`: Verifies while-else structure is preserved.
- `test_flare_miner_byte_identical`: Recompiled mlog matches original byte-for-byte.
- `test_turret_radar_byte_identical`: Recompiled mlog matches original byte-for-byte.
- `test_scale_100_byte_identical`: Recompiled mlog matches original byte-for-byte.
- `test_scale_500_byte_identical`: Recompiled mlog matches original byte-for-byte.
- `test_scale_1000_byte_identical`: Recompiled mlog matches original byte-for-byte.
- `test_out_of_scope_files_remain_unmodified_behavior`: Asserts `large_compiler_program`, `multi_func_math`, and `empty_branches` maintain their expected behavior.

### 3.2 JVM Runtime Tests (`tests/test_p8_remediation_jvm.py`)
- `test_turret_radar_jvm_exact_ticks_and_state`: Verifies exact tick equality on Mindustry v160.7 JVM (both run at 200 ticks at 300 steps).
- `test_flare_miner_jvm_exact_trace_and_state`: Verifies 300 steps, 38 ticks, `bound_unit='flare'`, `flag=1.0`, `item=0.0`.
- `test_scale_100_jvm_exact_state`: Verifies 300 steps, 38 ticks, `acc=8.001953125`, `i=10.0`.
- `test_scale_500_jvm_exact_state`: Verifies 300 steps, 38 ticks, `acc=8.001953125`, `i=10.0`.
- `test_scale_1000_jvm_exact_state`: Verifies 300 steps, 38 ticks, `acc=8.001953125`, `i=10.0`.
- `test_while_true_break_jvm`: Verifies runtime termination and variable mutation on JVM.
- `test_while_false_skipped_jvm`: Verifies loop body is not entered at runtime on JVM.
- `test_while_dynamic_condition_jvm`: Verifies dynamic while condition executes correct number of iterations.

### 3.3 Updated Existing Expectations
- `tests/test_phase1f.py:test_14_backward_jump`: Updated expected output from `["jump 3 equal true 0", "op add i i 1", "jump 0 always 0 0"]` to `["op add i i 1", "jump 0 always 0 0"]`.
- `tests/test_decompiler_loops.py`:
  - `test_loop_header_with_read_side_effect`: Updated `jump 8 always 0 0` expectation to `jump 7 always 0 0` (now exactly matches original mlog address).
  - `test_loop_header_with_sensor_side_effect`: Updated `jump 6 always 0 0` expectation to `jump 5 always 0 0`.

---

## 4. Corpus Metrics Comparison: P8 Baseline vs P8 Remediation

All metrics evaluated across all 32 files in `tests/corpus/` on Mindustry v160.7 JVM:

| Metric | P8 Baseline (Audit) | P8 Remediation (Final) | Delta | Scope / Denominator |
|---|---|---|---|---|
| **Decompile Success** | 32 / 32 (100.0%) | **32 / 32** (100.0%) | 0 | 32 total files |
| **AST Parse Success** | 32 / 32 (100.0%) | **32 / 32** (100.0%) | 0 | 32 total files |
| **Recompile Success** | 30 / 32 (93.75%) | **30 / 32** (93.75%) | 0 | 32 total files (2 recursion rejected by design) |
| **Recompile (Runnable)** | 30 / 30 (100.0%) | **30 / 30** (100.0%) | 0 | 30 non-recursive files |
| **Recursion Rejection** | 2 / 2 (100.0%) | **2 / 2** (100.0%) | 0 | 2 recursive files (ADR-003/004) |
| **Byte-Identical** | 22 / 30 (73.33%) | **27 / 30** (90.00%) | **+5 (+16.67%)** | 30 compilable runnable files |
| **Normalized Equality** | 22 / 30 (73.33%) | **27 / 30** (90.00%) | **+5 (+16.67%)** | 30 compilable runnable files |
| **Address Coverage** | 2,095 / 2,095 (100.0%) | **2,095 / 2,095** (100.0%) | 0 | 2,095 instructions across 32 files |
| **Statement Coverage** | 2,088 / 2,095 (99.67%) | **2,088 / 2,095** (99.67%) | 0 | Missing addr 0 in 7 function files by design |
| **Execution Trace Equality** | 22 / 30 (73.33%) | **27 / 30** (90.00%) | **+5 (+16.67%)** | 30 runnable files on JVM |
| **Final State Equality** | 30 / 30 (100.0%) | **30 / 30** (100.0%) | 0 | 30 runnable files on JVM |

---

## 5. Detailed Evidence on Remediated Files

| File | Before Remediation | After Remediation | JVM Validation Evidence |
|---|---|---|---|
| `handwritten/flare_miner.mlog` | 16 instrs (extra `jump 16 equal true 0`); trace offset | **15 instrs**; byte-identical; trace-identical | 300 steps, 38 ticks, `flare` bound, `flag=1.0`, `item=0.0`. Exact PC trace match. |
| `handwritten/turret_radar.mlog` | 15 instrs; 190 ticks at 300 steps | **14 instrs**; byte-identical; trace-identical | 300 steps, **200 ticks** (exact match with orig 200 ticks), `dead=1.0`. Exact PC trace match. |
| `pathological/scale_100_instr.mlog` | 101 instrs; 113 diff lines | **100 instrs**; byte-identical; trace-identical | 300 steps, 38 ticks, `acc=8.001953125`, `i=10.0`. 0 diff lines. |
| `pathological/scale_500_instr.mlog` | 501 instrs; 815 diff lines | **500 instrs**; byte-identical; trace-identical | 300 steps, 38 ticks, `acc=8.001953125`, `i=10.0`. 0 diff lines. |
| `pathological/scale_1000_instr.mlog` | 981 instrs; 1,610 diff lines | **980 instrs**; byte-identical; trace-identical | 300 steps, 38 ticks, `acc=8.001953125`, `i=10.0`. 0 diff lines. |

---

## 6. Remaining Residual Differences (Out of Scope)

Only 3 compilable files remain non-byte-identical, all confirmed semantically equivalent:
1. `compiler_generated/large_compiler_program.mlog`:
   - Difference: Commutative independent assignments (`set a s1; set b z` vs `set b z; set a s1`) at address 17-18.
   - Classification: `EQUIVALENT_LAYOUT`.
   - JVM State: 300 steps, 38 ticks, 100% equal variables (`acc=224`, `i=8`).
2. `compiler_generated/multi_func_math.mlog`:
   - Difference: Inverted clamp condition (`jump 8 greaterThanEq val low` vs `jump 9 lessThan val low`).
   - Classification: `TRACE_DIVERGENCE`.
   - JVM State: 3 ticks, 100% equal return values across all domain partitions (`< low`, `> high`, `in-range`).
3. `control_flow/empty_branches.mlog`:
   - Difference: Terminal instruction `jump 7 always 0 0` (EOF jump) lowered to canonical `end`.
   - Classification: `EQUIVALENT_LAYOUT`.
   - JVM State: 6 steps, 1 tick, 100% equal variables across all input domains (`val <= 100`, `val > 100`).

---

## 7. Limitations

1. **Recursion Contract (Unchanged):** `recursive_factorial.mlog` and `recursion.mlog` remain rejected at compile time by design per ADR-003 and ADR-004.
2. **Equivalent Layout Retention:** `large_compiler_program` and `empty_branches` maintain high-level Python DSL representations rather than hardcoding compiler instruction order.

---

## 8. Verification Commands Run

All commands executed cleanly on Windows 11 against Mindustry v160.7 engine:

```text
python -m unittest tests.test_p8_remediation
  -> Ran 16 tests in 1.11s, OK

python -m unittest tests.test_p8_remediation_jvm
  -> Ran 8 tests in 11.71s, OK

python -m unittest tests.test_p7_remediation tests.test_p7_remediation_jvm
  -> Ran 31 tests in 13.91s, OK

python -m unittest tests.test_p8_remediation tests.test_p8_remediation_jvm
  -> Ran 24 tests in 12.87s, OK

python run_tests.py --fast
  -> Ran 887 tests in 79.47s, OK (skipped=3)

python run_tests.py --jvm
  -> Ran 637 tests in 51.52s, OK

python run_p8_corpus_metrics.py
  -> 32/32 decompile, 30/32 recompile, 27/30 byte-identical (90.00%), 27/30 trace-equal (90.00%), 30/30 final-state equal (100.00%)
```
