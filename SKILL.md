---
name: mlog-compiler-skill
description: >-
  Comprehensive guide, architecture specification, and reference manual for mlog-py,
  the verified Python-to-Mindustry Logic compiler and decompiler framework. Covers the
  AST-to-IR compiler pipeline, MLog-to-Python decompiler pipeline (Phases 1-5), CFG
  recovery, structured control flow, expression recovery, function calling conventions,
  source mapping, semantic argument recovery, Single Source of Truth metadata, and
  real-engine validation harness.
---

# mlog-py: Mindustry Logic Compiler & Decompiler Skill

Welcome to the **mlog-py Skill**. This document is the primary operational manual for AI agents working on `mlog-py`, governing both the **Python → MLog compiler** and the **MLog → Python DSL decompiler**.

---

## 1. Agent Golden Rules

Every agent working on this codebase must adhere strictly to these 7 non-negotiable rules:

1. **Read Existing Architecture First**: Always inspect the relevant passes in `docs/` and `src/` before proposing or implementing changes.
2. **Leverage SSOT Metadata**: All property validation, opcode signatures, and typing stems from `src/metadata.py` and `src/mlog_registry.py`. Never invent or hardcode custom token maps.
3. **Uphold the Zero Guessing Principle**: Never synthesize high-level constructs (loops, expressions, OOP) without mathematical proof (dominance frontiers, single-use Use-Def chains).
4. **Fallback Over Guessing**: When the decompiler cannot prove semantic equivalence, fall back immediately to `UnstructuredNode` with comments and preserved raw instructions.
5. **Never Break Compiler Semantics**: Do not modify compiler behavior or DSL semantics to accommodate decompiler edge-cases. The compiler defines the canonical Python DSL spec.
6. **Add Regression Tests for Every Bug**: Every fix must include an isolated unit test reproducing the issue before and verifying the solution after.
7. **Run Full Test Suite Before Concluding**: Execute `python3 -m unittest discover -s tests` and verify 281/281 PASS before completing any task.

---

## 2. System Architecture & Directory Structure

```text
mlog-py/
├── SKILL.md                 # Single authoritative agent skill manual
├── README.md                # User-facing overview, quick-start, and workflows
├── compiler.py              # CLI entry point for compiler
├── mlog.py / mlog.pyi       # Runtime module and IDE typing stubs
├── docs/                    # Detailed technical specifications
│   ├── architecture.md      # Unified system architecture
│   ├── compiler.md          # Python-to-MLog compiler pipeline
│   ├── decompiler.md        # MLog-to-Python decompiler pipeline
│   ├── source-mapping.md    # Provenance tracking and SourceMap JSON
│   └── semantic-arguments.md# Semantic role recovery & device quoting
├── examples/                # Real, compilable and decompilable examples
│   ├── compiler/            # Python DSL -> MLog examples
│   └── decompiler/          # MLog -> Python DSL examples
├── src/                     # Core compiler and decompiler source code
│   ├── metadata.py          # Single Source of Truth (SSOT)
│   ├── compiler.py          # AST -> IR lowering
│   ├── emitter.py           # Two-pass address resolution
│   ├── validator.py         # Static grammar & processor limits
│   └── decompiler/          # Decompiler subsystem (Phases 1–5)
└── tests/                   # Comprehensive test suite (281 tests)
    └── corpus/              # 32-case real-world corpus
```

---

## 3. Python DSL Conventions & SSOT Metadata

The Python DSL is strongly typed and checked against Mindustry's engine classes:
- **Canonical DSL Imports**:
  ```python
  from mlog import jump, set, op, sensor, control, ucontrol, draw, read, write, wait, stop, end, getlink
  from mlog import SensorProperty, ControlProperty, UnitControl, DrawType, LogicOp, Condition, Units, raw, null
  ```
- **Physical Hardware Links vs Variables**:
  - Direct hardware links are quoted strings: `val = read("cell1", 0)`, `drawflush("display1")`, `printflush("message1")`.
  - Dynamic links bound via `b = getlink(0)` are unquoted Python identifiers.
- **Special Registers**: Emitted as quoted strings with `@` prefix: `set("@counter", 10)`, `u = sensor("@unit", "@dead")`.
- **Print Buffer Semantics (`print` & `printflush`)**:
  - In Mindustry Logic (`LExecutor.PrintI`), `print` appends text directly to the processor's internal `textBuffer`. It does **not** append a newline (`\n`) or space.
  - Consecutive `print()` statements concatenate content on the same line (e.g. `print("Status: ")` then `print("ONLINE")` outputs `"Status: ONLINE"`).
  - To insert a newline, the string literal must explicitly include `\n` (e.g. `print("Line 1\n")`).
  - **Buffer Limit**: The processor buffer is capped at 400 characters (`maxTextBuffer = 400`). If `length() >= 400`, `print()` calls are ignored. Text exceeding remaining capacity is truncated (`append(strValue, 0, Math.min(len, 400 - current_len))`).
  - **Value Formatting**: Booleans in Mindustry Logic are numbers `1` and `0` (`GlobalVars.java`). Numbers within `0.00001` of an integer format as integers (`Math.round(val)`). Invalid numbers (`NaN`, `Infinity`) become `null` and format as `"null"`.
  - **Flush Semantics**: `printflush(target)` copies text to the target block (if printable) and **unconditionally** clears the processor buffer to length 0 (`textBuffer.setLength(0)`), even if target is null, invalid, or non-printable.
  - Neither compiler nor decompiler may artificially synthesize `\n` or alter `print` calls, preserving exact 1-to-1 instruction semantics.

---

## 4. Compiler Pipeline (Python → MLog)

$$\text{Python AST} \xrightarrow{\text{parser.py}} \text{Symbolic IR} \xrightarrow{\text{compiler.py}} \text{PassThrough} \xrightarrow{\text{emitter.py}} \text{Two-Pass Resolution} \xrightarrow{\text{validator.py}} \text{Vanilla MLog}$$

1. **AST Whitelist (`parser.py`)**: Rejects unsupported features (`class`, `list`, `dict`, `for ... in`) with source locations.
2. **IR Lowering (`compiler.py`)**: Generates symbolic nodes (`IRLabel`, `IRSet`, `IROp`, `IRJump`, `IRRaw`) with compiler temporaries (`__tmp0`). Implements short-circuit evaluation for `and`, `or`, `not`.
3. **Two-Pass Resolution (`emitter.py`)**:
   - Pass 1: Maps labels to instruction addresses (labels occupy 0 slots).
   - Pass 2: Replaces symbolic labels with 0-indexed numeric line targets.
4. **Limits Validation (`validator.py`)**: Enforces $\le 1000$ instructions, $\le 500$ jumps, $\le 16$ tokens.
5. **Java Engine Harness**: Verifies against Mindustry's live `LParser` and `LAssembler`.

---

## 5. Decompiler Pipeline (MLog → Python DSL)

```text
MLog Assembly (.mlog)
       │
       ▼
 [parser.py]          Phase 1: Line-by-line parsing & MlogInstruction IR (tokens, addresses)
       │
       ▼
   [cfg.py]           Phase 1: Leader splitting & CFG reconstruction (Fallthrough, Conditional, Unconditional)
       │
       ▼
[structurer.py]       Phase 2: Dominance analysis & structured control flow (while, if, elif, else, break, continue)
       │
       ▼
 [dataflow.py]        Phase 3: Scoped Use-Def analysis, temporary collapsing & expression trees
       │
       ▼
[function_analyzer.py] Phase 4: Function boundary & calling convention recovery (FunctionDef, CallNode, ReturnNode)
       │
       ▼
[sourcemap.py]        Phase 4.5: Full-pipeline provenance tracking, bidirectional line/addr lookup, debug comments
       │
       ▼
[semantics.py]        Phase 5: SSOT Semantic Argument Recovery (Named Hardware Links, @constants, Program Variables)
       │
       ▼
Python DSL Source (.py) / SourceMap (.json)
```

### 1. Control Flow & Dominance Recovery
- Identifies basic block leaders and computes immediate dominators (`idom`).
- Natural loop back-edges reconstruct `WhileNode`; branch merge points reconstruct `IfNode` / `elif` / `else`.
- **Zero Guessing Fallback**: Irreducible CFG loops and indirect jumps modifying `@counter` emit `UnstructuredNode` comments and raw jumps.

### 2. Expression & Dataflow Recovery
- Analyzes Use-Def chains within basic block scopes.
- Single-use compiler temporaries (`__tmp0`) collapse into compound expression trees (`a + b * c`).
- Multi-use variables remain explicit assignments to guarantee side-effect correctness.

### 3. Function & Calling Convention Recovery
- Recognizes procedures from multi-site call jumps and return address stores (`set @counter __ret_addr`).
- Reconstructs `def name(args):` statements and call sites, preserving global variables.

### 4. Semantic Argument Recovery
Classifies tokens into 6 distinct semantic roles using `src/metadata.py`:
1. *Program Variables*: `x`, `val`, `total` $\to$ unquoted identifiers.
2. *Named Hardware Links*: `"cell1"`, `"display1"`, `"message1"`, `"reactor1"` $\to$ quoted string literals.
3. *Special Constants*: `"@unit"`, `"@counter"`, `"@health"` $\to$ quoted string literals.
4. *DSL Enums & Keywords*: `DrawType.CLEAR`, `SensorProperty.HEALTH`.
5. *Literals*: `10`, `3.14`, `"hello"`.
6. *Dynamic Variables Holding Blocks*: `b = getlink(0); sensor(hp, b, "@health")` $\to$ `b` is unquoted identifier.

---

## 6. Round-Trip Workflows

The framework provides guaranteed round-trip verification across three flows:

1. **Python → MLog**: `compile_py(source)` produces canonical MLog bytecode.
2. **MLog → Python DSL**: `decompile(mlog)` produces valid Python DSL code that passes `ast.parse`.
3. **MLog → Python → MLog**: Decompiled Python recompiles back into byte/token equivalent MLog instructions:
   ```python
   from src.decompiler import decompile
   from src.mlog import compile_py

   py_code = decompile(mlog_text)
   recompiled = compile_py(py_code, allow_functions=True)
   assert recompiled.mlog.strip() == mlog_text.strip()
   ```

---

## 7. Testing Requirements & Corpus Structure

- **Test Suite**: 281 automated tests in `tests/test_*.py`.
- **Hardening Corpus (`tests/corpus/`)**: 32 real-world programs across 6 categories:
  - `handwritten/`: Real game controller scripts (turrets, mining drones, reactor controllers).
  - `compiler_generated/`: Direct output from `mlog-py` compiler verifying decompiler symmetry.
  - `control_flow/`: Complex while loops, short-circuit ladders, chained elifs.
  - `functions/`: Multi-function math, loops inside functions, recursion.
  - `mindustry_api/`: Memory cell operations, display graphics, radar, unit control.
  - `pathological/`: 100 to 1000 instruction stress tests, irreducible CFGs, computed jumps, dead code.
- **Verification Command**:
  ```bash
  python3 -m unittest discover -s tests -p "test_*.py"
  ```

---

## 8. Realistic Known Limitations

1. **Irreducible Control Flow**: Non-natural loops fall back to `UnstructuredNode` rather than synthetic while structures.
2. **Temporary Scope**: Temporaries read multiple times or modified across basic blocks are not inlined.
3. **Flat Memory Model**: Mindustry has no heap or object system; object-oriented constructs, classes, and Python collections (`list`, `dict`) are not reconstructed.
4. **No Speculative Abstractions**: High-level game abstractions are never invented without structural proof.

---

## 9. Documentation Index

For detailed pass specifications, refer directly to `docs/`:
- [Architecture Overview](docs/architecture.md)
- [Compiler Pipeline](docs/compiler.md)
- [Decompiler Pipeline](docs/decompiler.md)
- [Source Mapping & Debug Mode](docs/source-mapping.md)
- [Semantic Argument Recovery](docs/semantic-arguments.md)
