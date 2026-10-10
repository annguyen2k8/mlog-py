# mlog-py System Architecture

This document describes the unified architecture of `mlog-py`, encompassing both the **Python → MLog compiler** and the **MLog → Python DSL decompiler**.

---

## 1. High-Level System Overview

`mlog-py` is a bidirectional translation framework between a strongly-typed subset of Python and vanilla Mindustry Logic (`mlog`):

```text
               ┌────────────────────────────────────────────────────────┐
               │                   Python Source Code                   │
               └───────────┬────────────────────────────────▲───────────┘
                           │                                │
            ast.parse()    │                                │ Python AST /
          + Whitelist      │                                │ Source Generator
                           ▼                                │
               ┌───────────────────────┐        ┌───────────────────────┐
               │    Python AST Nodes   │        │     Python DSL IR     │
               └───────────┬───────────┘        └───────────▲───────────┘
                           │                                │
            compiler.py    │                                │ semantics.py
            (AST Lowering) │                                │ (Semantic Roles)
                           ▼                                │
               ┌───────────────────────┐        ┌───────────────────────┐
               │      Symbolic IR      │        │       SourceMap       │
               └───────────┬───────────┘        └───────────▲───────────┘
                           │                                │
            optimizer.py   │                                │ sourcemap.py
            (PassThrough)  │                                │ (Provenance)
                           ▼                                │
               ┌───────────────────────┐        ┌───────────────────────┐
               │     Optimized IR      │        │   Function Program    │
               └───────────┬───────────┘        └───────────▲───────────┘
                           │                                │
            emitter.py     │                                │ function_analyzer.py
            (2-Pass Res)   │                                │ (Calling Conv)
                           ▼                                │
               ┌───────────────────────┐        ┌───────────────────────┐
               │      mlog Tokens      │        │     Expression IR     │
               └───────────┬───────────┘        └───────────▲───────────┘
                           │                                │
            validator.py   │                                │ dataflow.py
            (Grammar Check)│                                │ (Use-Def Chains)
                           ▼                                │
               ┌───────────────────────┐        ┌───────────────────────┐
               │  Mindustry Harness    │        │     Structured IR     │
               │   (Java LParser)      │        └───────────▲───────────┘
               └───────────┬───────────┘                    │
                           │                    structurer.py (Dominance)
                           ▼                                │
               ┌───────────────────────┐        ┌───────────────────────┐
               │  Vanilla MLog Output  │───────►│    BasicBlock CFG     │
               └───────────────────────┘        └───────────▲───────────┘
                                                            │
                                                cfg.py + parser.py
```

---

## 2. Compiler Subsystem (Python → MLog)

The forward compiler translates a verified Python subset into canonical MLog instructions:

1. **AST Parsing & Whitelist Validation (`src/parser.py`)**:
   Parses Python source using `ast.parse` and rejects unsupported language features (`classes`, `collections`, `comprehensions`, `try/except`) with exact line and column locations.

2. **Control Flow & Expression Lowering (`src/compiler.py`)**:
   Translates AST nodes into intermediate symbolic IR instructions (`IRLabel`, `IRSet`, `IROp`, `IRJump`, `IRRaw`). Emits compiler temporaries (`__tmp0`, `__tmp1`) for complex expressions and lowers short-circuit boolean conditions (`and`, `or`, `not`).

3. **Optimization Pass (`src/optimizer.py`)**:
   Implements an optimization interface with `PassThroughOptimizer` in Phase 1/2 to preserve deterministic execution and instruction order.

4. **Two-Pass Address Resolution (`src/emitter.py`)**:
   - **Pass 1**: Traverses the IR list to map every `IRLabel` to its instruction address without consuming instruction slots (labels occupy 0 slots).
   - **Pass 2**: Resolves symbolic label targets into 0-indexed numeric jump addresses.

5. **Static Grammar Validation (`src/validator.py`)**:
   Validates opcode bounds, argument counts, 1000 instruction limit, 500 jump limit, and token length limits.

6. **Engine Verification Harness (`src/mindustry_validator.py`, `tools/harness/MindustryHarness.java`)**:
   Verifies emitted mlog bytecode against Mindustry's live `LParser` and `LAssembler` running in the Java Virtual Machine.

> [!NOTE]
> For compiler pipeline passes, syntax subset tables, and CLI usage, see [compiler.md](compiler.md).

---

## 3. Decompiler Subsystem (MLog → Python DSL)

The reverse decompiler reconstructs high-level, human-readable Python DSL from flat MLog instructions across 5 hardened phases:

1. **Phase 1: Line Parsing & CFG Reconstruction (`src/decompiler/parser.py`, `src/decompiler/cfg.py`)**:
   Parses raw MLog into `MlogInstruction` objects, identifies basic block leaders (entry, jump targets, post-jump instructions), and builds a directed Control Flow Graph (CFG) with Fallthrough, Conditional, and Unconditional edges.

2. **Phase 2: Structured Control Flow (`src/decompiler/structurer.py`, `src/decompiler/structured_ir.py`)**:
   Computes dominance frontiers and immediate dominators. Detects natural loop back-edges to reconstruct `WhileNode`, branching trees (`IfNode`, `elif`, `else`), and scoped loop exits (`BreakNode`, `ContinueNode`).
   *Fallback*: Irreducible CFG loops and computed jumps fall back safely to `UnstructuredNode`.

3. **Phase 3: Expression & Dataflow Recovery (`src/decompiler/dataflow.py`, `src/decompiler/expression.py`)**:
   Performs scoped Use-Def analysis to detect single-use compiler temporary variables (`__tmp0`) and collapses them into compound expression trees (`BinaryOpNode`, `UnaryOpNode`, `CallNode`). Preserves multi-use variables to protect program semantics.

4. **Phase 4: Function & Procedure Recovery (`src/decompiler/function_analyzer.py`, `src/decompiler/function_ir.py`)**:
   Analyzes whole-program CFGs to identify calling conventions (`jump`, `set @counter`, return address handling). Reconstructs `FunctionDef`, `CallNode`, and `ReturnNode` structures while preserving global variables.

5. **Phase 4.5 & 5: Source Mapping & Semantic Argument Recovery (`src/decompiler/sourcemap.py`, `src/decompiler/semantics.py`)**:
   Tracks instruction provenance throughout all transformations. Classifies tokens into 6 distinct semantic roles using the Single Source of Truth, ensuring physical hardware links (`"cell1"`, `"display1"`) are emitted as string literals rather than bare undefined Python variables.

> [!NOTE]
> For detailed decompiler passes, see [decompiler.md](decompiler.md). For dedicated specifications, see [source-mapping.md](source-mapping.md) and [semantic-arguments.md](semantic-arguments.md).

---

## 4. Single Source of Truth (SSOT) Architecture

All instruction signatures, opcode rules, enum definitions, and type stubs originate from a single centralized authority:

- **`src/metadata.py`**: Defines `INTRINSICS`, parameter limits, argument signatures, and generates `mlog.pyi`.
- **`src/mlog_registry.py`**: Contains property enums extracted directly from Mindustry Java sources (`LAccess`, `LUnitControl`, `LogicOp`, `Items`, `Liquids`, `Units`, etc.).

Both compiler and decompiler query this SSOT to validate properties and determine argument roles.

---

## 5. Core Operational Principles

1. **Zero Guessing**: If a control flow structure or expression tree cannot be proven mathematically via dominance or Use-Def chains, fall back to safe unstructured representations (`UnstructuredNode`, explicit assignments) rather than inventing speculative code.
2. **Deterministic Round-Trip**: Code compiled to MLog and decompiled back must retain semantic equivalence and recompile cleanly.
3. **Semantic Isolation**: Never modify compiler semantics to accommodate decompiler quirks. The compiler defines the canonical DSL specification.
