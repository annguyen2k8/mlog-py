# P7 Fidelity Audit: Execution Traces, Source Maps, and Round-Trip Semantics

- **Date:** 2026-11-05
- **Baseline:** `54179b5a7a34260d299465b0dbc56a14083f731e` (`docs(p6): record remediation report and control-flow contracts`), equal to `origin/main`
- **Prior report:** `p6_remediation_report.md`
- **Audit scope:** decompiler output, recompiled mlog, source maps, function
  reconstruction, and JVM execution traces for all 32 corpus files
- **Mode:** read-only. No source, test, documentation, corpus, or `scratch/`
  file was modified. The only repository artifact added is this report.

## 0. Method and environment

The audit used the public API:

```python
from mlog.decompiler import decompile_with_source_map
from mlog import compile_py

py, source_map = decompile_with_source_map(original_mlog, filename=path)
recompiled = compile_py(py, allow_functions=True, validate=True).mlog
```

Execution used a copy of `MindustryHarness` kept outside the repository at
`C:\Users\Admin\AppData\Local\Temp\opencode\p7-trace`. The harness prints
`TRACE:<step>:<pc>` and `TRACE_UNIT:<step>:<pc>:<unit>` immediately before
`exec.runOnce()`, so the trace is the exact dynamic instruction sequence, not a
reconstruction from final state. It runs the real Mindustry v160.7
(`D:\Anzuno\Mindustry-source`) on a synthetic 100x100 world containing one
processor, a message block, a memory cell, a logic display, and a few buildings.
One step is one `runOnce()`; the step cap was 300 for corpus runs.

Throughout this report:

- **trace equality** means equal `(step, pc)` sequence and equal normalized
  opcode/operands, not just equal final variables.
- **final-state equality** means equal variables, messages, text buffer,
  graphics/display command counts, and bound unit after the step cap.
- Findings below are `[verified]` on the JVM unless explicitly marked
  `[static]`. A `[static]` finding is proven from the decompiler output and
  recompiled instruction stream but was not separately run.

## 1. Executive summary

| ID | Severity | Area | Files / cases | Effect |
| --- | --- | --- | --- | --- |
| P7-CRIT-01 | Critical | Structurer drops the else edge of a nested conditional whose target is the enclosing else entry | `arithmetic_dataflow`, `short_circuit_ladder`, `reactor_safety` | Wrong final state under valid inputs; corpus inputs mask it |
| P7-CRIT-02 | Critical | Bare `@` registers are emitted as Python strings | `computed_jump_counter`; any `set`/`op`/jump-condition using `@counter`, `@unit`, `@time`, ... | Wrong values and wrong control flow; corpus mostly avoids it |
| P7-HIGH-01 | High | Loop exit resumes at `max_body_address + 1` instead of the recorded `exit_address`, so the gap is executed | `base_manager_120` (P6-HIGH-02) | Recompiled program executes originally dead code and binds a unit |
| P7-MED-01 | Medium | Address 0 (function-table preamble jump) has no source mapping | 7 function-bearing files | One unmapped instruction per file; currently reported as a "function-body gap" |
| P7-MED-02 | Medium | `FunctionDef` mappings duplicate every body address and inflate coverage counts | Same 7 files | `mapped`/coverage ratios overstate precision |
| P7-LOW-01 | Low | Benign reordering/layout/timing differences | 8 files | Same final state, different trace; timing can be observable via `@tick` |
| P7-LOW-02 | Low | Corpus defects | `base_manager_120`, `flare_miner` | One input never exits; one input is engine-invalid |

Aggregate separated metrics:

| Metric | Result |
| --- | --- |
| Decompile to AST | 32/32 |
| Recompile | 30/32 (2 recursion rejections by design) |
| Byte-identical | 17/30 compilable (17/32 overall) |
| Source map covers every instruction | 25/32 (7 files miss only address 0) |
| Execution trace equal | 19/29 runnable, valid programs |
| Final state equal | 29/29 runnable, valid programs (fixed inputs only) |
| Semantic counterexamples under valid operand variants | 4 files: `arithmetic_dataflow`, `short_circuit_ladder`, `reactor_safety`, `base_manager_120` |

The central result: **final-state equality on the fixed corpus is not evidence
of fidelity**. Three corpus files produce different final state under ordinary
operand changes, and one more executes a different instruction set (including
`ubind`) under a valid control variant. `short_circuit_ladder` and
`reactor_safety` are even trace-equal on the committed corpus inputs and still
contain the dropped-else defect.

## 2. P7-CRIT-01: dropped else edge

### 2.1 Reproduction

The decompiled structure is input-independent, so the defect is visible in the
Python even when the committed corpus inputs do not take the affected branch.
The table below uses variants that only change `set` operands; no instruction,
address, or control-flow edge is added or removed.

| File | Conditional jump | Original target | Recompiled target | Variant operands | Original result | Recompiled result |
| --- | --- | --- | --- | --- | --- | --- |
| `compiler_generated/arithmetic_dataflow.mlog` | addr 16 `jump 19 greaterThanEq x 500` | 19 (`res = 0`) | 18 (`jump 20 always`) | `set a 30` (x=682, y=2182) | `res = 0.0` | `res = null` |
| `control_flow/short_circuit_ladder.mlog` | addr 8 `jump 11 notEqual d 4` | 11 (`flag = 0 - 1`) | 10 (`jump 12 always`) | `set a 5`, `set d 5` | `flag = -1.0` | `flag = 0.0` |
| `handwritten/reactor_safety.mlog` | addr 3 `jump 5 greaterThan heat 0.2` | 5 (alert block) | 4 (`jump 9 always` → nominal) | `set heat 0.5`, `set cryo 20` | `message1 = "ALERT: Reactor Overheating"` | `message1 = "Reactor Status: Nominal"` |

Exact JVM traces:

```text
arithmetic_dataflow (a=30)
  original : 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 19      res=0.0
  recompiled: 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 18      res=null

short_circuit_ladder (a=5, d=5)
  original : 0 1 2 3 4 5 7 8 11                               flag=-1.0
  recompiled: 0 1 2 3 4 5 7 8 10                               flag=0.0

reactor_safety (heat=0.5, cryo=20)
  original : 0 1 2 3 5 6 7 8          8 steps, 1 tick         message1="ALERT: Reactor Overheating"
  recompiled: 0 1 2 3 4 9 10 11 12    9 steps, 2 ticks        message1="Reactor Status: Nominal"
```

### 2.2 Decompiled structure

`arithmetic_dataflow` (variant):

```python
y = x + d
if y > 100:
    if x < 500:
        res = 1
else:
    res = 0
```

The original semantics are `if y > 100 and x < 500: res = 1 else: res = 0`.
When `y > 100` and `x >= 500`, address 16 jumps to address 19 (`res = 0`).
The decompiled nested `if` has no else edge, and the recompiled false edge
falls through to address 18 (`jump 20 always`), skipping `res = 0` at 19.

`short_circuit_ladder` (variant):

```python
if c < d:
    if d == 4:
        flag = 1
else:
    flag = op("sub", 0, 1)
```

Address 8 jumps to 11 when `d != 4`; with `c < d` true and `d != 4`, the
original takes the inner false edge to 11. The recompiled inner false edge
falls through to 10 (`jump 12 always`), skipping `flag = 0 - 1`.

`reactor_safety` (variant):

```python
if cryo >= 10:
    if heat <= 0.2:
        pass
else:
    control.enabled("reactor1", 0)
    print("ALERT: Reactor Overheating")
    printflush("message1")
    end()
```

Address 3 jumps to 5 when `heat > 0.2`. The recompiled inner false edge falls
through to 4 (`jump 9 always`), so a hot reactor reports nominal status.

### 2.3 Root cause

`src/decompiler/structurer.py` lines 718-751:

```python
if jump_target > stop_address:
    if jump_target <= stop_address + 1:
        # Exiting to enclosing branch boundary/else entry
        ...
        nodes.append(
            IfNode(
                condition_str=cond_str,
                then_body=sub_then,
                else_body=[],          # line 745
                ...
            )
        )
        curr_addr = stop_address      # line 750
        continue
```

When a conditional jump inside a then-body targets `stop_address + 1`, the
guard treats the target as the enclosing branch boundary. It emits a one-sided
`IfNode` whose then-body is the remainder of the current scope and leaves the
else empty, then sets `curr_addr = stop_address`. The caller has already
structured the target address as the enclosing `if`'s else body. The nested
`if` therefore loses the edge to that else body. The compiler faithfully
recompiles the wrong structure; this is a decompiler structuring failure, not
a compiler failure.

This is exactly the situation where ADR 0003 and the zero-guessing contract
require either a proven merge representation or an `UnstructuredNode`. A
one-sided nested `if` is neither.

### 2.4 Why P6 missed it

P6 compared final JVM state on the committed inputs only:

- `arithmetic_dataflow` uses `a=10, b=20, c=30`, so `x = 242`; `x < 500` is
  true and the dropped edge is never taken. The trace still differs at address
  16 (target 19 vs 18) but final state matches.
- `short_circuit_ladder` uses `d = 4`, so address 8 falls through and the
  dropped edge is not taken. The default trace is equal.
- `reactor_safety` leaves `reactor1` unset, so `cryo` is null and address 2
  jumps directly to the alert block at 5. Address 3 is never executed and the
  dropped inner edge is not taken; both forms emit the ALERT message.

### 2.5 Remediation

1. Preferred minimal fix: in the `jump_target <= stop_address + 1` path, if the
   target is the enclosing else entry and the current scope is a nested
   then-body, emit an `UnstructuredNode` for the conditional jump instead of a
   one-sided `IfNode`. This preserves the exact jump and satisfies the
   zero-guessing contract.
2. Alternative: propagate the enclosing else body into the nested `IfNode`'s
   `else_body`. This is semantically correct but duplicates AST and can
   duplicate side-effecting statements; only do it when the else body is pure
   or explicitly duplicated by the compiler.
3. Add regression tests for all three files plus the operand-only variants
   above. Assert both trace equality and final-state equality, not just the
   latter.

## 3. P7-CRIT-02: bare special registers are quoted

### 3.1 Reproduction

`format_operand` treats every token starting with `@` as a Python string
constant (`repr(op)`), and `ConstantExpr.to_python` does the same for expression
synthesis. `raw()` already exists as the compiler's supported escape hatch for
a bare mlog token, so the fix path is known.

| Case | Original mlog | Decompiled Python | Recompiled mlog | Original result | Recompiled result |
| --- | --- | --- | --- | --- | --- |
| `set` register | `set x @counter` | `x = '@counter'` | `set x "@counter"` | `x = 1.0`, message `"1"` | `x = "@counter"`, message `"@counter"` |
| `set` register | `set x @time` | `x = '@time'` | `set x "@time"` | `x = 0.0`, message `"0"` | `x = "@time"`, message `"@time"` |
| `op` operand | `op add x @time 1` | `x = '@time' + 1` | `op add x "@time" 1` | `x = 1.0` | `x = 2.0` |
| `op` operand | `jump 2`; `op add x @counter 1` | `x = op("add", '@counter', 1)` | `op add x "@counter" 1` | `x = 4.0` | `x = 2.0` |
| unit register | `ubind @flare`; `set u @unit` | `u = '@unit'` | `set u "@unit"` | `u = "flare"` | `u = "@unit"` |
| jump condition | `jump 2 equal @unit null` | `if '@unit' != None: x = 1` | `jump 2 equal "@unit" null` | trace `0 2 3 4`, x=2.0 | trace `0 1 2 3 4`, x=2.0 |

The `computed_jump_counter` corpus file also exposes the bug:

```text
original : 0 1 4 5 6 7 8      r=2.0
recompiled: 0 1 3 6 7 8      r=2.0
```

The recompiled instruction is:

```mlog
op add @counter "@counter" offset
```

The destination `@counter` is normalized back to a register by the compiler, but
the source operand `"@counter"` is a string object whose numeric value is `1`.
The original reads the live counter value (`2` after fetch), so it computes
`2 + 2 = 4` and jumps to address 4; the recompiled form computes `1 + 2 = 3` and
jumps to address 3. Final `r` happens to match because both branches end at
`set r 2`, but the executed path and any side effects on the skipped branch
would differ.

### 3.2 Root cause

- `src/decompiler/structured_ir.py:83-95` (`format_operand`), specifically lines
  91-92: `if op.startswith("@"): return repr(op)`.
- `src/decompiler/structured_ir.py:100-101`: `condition_to_python` uses
  `format_operand` for both comparison operands.
- `src/decompiler/expression.py:412-414`: bare `@...` tokens become
  `ConstantExpr(value="@...")`, and `ConstantExpr.to_python` (lines 139-142)
  emits `repr(...)`.
- `src/decompiler/structured_ir.py:401` (`dest_str = repr(dest)`) is an
  inconsistency, but it did not produce a confirmed failure: the compiler maps
  a quoted `"@counter"` destination back to `@counter`. Keep it in scope when
  cleaning up the formatter, but do not report it as a separate defect.

This is not a conflict with `format_semantic_argument`: intrinsic arguments such
as `ubind("@flare")` and `sensor('@unit', '@flag')` compile back to bare tokens
because the compiler unquotes registry tokens in argument positions. The defect
is specifically the generic value/expression path, where a `@` token is a
register or built-in variable, not a string.

### 3.3 Remediation

1. Change `format_operand` to emit `raw("...")` for bare `@` tokens, or emit the
   bare token directly when the compiler accepts it. `raw()` is already the
   documented, validated escape hatch and produces `set x @counter`,
   `op add x @counter 1`, and `set x @unit` correctly (verified).
2. Change `ConstantExpr` handling in `expression.py` so a bare `@` token becomes
   a raw/register expression, not a quoted string. Quoted string literals
   (`"@foo"`) must stay strings; the parser preserves the quotes, so the two
   cases are distinguishable.
3. Add tests for `set`, `op` (source and destination), jump conditions, and
   `computed_jump_counter`, including JVM trace assertions.

## 4. P7-HIGH-01: loop-exit gap (P6-HIGH-02)

### 4.1 The committed corpus input never reaches the gap

P6-HIGH-02 described `base_manager_120.mlog` addresses 20-21 (`ubind @flare`,
`sensor u_flag @unit @flag`) as dead code skipped by the turret loop exit. That
is correct statically, but the committed input does not exercise the exit path
in this harness:

```text
trace: 7 8 9 10 11 12 13 14 15 19 8 9 10 11 12 13 14 15 19 8 ...
```

Address 15 is `jump 19 always 0 0`, so the path at 14/15 skips addresses 16, 17,
and 18 — including `op add turret_idx turret_idx 1`. Whenever `t_hp_ratio >=
0.4`, `turret_idx` stays `0.0` and the loop runs until the 300-step cap. The
exit path requires `t_hp_ratio < 0.4`, which the synthetic world does not
produce. P6's statement that the original exit "jumps to address 22" was
therefore not demonstrated at runtime on the committed file; it is a static
property of the instruction stream.

A minimal operand-only variant makes the loop exit:

```mlog
op div t_hp_ratio 1 10      # replaces: op div t_hp_ratio t_hp t_max_hp
```

With `t_hp_ratio = 0.1`, address 13 jumps to 18, the counter increments, and
the loop terminates at `turret_idx = 4`.

### 4.2 Observed divergence

```text
original : ... 13 18 19 8 22 23 24 25 ...       178 steps, 23 ticks
recompiled: ... 13 18 19 8 20 21 22 23 24 25 ... 183 steps, 23 ticks

original : bound_unit=null,  u_flag=null,  bar_w=null
recompiled: bound_unit=flare, u_flag=0.0,   bar_w=0.0
```

The recompiled loop exit targets address 20 instead of 22, so it executes
`ubind @flare` and `sensor u_flag @unit @flag` — instructions the original never
executes on this path. Binding a unit is an observable side effect, and
`u_flag` changes from unset to `0.0`.

### 4.3 There are two gaps, not one

The same file has a second loop with the same defect. The memory loop guard at
address 27 is `jump 36 greaterThanEq cell_idx 8`; addresses 33-35 are
`draw clear`, `draw color`, and `op mul bar_w power_ratio 80`. The original
skips 33-35 and lands on 36, leaving `bar_w` unset. The recompiled guard lands
on 33, executes the three instructions, and produces `bar_w = 0.0`.

```text
after last memory-loop iteration:
  original : 32 27 36 37 38 39 ...
  recompiled: 32 27 33 34 35 36 37 38 39 ...
```

So the P6-H02 description (addresses 20-21) was incomplete: the file contains
gaps `[20, 22)` and `[33, 36)`.

### 4.4 Root cause

`src/decompiler/structurer.py:540`:

```python
curr_addr = max(loop.max_body_address + 1, curr_addr + 1)
```

The loop's `exit_address` was computed correctly at lines 178-202 (target 22 for
the turret loop, target 36 for the memory loop), but sequential structuring
resumes at `max_body_address + 1` (20 and 33). The instructions in
`(max_body_address, exit_address)` are therefore emitted as reachable
fall-through code. A structured `while` exit always falls through to the next
emitted statement, so the recompiled guard is retargeted to the gap start.

The zero-guessing contract applies: the decompiler cannot prove that the gap is
unreachable from every path, and it cannot represent "loop exits past a
non-contiguous block" as a plain `while`. It should either preserve the gap as
unstructured/dead code with an explicit exit jump, or reject the loop to
`UnstructuredNode`.

### 4.5 Remediation

1. When `loop.exit_address > loop.max_body_address + 1`, do not resume at
   `max_body_address + 1`. Emit the gap as an unreachable/`UnstructuredNode`
   region and ensure the loop's false edge still targets `exit_address`; or
   fall back to `UnstructuredNode` for the whole loop.
2. Fix the corpus input separately: address 15 should jump to 18, not 19, if the
   intent is to increment the counter after shooting. As written, the
   `t_hp_ratio >= 0.4` path cannot exercise the post-loop region.
3. Add a regression that uses the corrected input (or the operand-only variant)
   and asserts `bound_unit`, `u_flag`, and `bar_w`, not just variables and
   messages. The current P6 metric does not compare `bound_unit`.

## 5. Source-map fidelity

### 5.1 Per-file coverage

All 32 files were checked address by address. There are no out-of-range
mappings, no invalid Python line numbers, and no duplicated statement-level
mappings. Twenty-five files map every instruction. The seven function-bearing
files each miss exactly one address: address 0.

| File | Instructions | Mapped | Missing |
| --- | ---: | ---: | --- |
| `compiler_generated/large_compiler_program.mlog` | 41 | 40 | `[0]` |
| `compiler_generated/multi_func_math.mlog` | 23 | 22 | `[0]` |
| `compiler_generated/recursive_factorial.mlog` | 16 | 15 | `[0]` |
| `functions/func_with_loop.mlog` | 13 | 12 | `[0]` |
| `functions/nested_calls.mlog` | 17 | 16 | `[0]` |
| `functions/recursion.mlog` | 21 | 20 | `[0]` |
| `functions/two_functions.mlog` | 17 | 16 | `[0]` |

Address 0 in every case is the function-table preamble:

```mlog
0  jump <global_start> always 0 0
```

It is structural, not a Python statement. `SourceMap.mlog_to_python(0)` returns
`None`. For `large_compiler_program`, addresses 1-3 map to the `return a + b`
line, addresses 4-11 map to the `multiply` body, and address 28 maps to the
first global statement `i = 0`.

This corrects P6 section 8.3. The gap is **not** a function-body source-map
gap. Every function-body address has a statement-level mapping; only the global
preamble at address 0 is unmapped.

### 5.2 Per-function coverage

`FunctionDef` mappings duplicate the entire function range. Excluding them,
every body address is still covered by at least one statement mapping:

| File | Function | mlog range | Body addresses | Statement mappings | Covered | Uncovered |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `large_compiler_program` | `add` | 1-3 | 3 | 1 | 3 | none |
| `large_compiler_program` | `multiply` | 4-11 | 8 | 6 | 8 | none |
| `large_compiler_program` | `compute_stat` | 12-27 | 16 | 5 | 16 | none |
| `multi_func_math` | `square` | 1-3 | 3 | 1 | 3 | none |
| `multi_func_math` | `clamp` | 4-12 | 9 | 5 | 9 | none |
| `recursive_factorial` | `fact` | 1-11 | 11 | 5 | 11 | none |
| `func_with_loop` | `sum_to_n` | 1-8 | 8 | 6 | 8 | none |
| `nested_calls` | `double_val` | 1-3 | 3 | 1 | 3 | none |
| `nested_calls` | `quad_val` | 4-12 | 9 | 3 | 9 | none |
| `recursion` | `fib` | 1-16 | 16 | 7 | 16 | none |
| `two_functions` | `add` | 1-3 | 3 | 1 | 3 | none |
| `two_functions` | `sub` | 4-6 | 3 | 1 | 3 | none |

### 5.3 `FunctionDef` coarse mappings inflate coverage

`FunctionDef` mappings span the full function range and duplicate every body
address. Duplicate counts: `large_compiler_program` 27, `multi_func_math` 12,
`recursive_factorial` 11, `func_with_loop` 8, `nested_calls` 12,
`recursion` 16, `two_functions` 6. `SourceMap.mlog_to_python` correctly prefers
non-`FunctionDef` mappings, so resolution is still precise, but any metric that
counts raw mapped addresses or treats every mapped line as statement-level will
overstate precision. The P6 ratios (0.9756, 0.9565, etc.) are exactly
`(instructions - 1) / instructions`, not evidence of partial function-body
coverage.

### 5.4 Remediation

1. Emit a mapping for address 0 to the first global statement line (or to a
   synthetic comment line such as `# function table`). This closes the only
   missing address.
2. Mark `FunctionDef` mappings as coarse and exclude them from
   "mapped instruction" counts; report statement-level and coarse-level
   coverage separately.
3. Add a source-map test that iterates every address and asserts a non-`None`
   mapping, including address 0.

## 6. Function reconstruction

Function reconstruction is strong for the non-recursive subset:

| File | Functions | Instructions | Byte-equal | Trace-equal | Final-state |
| --- | --- | ---: | --- | --- | --- |
| `functions/func_with_loop.mlog` | `sum_to_n` | 13 | yes | yes | yes |
| `functions/nested_calls.mlog` | `double_val`, `quad_val` | 17 | yes | yes | yes |
| `functions/two_functions.mlog` | `add`, `sub` | 17 | yes | yes | yes |
| `compiler_generated/large_compiler_program.mlog` | `add`, `multiply`, `compute_stat` | 41 | no | no | yes |
| `compiler_generated/multi_func_math.mlog` | `square`, `clamp` | 23 | no | no | yes |

- Call nodes map the full calling-convention range: in
  `large_compiler_program`, `s1 = add(x, y)` maps addresses 12-16 and
  `s2 = multiply(z, s1)` maps 17-21.
- Multiple returns are mapped: `compute_stat` has `Return` nodes for
  addresses 23-25 and 26-27; `clamp` and `fib` likewise.
- Nested calls compile and execute identically (`nested_calls`, byte-equal and
  trace-equal).
- Recursion is rejected by design with an explicit diagnostic:
  `recursive user function call is not supported: fact -> fact (mlog has no call
  stack; recursion would overwrite the return address)`. This is a documented
  contract, not a regression.

The two non-byte-equal function files differ only in benign expression/layout
ways (see section 8); their function bodies, call edges, and returns are
correctly reconstructed.

## 7. Separated round-trip metrics

| File | Instr | Mapped | Missing | Recompile | Byte-equal | Trace-equal | Final-state |
| --- | ---: | ---: | --- | --- | --- | --- | --- |
| `compiler_generated/arithmetic_dataflow.mlog` | 20 | 20 | - | yes | no | no | yes |
| `compiler_generated/large_compiler_program.mlog` | 41 | 40 | `[0]` | yes | no | no | yes |
| `compiler_generated/multi_func_math.mlog` | 23 | 22 | `[0]` | yes | no | no | yes |
| `compiler_generated/nested_while_if.mlog` | 19 | 19 | - | yes | yes | yes | yes |
| `compiler_generated/recursive_factorial.mlog` | 16 | 15 | `[0]` | no | n/a | n/a | n/a |
| `compiler_generated/sensor_monitoring.mlog` | 16 | 16 | - | yes | yes | yes | yes |
| `control_flow/chained_elif.mlog` | 15 | 15 | - | yes | yes | yes | yes |
| `control_flow/empty_branches.mlog` | 7 | 7 | - | yes | no | no | yes |
| `control_flow/loop_in_if_in_loop.mlog` | 15 | 15 | - | yes | yes | yes | yes |
| `control_flow/nested_while_breaks.mlog` | 17 | 17 | - | yes | yes | yes | yes |
| `control_flow/short_circuit_ladder.mlog` | 12 | 12 | - | yes | no | yes* | yes |
| `functions/func_with_loop.mlog` | 13 | 12 | `[0]` | yes | yes | yes | yes |
| `functions/nested_calls.mlog` | 17 | 16 | `[0]` | yes | yes | yes | yes |
| `functions/recursion.mlog` | 21 | 20 | `[0]` | no | n/a | n/a | n/a |
| `functions/two_functions.mlog` | 17 | 16 | `[0]` | yes | yes | yes | yes |
| `handwritten/base_manager_120.mlog` | 120 | 120 | - | yes | no | no | yes |
| `handwritten/display_bar_graph.mlog` | 12 | 12 | - | yes | yes | yes | yes |
| `handwritten/flare_miner.mlog` | 15 | 15 | - | yes | no | no | yes** |
| `handwritten/reactor_safety.mlog` | 13 | 13 | - | yes | no | yes* | yes |
| `handwritten/turret_radar.mlog` | 14 | 14 | - | yes | no | no | yes |
| `mindustry_api/drawing_pipeline.mlog` | 6 | 6 | - | yes | yes | yes | yes |
| `mindustry_api/memory_ops.mlog` | 7 | 7 | - | yes | yes | yes | yes |
| `mindustry_api/message_formatting.mlog` | 8 | 8 | - | yes | yes | yes | yes |
| `mindustry_api/sensor_control_full.mlog` | 12 | 12 | - | yes | yes | yes | yes |
| `mindustry_api/unit_controls.mlog` | 7 | 7 | - | yes | yes | yes | yes |
| `pathological/computed_jump_counter.mlog` | 9 | 9 | - | yes | no | no | yes |
| `pathological/irreducible_cfgs.mlog` | 7 | 7 | - | yes | yes | yes | yes |
| `pathological/scale_1000_instr.mlog` | 980 | 980 | - | yes | no | no | yes |
| `pathological/scale_100_instr.mlog` | 100 | 100 | - | yes | no | no | yes |
| `pathological/scale_500_instr.mlog` | 500 | 500 | - | yes | no | no | yes |
| `pathological/spaghetti_goto.mlog` | 9 | 9 | - | yes | yes | yes | yes |
| `pathological/unreachable_dead_code.mlog` | 7 | 7 | - | yes | yes | yes | yes |

`*` Trace-equal only on the committed inputs; the dropped-else variant diverges
(section 2).

`**` Both forms are rejected by the engine, so final-state equality is vacuous.

## 8. Benign trace differences

The first five differences were proven semantically equivalent on the tested
inputs; `flare_miner` is unverifiable. They still matter for byte-for-byte and
timing fidelity.

| File | Difference | Evidence |
| --- | --- | --- |
| `compiler_generated/large_compiler_program.mlog` | `set a s1` and `set b z` swapped at 17/18 | Independent assignments; all variables equal after 300 steps |
| `compiler_generated/multi_func_math.mlog` | Clamp condition inverted at address 4 (`greaterThanEq val low` → `lessThan val low`), branch layout swapped | All three clamp paths return the same value; JVM final state equal |
| `control_flow/empty_branches.mlog` | Final `jump 7 always` replaced by `end` | Address 7 is the program end; equivalent |
| `handwritten/turret_radar.mlog` | Extra leading `jump 15 equal true 0` guard; 14 → 15 instructions | Always-false guard; final state equal, but ticks 200 → 190 at the 300-step cap |
| `pathological/scale_100/500/1000_instr.mlog` | Extra `while True` guard; +1 instruction | Always-false guard; final state equal, timing can differ |
| `handwritten/flare_miner.mlog` | 15 → 16 instructions | Both forms rejected by the engine; runtime unverifiable |

The `scale_*` and `turret_radar` timing changes are benign for final state but
are observable to programs that read `@tick` or depend on instruction budget.
They should not be described as "byte-for-byte equivalent".

## 9. Corrections to the P6 report

1. **Section 8.1, "no runtime mismatches":** not established. Three files have
   final-state mismatches under valid operand variants (`arithmetic_dataflow`,
   `short_circuit_ladder`, `reactor_safety`), `base_manager_120` has an
   observable `ubind`/`u_flag`/`bar_w` mismatch under a valid control variant,
   and `computed_jump_counter` executes a different path. The committed corpus
   inputs and the final-state-only comparison hide these.
2. **Section 8.1 classification:** `computed_jump_counter` is not an
   "expression reconstruction or temporary-allocation" difference; it is the
   special-register bug. `base_manager_120` is P6-H02, not a benign expression
   difference.
3. **Section 8.2, P6-H02:** the static description is correct but was not
   observed at runtime on the committed file, because address 15 skips the
   counter increment on the `t_hp_ratio >= 0.4` path and that path does not
   exit. The file also has a second gap at `[33, 36)`, omitted by P6. The gap is
   not "out of scope" in the sense of being unproven: it is reproducible with an
   operand-only variant.
4. **Section 8.3:** the seven files do not have function-body gaps. They each
   miss only address 0 (the function-table preamble). Every body address has a
   statement-level mapping; `FunctionDef` mappings duplicate the whole range and
   inflate raw coverage counts.
5. **Section 8.4:** correct. Recursion remains intentionally unsupported.

## 10. Remediation priorities

| Priority | Action | Location | Acceptance test |
| --- | --- | --- | --- |
| P0 | Stop emitting a one-sided nested `if` when the target is the enclosing else entry; use `UnstructuredNode` or propagate the else body | `src/decompiler/structurer.py:718-751` | All three Critical-01 variants produce equal traces and final state |
| P0 | Emit bare `@` registers via `raw()` in value/expression positions | `src/decompiler/structured_ir.py:83-101`, `src/decompiler/expression.py:412-414` | `set`/`op`/jump-condition register cases round-trip and match JVM values |
| P1 | Preserve loop-exit gaps: resume at `exit_address`, emit the gap as unreachable/`UnstructuredNode`, or fall back to `UnstructuredNode` | `src/decompiler/structurer.py:540` | P6-H02 variant matches trace, `bound_unit`, `u_flag`, and `bar_w` |
| P2 | Map address 0; mark `FunctionDef` ranges as coarse and separate them in coverage metrics | `src/decompiler/sourcemap.py`, `src/decompiler/function_ir.py` | Every address maps; coverage report distinguishes statement vs coarse |
| P3 | Fix corpus defects and add variants: `base_manager_120` address 15 should jump to 18; `flare_miner` `ulocate building container` is invalid in v160.7 | `tests/corpus/handwritten/base_manager_120.mlog`, `tests/corpus/handwritten/flare_miner.mlog` | Corpus exercises the post-loop region; invalid input is either fixed or explicitly skipped |
| P4 | Update P6 report/ADR wording after fixes | `p6_remediation_report.md`, `docs/adr/0003-...` | No stale claims about "no runtime mismatches" or "function-body gaps" |

## 11. Unverifiable limits

- **Synthetic world.** The JVM harness uses a 100x100 synthetic world with one
  processor and a few buildings, not a real save. Sensor values for missing
  buildings are null; unit binding is exercised with a spawned flare. Instruction
  semantics are real Mindustry v160.7, but gameplay-level behavior (enemy AI,
  waves, real buildings, multiplayer state) was not tested.
- **Step cap.** Corpus runs stop at 300 steps or 300 ticks. Equality means
  "equal within the cap", not "both programs terminate with equal state". The
  `base_manager_120` corpus input does not exit on the `t_hp_ratio >= 0.4`
  path exercised here.
- **`flare_miner.mlog`.** The engine rejects both forms with
  `Line 8: Mindustry rejected statement as InvalidStatement: 'ulocate building
  container 0 @copper cx cy found cblock'`. Runtime fidelity for this file is
  unverifiable until the corpus input is corrected.
- **No compiler-side source map.** The repository exposes only the decompiler's
  mlog → Python map (`SourceMap.mlog_to_python`). Python → mlog provenance was
  checked by instruction comparison and JVM traces, not by a compiler-side map.
- **Recursion.** `recursive_factorial` and `recursion` are rejected by design,
  so no runtime comparison exists. This is an intentional contract, not a
  fidelity result.
- **Variants are synthetic.** They change only operands (`set` values) or one
  arithmetic instruction, and use valid mlog. They prove the defects are
  input-dependent, not that every possible input diverges.
- **Fast test tier.** The first run failed with `[Errno 28] No space left on
  device` because the host `D:` volume was full; after removing regenerable
  Python caches (not source, tests, docs, corpus, or evidence files), the tier
  passed 850/850 with 3 skips. The disk-full failures were environmental, not
  code regressions.

## 12. Verification and repository state

Commands run:

```text
python run_tests.py --fast
  -> Ran 850 tests, OK (skipped=3)

JVM traces via MindustryTraceHarness (Mindustry v160.7 local build)
  -> 32 corpus files, 300-step cap, TRACE:<step>:<pc> before each runOnce()
  -> 7 function files, per-address and per-function coverage
  -> operand-only variants for arithmetic_dataflow, short_circuit_ladder,
     reactor_safety, base_manager_120, and special-register cases
```

Git state:

```text
before: HEAD 54179b5, ?? scratch/
after:  HEAD 54179b5, ?? scratch/
        ?? p7_fidelity_audit.md
```

No tracked file changed. `scratch/` was not modified. The only new repository
artifact is this report.
