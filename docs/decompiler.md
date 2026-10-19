# MLog → Python DSL Decompiler

This document details the multi-phase reverse engineering pipeline that reconstructs clean, typed Python DSL code from flat Mindustry Logic instructions.

---

## 1. Decompiler Pipeline Overview

```text
Vanilla MLog Source (.mlog)
       │
       ▼
 [parser.py]          Phase 1: Line-by-line parsing & MlogInstruction IR
       │
       ▼
   [cfg.py]           Phase 1: Leader splitting & CFG edge reconstruction
       │
       ▼
[structurer.py]       Phase 2: Dominance analysis & structured control flow recovery
       │
       ▼
 [dataflow.py]        Phase 3: Scoped Use-Def analysis, temporary collapsing & expressions
       │
       ▼
 [naming.py]          Phase 3.5: Reserved-identifier normalization for round-trip
       │
       ▼
[function_analyzer.py] Phase 4: Function boundary & calling convention detection
       │
       ▼
[sourcemap.py]        Phase 4.5: Full-pipeline provenance tracking & debug mode
       │
       ▼
[semantics.py]        Phase 5: SSOT Semantic Argument Recovery
       │
       ▼
Python DSL Source (.py) / SourceMap (.json)
```

---

## 2. Phase 1: Parsing & Control Flow Graph (CFG)

- **Instruction Parsing (`src/decompiler/parser.py`)**: Tokenizes each MLog line into an `MlogInstruction(address, opcode, args, loc)`. Handles string literals with escaped characters, comments, and empty lines.
- **Basic Block Leader Splitting (`src/decompiler/cfg.py`)**:
  Identifies basic block leaders:
  1. Address `0` (entry point).
  2. Any target address of a jump instruction.
  3. Any instruction immediately following a jump or terminator (`end`, `stop`).
- **Edge Construction**: Connects blocks with directed edges:
  - `EdgeType.FALLTHROUGH`: Sequential fallthrough to block $i+1$.
  - `EdgeType.CONDITIONAL`: True-branch of a conditional jump.
  - `EdgeType.UNCONDITIONAL`: Direct branch of an unconditional jump.

---

## 3. Phase 2: Structured Control Flow

- **Dominance Analysis (`src/decompiler/structurer.py`)**: Computes immediate dominators (`idom`) and dominance frontiers for every basic block.
- **Natural Loop Detection**: Identifies back-edges $u \to v$ where $v$ dominates $u$.
  - **Top-tested While Loops (`while cond:`)**: Pure temporary calculations feeding the condition jump are inlined directly into the comparison expression.
  - **Loop Header Side-Effects**: When a loop header contains I/O operations (`read`, `sensor`, `getlink`), the loop is safely structured as `while True:` where the pre-instructions execute first, followed by `if exit_cond: break`, ensuring exact execution order without undefined variable access.
  - **Bottom-tested Loops (`do-while`)**: When the condition check occurs at the latch back-edge, the body statements are scoped up to `latch_block.end_address`, and the latch is cleanly emitted as `if not (latch_cond): break`.
- **Branch Ladder Recovery**: Reconstructs `IfNode` trees with optional `elif` and `else` branches based on convergence merge points.
- **Break & Continue Isolation**: Distinguishes between loop-internal jumps (`continue` targeting header/latch, `break` targeting loop exit) and external jumps across nested loops.
- **Zero Guessing Fallback (`UnstructuredNode`)**:
  If a loop is irreducible (multiple entry points) or an indirect jump modifies `@counter`, the structurer does not guess speculative while loops. Instead, it emits `UnstructuredNode` with comments and raw, unquoted semantic `jump(...)` calls (`jump(1, "equal", y, 2)`) to preserve 100% execution fidelity and byte-for-byte round-trip equivalence.

---

## 4. Phase 3: Expression & Dataflow Recovery

- **Scoped Use-Def Analysis (`src/decompiler/dataflow.py`)**:
  Tracks definitions and usages of variables within structured basic block scopes.
- **Loop Invariant Safety**:
  Guarantees that variables modified inside a `WhileNode` body are never inlined into `WhileNode.condition_expr` or folded out of the loop scope.
- **Temporary Variable Collapsing**:
  Compiler-generated temporaries (`__tmp0`, `__tmp1`) are collapsed into compound expression trees if and only if:
  1. The variable is defined exactly once.
  2. The variable is used exactly once.
  3. The use occurs within the same structured scope without intervening redefinitions or side-effects.
- **Alias Simplification & Constant Folding (`--simplify-expressions`)**:
  Eliminates redundant variable-to-variable aliases (`b = g`) and folds constant operations while strictly respecting Mindustry arithmetic semantics and IEEE-754 limits.
- **Expression IR (`src/decompiler/expression.py`)**:
  Builds nested `BinaryOpNode`, `UnaryOpNode`, and `CallNode` expression trees with proper operator precedence and minimal parenthesization.
- **Safe Multi-Use Preservation**:
  Variables used multiple times or modified across basic blocks remain explicit assignments (`AssignNode`) to protect against side-effect corruption.

---

## 5. Phase 4: Function & Procedure Recovery

- **Boundary Analysis (`src/decompiler/function_analyzer.py`)**:
  Scans whole-program CFG for calling conventions:
  - Function entry points jumped to from multiple distinct call sites.
  - Return address conventions (`set @counter __ret_addr` or `jump __ret_addr`).
  - Parameter bindings preceding the call jump.
  - Return value recovery from return register assignments (`set __retval_fn ...`).
- **Whole-Program Structuring (`src/decompiler/function_ir.py`)**:
  Emits `FunctionDef` blocks with typed parameter lists and `ReturnNode` statements, isolating top-level script statements from procedure bodies.

---

## 5.5. Phase 3.5: Reserved-Identifier Normalization (`src/decompiler/naming.py`)

The compiler allocates scratch registers named `__tmp0`, `__tmp1`, ... and the parser
rejects those names in user source (`Compiler.format_name`). When Phase 3 cannot prove a
temporary is safe to fold — for example a `read` feeding a `write` inside a loop, where
re-evaluating would reorder a memory access — the temporary must stay as an explicit
assignment. Emitting the raw name would produce Python the compiler refuses to recompile.

This pass builds a single deterministic, collision-free mapping (`__tmp0` → `tmp_val_0`,
numbered in first-appearance order) and applies it to every read, write, and instruction
operand of the structured tree:

- it is a pure 1:1 rename — no assignment, use, or operand is added, removed, or reordered;
- identifiers that are not compiler temporaries are never touched;
- a temporary that exists only in an elidable `ulocate` output slot keeps its original
  name, because `instruction_to_python` drops that operand and the compiler regenerates the
  same scratch register on its own.

---

## 6. Phase 5: Semantic Argument Recovery

- Categorizes instruction arguments into 6 distinct semantic roles using the Single Source of Truth (`src/metadata.py`).
- Emits physical hardware links as string literals (`"cell1"`, `"display1"`) to prevent Python `NameError` exceptions.
- See [semantic-arguments.md](semantic-arguments.md) for full specification.
- For instruction-to-source provenance tracking (Phase 4.5), see [source-mapping.md](source-mapping.md).

---

## 7. Python API

```python
from src.decompiler import decompile, decompile_with_source_map

mlog_text = """
sensor heat reactor1 @heat
jump 4 lessThanEq heat 0.5
control enabled reactor1 0 0 0 0
"""

# Basic decompilation
python_code = decompile(mlog_text)

# Decompilation with advanced dataflow expression & alias simplification
simplified_code = decompile(mlog_text, recover_expressions=True)

# Decompilation with provenance comments (# mlog[<addr>])
debug_code = decompile(mlog_text, debug=True)

# Decompilation with SourceMap object
clean_code, sm = decompile_with_source_map(mlog_text)
```
