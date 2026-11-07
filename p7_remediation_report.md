# P7 Remediation Report

- **Date**: 2026-11-07
- **Baseline**: `54179b5a7a34260d299465b0dbc56a14083f731e`
  (`docs(p6): record remediation report and control-flow contracts`)
- **Audit**: `p7_fidelity_audit.md`
- **Engine**: Mindustry v160.7 (real `LExecutor` through the JVM tier)
- **Scope**: P7-CRIT-01, P7-CRIT-02, P7-HIGH-01, P7-MED-01, P7-MED-02,
  P7-LOW-01, P7-LOW-02
- **Status**: All P7 code and corpus findings fixed. The remaining layout and
  timing differences are documented in section 9; this report does not claim
  100% trace or byte fidelity.

---

## 1. Executive Summary

| Finding | Severity | Failure mode at baseline | Status | Commit |
| --- | --- | --- | --- | --- |
| P7-CRIT-01 | Critical | A conditional inside a then-body whose false edge targeted the enclosing else entry became a one-sided nested `if`; the else edge was dropped. | Fixed | `fde8a92` |
| P7-CRIT-02 | Critical | Bare `@` registers in value positions were emitted as Python strings, so recompilation read string objects instead of live registers. | Fixed | `fde8a92` |
| P7-HIGH-01 | High | A loop exit that skipped instructions resumed at `max_body_address + 1`; the skipped gap executed after recompilation. | Fixed | `fde8a92` |
| P7-MED-01 | Medium | Address 0 (function-table preamble) had no source mapping. | Fixed | `fde8a92` |
| P7-MED-02 | Medium | `FunctionDef` mappings duplicated every body address and inflated coverage counts. | Fixed | `fde8a92` |
| P7-LOW-01 | Low | Benign reordering/layout/timing differences remain in 8 files. | Documented, not eliminated | — |
| P7-LOW-02 | Low | `base_manager_120` never exited its turret loop; `flare_miner` used an invalid `ulocate` group. | Fixed | `44952f4` |

Regression coverage:

- `tests/test_p7_remediation.py`: 20 pure-Python tests.
- `tests/test_p7_remediation_jvm.py`: 11 Mindustry v160.7 JVM tests.
- Existing P5/P6 and decompiler tests were updated where the corrected output
  intentionally changed (`raw("@...")` registers, corrected loop fixtures).

Final suite results:

```text
python run_tests.py --fast  -> Ran 871 tests, OK (skipped=3)
python run_tests.py --jvm   -> Ran 629 tests, OK
python run_tests.py --all   -> Ran 1500 tests, OK (skipped=3)
```

---

## 2. Method and Metrics

The audit used the public API:

```python
from mlog.decompiler import decompile_with_source_map
from mlog import compile_py

py, source_map = decompile_with_source_map(original_mlog, filename=path)
recompiled = compile_py(py, allow_functions=True, validate=True).mlog
```

Execution used a copy of the Mindustry harness kept outside the repository at
`C:\Users\Admin\AppData\Local\Temp\opencode\p7-trace`. The harness prints
`TRACE:<step>:<pc>` immediately before each `runOnce()`, so the trace is the
exact dynamic instruction sequence. It runs Mindustry v160.7 on a synthetic
100x100 world containing one processor, a message block, a memory cell, a
display, and test buildings.

Metric definitions:

- **Decompile**: the program produces parseable Python.
- **Recompile**: the Python compiles back to mlog (`allow_functions=True`).
- **Byte-identical**: stripped original and recompiled line sequences are
  equal.
- **Normalized**: parsed `(opcode, operands)` sequences are equal after numeric
  canonicalization.
- **Address coverage**: every original instruction address has at least one
  source-map mapping, including coarse container mappings.
- **Statement coverage**: every address has a non-coarse statement mapping.
- **Trace equality**: equal `(step, pc)` sequence, not only equal final state.
- **Final state**: variables, messages, text buffer, display command counts,
  and bound unit after the step cap.

The 300-step cap was used for corpus runs. Recursion is rejected by design, so
the two recursive corpus files are excluded from runtime comparisons.

---

## 3. P7-CRIT-01: Dropped Else Edge

### 3.1 Root cause

`CFGStructurer._structure_range()` treated a conditional jump inside a
then-body that targeted `stop_address + 1` as an enclosing branch boundary. It
emitted an `IfNode` with `else_body=[]` and advanced `curr_addr` to the stop
address, while the caller had already structured the target address as the
enclosing `if`'s else body. The nested `if` therefore lost its false edge.
The compiler faithfully reproduced the wrong structure.

### 3.2 Fix

`mlog/decompiler/structurer.py` and `src/decompiler/structurer.py` (identical):

1. If the then-region is exactly a chain of deferred conditionals whose false
   edges all target the enclosing else entry, flatten the chain into one
   combined condition: `if outer and inner: ... else: ...`. No statement runs
   between the conditions, so this preserves evaluation order.
2. If any statement interleaves with the chain, flattening would change
   execution order. The conditional jump is preserved as an `UnstructuredNode`
   and the remaining statements stay in address order. The false edge still
   reaches the enclosing else entry.

The choice depends only on CFG/address structure, never on guessed purity.

### 3.3 JVM evidence

`arithmetic_dataflow`, variant `set a 30` (x=682, y=2182):

```text
before original : 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 19   res=0.0
before recompiled: 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 18   res=null
after  original : 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 19   res=0.0
after  recompiled: 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 19   res=0.0
```

`short_circuit_ladder`, variant `set a 5`, `set d 5`:

```text
before original : 0 1 2 3 4 5 7 8 11    flag=-1.0
before recompiled: 0 1 2 3 4 5 7 8 10   flag=0.0
after  both     : 0 1 2 3 4 5 7 8 11    flag=-1.0
```

`reactor_safety`, variant `heat=0.5`, `cryo=20`:

```text
before original : 0 1 2 3 5 6 7 8           8 steps, 1 tick   ALERT
before recompiled: 0 1 2 3 4 9 10 11 12     9 steps, 2 ticks  Nominal
after  both     : 0 1 2 3 5 6 7 8           8 steps, 1 tick   ALERT
```

Decompiled forms after the fix:

```python
# arithmetic_dataflow variant
if y > 100 and x < 500:
    res = 1
else:
    res = 0

# short_circuit_ladder variant
# [UNSTRUCTURED REGION]
jump(9, "lessThan", b, c)
if c < d and d == 4:
    flag = 1
else:
    flag = op("sub", 0, 1)

# reactor_safety variant
if cryo >= 10 and heat <= 0.2:
    pass
else:
    control.enabled("reactor1", 0)
    print("ALERT: Reactor Overheating")
    printflush("message1")
    end()
```

A synthetic case with a statement between the two conditionals verifies the
materialization path: the deferred conditional is emitted as a raw jump to the
enclosing else entry, and the test asserts the exact recompiled instruction
stream.

All three variants are byte-identical after the fix and execute the same PC
sequence as their originals.

---

## 4. P7-CRIT-02: Bare `@` Registers

### 4.1 Root cause

`format_operand()` and `ConstantExpr.to_python()` emitted every token starting
with `@` through `repr()`. A bare `@counter`, `@time`, or `@unit` therefore
became a Python string, which recompiled to a quoted mlog string object rather
than the live register. The parser preserves the distinction between a bare
token and `"@..."`, so the two cases are separable.

### 4.2 Fix

- `format_operand()` emits `raw("@...")` for bare `@` tokens in generic value
  positions (`set` values, `op` source operands, jump conditions).
- `ConstantExpr.to_python()` emits `raw("@...")` only when `raw_str` is not a
  quoted literal.
- `set` register destinations use `raw()` as well; non-identifier quoted
  destinations remain valid Python string arguments.
- Intrinsic argument positions such as `sensor("reactor1", "@heat")` keep their
  existing quoted form because the compiler restores registry tokens.

### 4.3 JVM evidence

`computed_jump_counter`:

```text
before original : 0 1 4 5 6 7 8    r=2.0   message1="2"
before recompiled: 0 1 3 6 7 8    r=2.0   (wrong path; skipped side effects)
after  both     : 0 1 4 5 6 7 8    r=2.0   message1="2"
```

The recompiled destination was already normalized back to `@counter`, but the
source operand was a string whose numeric value is 1. The original reads the
live counter value (2 after fetch) and computes `2 + 2 = 4`; the broken form
computed `1 + 2 = 3`.

Register cases:

| Case | Before | After |
| --- | --- | --- |
| `set x @counter` | `x = '@counter'`, message `@counter` | `x = raw("@counter")`, `x=1.0`, message `1` |
| `op add x @time 1` | `x = '@time' + 1`, `x=2.0` | `x = raw("@time") + 1`, `x=1.0` |
| `jump 2 equal @unit null` | trace `0 1 2`, string comparison | trace `0 2`, live register comparison |
| `ubind @flare`; `set u @unit` | `u="@unit"` | `u="flare"` |
| `set x "@foo"` | Python string | still a Python string |

All register cases now produce byte-identical recompiled mlog and equal final
state.

---

## 5. P7-HIGH-01: Loop-Exit Gap

### 5.1 Root cause

`CFGStructurer` computed each loop's `exit_address` correctly but resumed
sequential structuring at `max_body_address + 1`. When the exit address skipped
instructions, the recompiled `while` false edge landed at the gap start, so the
gap executed. `base_manager_120` has two gaps:

- `[20, 22)`: `ubind @flare`, `sensor u_flag @unit @flag`
- `[33, 36)`: `draw clear`, `draw color`, `op mul bar_w power_ratio 80`

A structured `while` cannot express "exit past a non-contiguous block". The
zero-guessing contract requires a raw representation.

### 5.2 Fix

When `loop.exit_address > loop.max_body_address + 1`, the structurer emits the
entire loop region from the current address up to `exit_address` as an
`UnstructuredNode` and resumes structuring exactly at `exit_address`. The raw
region keeps every instruction, guard, latch, and target visible; the skipped
gap is unreachable on the exit path. The check is address-driven; no file,
address, or instruction pattern is hardcoded.

### 5.3 JVM evidence

Operand-only variant
`op div t_hp_ratio 1 10` (makes `t_hp_ratio = 0.1`):

```text
before original : ... 13 18 19 8 22 23 24 25 ...        178 steps, 23 ticks
before recompiled: ... 13 18 19 8 20 21 22 23 24 25 ... 183 steps, 23 ticks
before state     : bound=null, u_flag=null, bar_w=null
before recompiled: bound=flare, u_flag=0.0, bar_w=0.0

after  both      : ... 13 18 19 8 22 23 24 25 ...        178 steps, 23 ticks
after  state     : bound=null, u_flag=null, bar_w=null
```

Committed corpus input after the P7-LOW-02 fix:

```text
original : RUN_OK:184, 23 ticks, turret_idx=4.0, cell_idx=8.0,
           message1="Status: Nominal", bound=null
recompiled: same
trace_equal: 184/184 PCs
```

The source map covers both raw gap regions and all 120 instructions.

---

## 6. P7-MED-01 and P7-MED-02: Source Maps

### 6.1 Address 0 and coarse container mappings

- Address 0 (the function-table preamble jump) now has a coarse `Preamble`
  mapping. It resolves to the first function line rather than an invented
  executable statement.
- `FunctionDef` mappings are marked `is_coarse=True`. They span the full
  function body for navigation but no longer count as statement-level
  provenance.
- `SourceMap.mlog_to_python()` prefers the smallest non-coarse mapping, so a
  body address resolves to its precise `Return`/`Call`/`Assign` statement.
- New helpers: `mapped_addresses(include_coarse=...)`,
  `missing_addresses(total, include_coarse=...)`, and
  `coverage_summary(total)`.

### 6.2 Coverage results

Across the 32-file corpus (2095 instructions):

| Metric | Baseline | Final |
| --- | ---: | ---: |
| Addresses mapped | 2088/2095 (99.67%) | 2095/2095 (100%) |
| Files with full address coverage | 25/32 | 32/32 |
| Statement-level addresses mapped | 2088/2095 (99.67%) | 2088/2095 (99.67%) |
| Files with full statement coverage | 25/32 | 25/32 |

The seven function-bearing files miss exactly address 0 at statement level:
`large_compiler_program`, `multi_func_math`, `recursive_factorial`,
`func_with_loop`, `nested_calls`, `recursion`, and `two_functions`. Every
function-body address is mapped. Counting `FunctionDef` ranges as statements
previously hid this distinction and overstated precision.

---

## 7. P7-LOW-02: Corpus Corrections

### 7.1 `base_manager_120.mlog`

Address 15 was `jump 19 always 0 0`, so the `t_hp_ratio >= 0.4` path skipped
`op add turret_idx turret_idx 1` and looped until the step cap. The counter
increment is now reachable from both paths:

```mlog
13 jump 18 lessThan t_hp_ratio 0.4
14 control shoot t_block 0 0 1 0
15 jump 18 always 0 0
16 control shoot t_block 0 0 0 0
17 control enabled t_block 1 0 0 0
18 op add turret_idx turret_idx 1
19 jump 8 always 0 0
```

Before: `RUN_OK:300`, `turret_idx=0.0`, loop never exits.
After: `RUN_OK:184`, 23 ticks, `turret_idx=4.0`, `cell_idx=8.0`,
`message1="Status: Nominal"`, trace equal and byte-identical.

### 7.2 `flare_miner.mlog`

`ulocate building container` is rejected by Mindustry v160.7 as an
`InvalidStatement`; `storage` is the valid building group. The instruction is
now:

```mlog
ulocate building storage 0 @copper cx cy found cblock
```

Before: both original and recompiled forms failed at that line, so runtime
fidelity was unverifiable.
After: both run `RUN_OK:300`, bind a flare, and reach the same final variables,
messages, and display state. The recompiled form still has one extra leading
`jump 16 equal true 0` guard (the benign P7-LOW-01 layout difference), so the
PC trace is not identical.

---

## 8. Corpus Metrics: Baseline to Final

The 32-file corpus was re-run with the exact trace harness. The two recursive
files are rejected by design; the remaining 30 recompile.

| Metric | Baseline `54179b5` | Final |
| --- | ---: | ---: |
| Decompile to Python | 32/32 | 32/32 |
| Recompile | 30/32 | 30/32 |
| Byte-identical | 17/30 | **22/30** |
| Normalized equal | 17/30 | **22/30** |
| Full address coverage | 25/32 | **32/32** |
| Trace-equal | 19/30 (19/29 engine-valid) | **22/30** |
| Final-state equal | 29/29 engine-valid (flare invalid) | **30/30 (flare now valid)** |

Byte-identical gains: `arithmetic_dataflow`, `short_circuit_ladder`,
`base_manager_120`, `reactor_safety`, and `computed_jump_counter`.

Trace-equality gains: `arithmetic_dataflow`, `base_manager_120`, and
`computed_jump_counter`. `short_circuit_ladder` and `reactor_safety` were
already trace-equal on the committed inputs but failed on valid operand
variants; both variants now pass.

The five dropped-else/register variants, the base-manager ratio variant, and
all register cases were re-run with exact traces and are now equal:

```text
arithmetic a=30       18/18 PCs, res=0.0
short a=5 d=5          9/9 PCs, flag=-1.0
reactor heat=0.5       8/8 PCs, ALERT
base manager ratio   178/178 PCs, u_flag=null, bar_w=null, bound=null
computed jump          7/7 PCs, r=2.0, message "2"
set @counter           3/3 PCs, x=1.0
op @time               3/3 PCs, x=1.0
jump @unit             2/2 PCs, x=2.0
ubind @unit            4/4 PCs, u="flare"
```

---

## 9. Remaining Differences

Eight compiled files are not byte-identical and have different PC traces. All
have equal final state on the tested inputs.

| File | Difference | Risk |
| --- | --- | --- |
| `large_compiler_program` | Two independent assignments (`set a s1`, `set b z`) swapped at 17/18. | None on tested input. |
| `multi_func_math` | `clamp` condition inverted (`greaterThanEq` to `lessThan`), branch layout swapped; all three paths return the same value. | None on tested input. |
| `empty_branches` | Final `jump 7 always` replaced by `end`; address 7 is program end. | None. |
| `flare_miner` | Extra leading `jump 16 equal true 0` guard; 15 -> 16 instructions. Both run 300 steps and 38 ticks. | Always-false guard; trace offset only. |
| `turret_radar` | Extra leading `jump 15 equal true 0` guard; 14 -> 15 instructions. | Timing at instruction budget; ticks 200 -> 190 at the 300-step cap. |
| `scale_100_instr` | Extra `while True` guard; +1 instruction. | Timing/`@tick` observable. |
| `scale_500_instr` | Extra `while True` guard; +1 instruction. | Timing/`@tick` observable. |
| `scale_1000_instr` | Extra `while True` guard; +1 instruction. | Timing/`@tick` observable. |

These are layout/timing differences, not semantic final-state differences. They
are visible to programs that inspect `@tick` or hit an instruction budget, so the
decompiler does not claim full trace fidelity. Eliminating them would require
modeling instruction-budget and tick timing in the structurer; that is outside
this remediation.

Recursion remains intentionally unsupported: `recursive_factorial` and
`recursion` fail with the documented diagnostic because mlog has no call stack.

---

## 10. Verification

Commands run on the final tree:

```text
python run_tests.py --fast
  -> Ran 871 tests, OK (skipped=3)

python run_tests.py --jvm
  -> Ran 629 tests, OK

python run_tests.py --all
  -> Ran 1500 tests, OK (skipped=3)

python -m unittest tests.test_p7_remediation
  -> Ran 20 tests, OK

python -m unittest tests.test_p7_remediation_jvm
  -> Ran 11 tests, OK

python -m unittest tests.test_p6_remediation_jvm tests.test_p7_remediation_jvm
  -> Ran 22 tests, OK
```

Additional checks:

- `git diff --check`: clean.
- `mlog/decompiler/{expression,sourcemap,structured_ir,structurer}.py` and
  `src/decompiler/` counterparts are byte-identical (SHA-256 matched).
- No metadata or opcode registry change, so generated stubs were not
  regenerated.
- The 32-file corpus was decompiled, recompiled, source-mapped, and executed
  with exact traces as reported above.

---

## 11. Files Changed

Code:

- `mlog/decompiler/structurer.py`, `src/decompiler/structurer.py`
- `mlog/decompiler/structured_ir.py`, `src/decompiler/structured_ir.py`
- `mlog/decompiler/expression.py`, `src/decompiler/expression.py`
- `mlog/decompiler/sourcemap.py`, `src/decompiler/sourcemap.py`

Tests:

- `tests/test_p7_remediation.py` (new)
- `tests/test_p7_remediation_jvm.py` (new)
- `tests/test_p5_remediation.py`, `tests/test_p6_remediation.py`,
  `tests/test_corpus_hardening.py`, `tests/test_decompiler_*.py`,
  `tests/test_semantic_argument_recovery.py`, `tests/test_tier3_runtime.py`
- `tests/corpus/handwritten/base_manager_120.mlog`
- `tests/corpus/handwritten/flare_miner.mlog`
- `run_tests.py` (JVM module registration)

Examples and docs:

- `examples/decompiler/block_vs_variable.py`,
  `examples/decompiler/reactor_safety.py`,
  `examples/decompiler/special_constants.py`
- `docs/decompiler.md`, `docs/source-mapping.md`,
  `docs/semantic-arguments.md`, `SKILL.md`
- `docs/adr/0004-p7-decompiler-fidelity-contracts.md` and
  `docs/adr/README.md`
- `p7_fidelity_audit.md` and this report
- `docs/adr/0003-p6-control-flow-and-recursion-contracts.md` and
  `p6_remediation_report.md` (P6 claims corrected where P7 disproved them)

Commits:

| Commit | Message |
| --- | --- |
| `fde8a92` | `fix(decompiler): remediate P7 fidelity defects` |
| `49cc70f` | `test(p7): cover fidelity regressions and update register expectations` |
| `44952f4` | `test(p7): correct corpus defects and extend low-02 coverage` |

Documentation, audit, report, and handoff changes are committed as the
accompanying docs commit.

---

## 12. Limitations

- The JVM harness uses a synthetic world, not a real save. Gameplay-level
  behavior (enemy AI, waves, multiplayer) was not tested.
- Trace equality is established within the 300-step cap. It does not prove
  termination equivalence for arbitrary inputs.
- Operand variants are synthetic but valid mlog. They prove the fixed defects
  are input-dependent; they do not enumerate every possible input.
- The trace harness is external to the repository and is not part of CI; the
  in-repo JVM tests compare run length, ticks, variables, messages, text buffer,
  displays, and bound unit.
- `flare_miner` and the `scale_*`/`turret_radar` programs retain an always-false
  leading guard. This is semantically benign on the tested inputs but is
  observable in traces and timing.
- Statement-level source coverage intentionally excludes address 0 in the seven
  function files because no Python statement executes the function-table
  preamble. Address-level coverage includes it through a coarse `Preamble`
  mapping.
- The corpus fixes change the test inputs (`base_manager` counter path and
  `flare_miner` building group); they do not change compiler or decompiler
  semantics for arbitrary programs.
