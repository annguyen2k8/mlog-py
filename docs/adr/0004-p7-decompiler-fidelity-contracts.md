# ADR-004: P7 Decompiler Fidelity Contracts

- **Status**: Accepted
- **Date**: 2026-11-07
- **Deciders**: mlog-py Compiler Team
- **Target Engine**: Mindustry v160.7

---

## 1. Context

The P7 fidelity audit re-ran the 32-file corpus with execution traces rather
than final-state-only comparison. It found five defects that the P6 verification
could not see:

1. **Dropped else edge (P7-CRIT-01).** When a conditional inside a then-body
   exited to the enclosing `if`'s else entry, the structurer emitted a one-sided
   nested `if` with `else_body=[]`. The edge to the else block was lost. Valid
   operand changes in `arithmetic_dataflow`, `short_circuit_ladder`, and
   `reactor_safety` produced different results; the committed corpus inputs
   happened to avoid the affected branch.
2. **Bare `@` registers quoted as strings (P7-CRIT-02).** `format_operand()` and
   `ConstantExpr.to_python()` emitted `'@counter'`, `'@time'`, and `'@unit'` as
   Python strings. Recompilation produced `set x "@counter"` instead of
   `set x @counter`, so the engine read a string object instead of the live
   register. `computed_jump_counter` took a different instruction path.
3. **Loop-exit gap executed (P7-HIGH-01).** The structurer resumed at
   `max_body_address + 1`, not the loop's recorded `exit_address`. When a loop
   exit skipped instructions, the recompiled form executed the skipped gap and
   produced observable side effects (`ubind`, `u_flag`, `bar_w`).
4. **Missing preamble mapping (P7-MED-01).** Address 0, the function-table
   preamble jump, had no source mapping in seven function-bearing files.
5. **Inflated coverage (P7-MED-02).** `FunctionDef` mappings duplicated every
   body address, so raw mapped-address counts overstated statement-level
   precision.

---

## 2. Decision

### 2.1 Preserve the enclosing else edge

A conditional inside a then-body whose false edge targets the enclosing else
entry must never become a one-sided nested `if`.

- If the then-region is exactly a chain of conditionals whose false edges all
  target that else entry, flatten the chain into one combined condition:
  `if outer and inner: ... else: ...`. The merge is valid because no statement
  executes between the conditions.
- If any statement interleaves with the chain, flattening would change execution
  order. Preserve the original conditional jump as an `UnstructuredNode` and
  keep the remaining statements in address order. The false edge still reaches
  the enclosing else entry.

The choice depends only on address structure, never on guessed purity.

### 2.2 Treat bare `@` tokens as registers

`format_operand()` and expression synthesis emit `raw("@...")` for bare `@`
tokens in generic value positions (`set` values, `op` source operands, jump
conditions). This is the compiler's documented escape hatch and recompiles to a
bare token.

A quoted input token (`"@unit"`) is a real string and stays a Python string
literal. The parser preserves the quotes, so the two cases remain
distinguishable. Intrinsic argument positions such as `sensor("reactor1",
"@heat")` keep their existing quoted form because the compiler restores registry
tokens to bare operands.

### 2.3 Make the recorded loop exit authoritative

When `loop.exit_address > loop.max_body_address + 1`, a structured `while`
fallthrough cannot represent the original control flow. Emit the entire region
from the current address up to `exit_address` as an `UnstructuredNode`, then
resume structuring exactly at `exit_address`.

The raw region keeps every instruction, jump target, and latch visible and
preserves the original execution order. The fix is driven by CFG and recorded
addresses; no file, address, or instruction pattern is hardcoded.

### 2.4 Separate coarse and statement-level provenance

- Mark `FunctionDef` mappings as coarse (`is_coarse=True`). They remain useful
  for navigation but do not count as statement-level provenance.
- Record address 0 (the function-table preamble) as a coarse `Preamble` mapping
  on the first function line. No executable Python statement is invented.
- Report coverage at two levels: address coverage (`include_coarse=True`) must
  cover every instruction; statement coverage (`include_coarse=False`) measures
  precise mappings and may legitimately miss address 0.
- `mlog_to_python()` prefers the smallest non-coarse mapping so a body address
  resolves to its precise statement, not the enclosing function.

---

## 3. Consequences

- Decompiled code no longer silently changes branch outcomes under different
  operands. When the structure cannot be proven equivalent, output is raw rather
  than guessed.
- `raw("@...")` appears in generated Python for bare registers. Consumers that
  asserted the old quoted-string output must update; this is a deliberate
  correctness change, not a formatting preference.
- Some loops decompile to a larger raw region instead of a `while`. This is
  expected for exits that skip instructions and preserves byte-for-byte
  round-trip fidelity.
- Source-map consumers can distinguish address coverage from statement
  coverage. `FunctionDef` and preamble mappings carry `is_coarse`.
- The source map always covers every instruction, including address 0.

---

## 4. Verification Evidence

- `tests/test_p7_remediation.py`: 20 pure tests for the three dropped-else
  variants, the materialization path, bare `@` in `set`/`op`/jump/expression
  contexts, quoted-string distinction, both loop gaps, corpus validity, and
  coverage semantics.
- `tests/test_p7_remediation_jvm.py`: 11 JVM tests comparing run length, ticks,
  variables, messages, text buffer, displays, and bound unit on Mindustry
  v160.7, including the two corrected corpus programs.
- Exact external trace audit: all dropped-else variants, `base_manager_120`
  operand variant, `computed_jump_counter`, and register cases now execute the
  same PC sequence as the originals.
- Corpus metrics after remediation: 32/32 decompile, 30/32 recompile (2
  intentional recursion rejections), 22/30 byte-identical, 32/32 full address
  coverage (2095/2095 instructions), 2088/2095 statement-level coverage
  (99.67%), 22/30 trace-equal, 30/30 final-state-equal. `flare_miner` is now
  engine-valid; its remaining trace difference is the benign leading guard.
- Full suite: `python run_tests.py --all` passed 1500/1500 with 3 skips.
