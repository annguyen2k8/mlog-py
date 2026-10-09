# mlog-py Examples Directory

This directory contains verified, paired examples showcasing compilation (Python DSL $\to$ MLog) and decompilation (MLog $\to$ Python DSL).

---

## 1. Compiler Examples (`examples/compiler/`)

Each example consists of a Python source file (`.py`) and its compiled vanilla Mindustry Logic output (`.mlog`).

| File | Description |
| :--- | :--- |
| `for_range.py` / `.mlog` | **For-Range Loops**: `for i in range(start, stop, step)` with loop step latch, and `break` / `continue` statements in `if` branches. |
| `bitwise_operations.py` / `.mlog` | **Bitwise Operators**: `&`, `\|`, `^`, `~`, `<<`, `>>` with 64-bit integer hardening. |
| `min_max.py` / `.mlog` | **Math Built-ins**: Native lowering of `min()` and `max()` to `op min` and `op max`. |
| `while_break_continue.py` / `.mlog` | **While Loops**: `while` loops with early `break` and latch `continue`. |
| `if_elif_else.py` / `.mlog` | **Conditionals**: Nested `if`, `elif`, and `else` control flow ladders. |
| `nested_control_flow.py` / `.mlog` | **Nested Loops**: Multi-level nested loops with matrix coordinate indexing and messages. |
| `reactor_control.py` / `.mlog` | **Thorium Reactor Controller**: Temperature sensing and automatic emergency toggle. |
| `display_draw.py` / `.mlog` | **Logic Display Graphics**: Drawing primitives (`clear`, `color`, `rect`, `line`) and `drawflush`. |
| `print_message.py` / `.mlog` | **Message Buffer**: Multi-part string concatenation and `printflush`. |
| `memory_cell.py` / `.mlog` | **Memory Cell I/O**: Direct `read` and `write` addressing on memory cells. |
| `block_vs_variable.py` / `.mlog` | **Semantic Block Links**: Differentiating dynamic variable references from block names. |
| `special_constants.py` / `.mlog` | **Built-in Constants**: Built-in Mindustry variables (`@this`, `@time`, `@counter`). |
| `arithmetic_dataflow.py` / `.mlog` | **Arithmetic Lowering**: Binary operations with temporary register allocations. |
| `functions.py` / `.mlog` | **Function Calling**: Reusable procedures with argument registers and return addresses. |
| `roundtrip_demo.py` | **Compiler Runner**: Standalone runner demonstrating compilation across multiple patterns. |

Run the compilation demo:
```bash
python3 examples/compiler/roundtrip_demo.py
```

---

## 2. Decompiler Examples (`examples/decompiler/`)

Examples demonstrating bytecode disassembly, CFG reconstruction, expression folding, and self-contained import generation.

| File | Description |
| :--- | :--- |
| `bitwise_dataflow.py` / `.mlog` | **Bitwise Expression Recovery**: Recovers `op and`, `op or`, `op xor`, `op not`, `op shl`, `op shr` to clean Python operators. |
| `min_max_recovery.py` / `.mlog` | **Min/Max Recovery**: Recovers `op min` and `op max` to native Python `min()` and `max()`. |
| `reactor_safety.py` / `.mlog` | **Control Flow Structuring**: Recovers branch jumps into clean `if-else` blocks and sensors. |
| `nested_loops.py` / `.mlog` | **Nested Loop Recovery**: Natural loop back-edge detection into nested `while` structures. |
| `branch_ladder.py` / `.mlog` | **Branch Ladder Structuring**: Recovers complex multi-way jump cascades. |
| `display_graphics.py` / `.mlog` | **Drawing API Recovery**: Reconstructs display calls with typed `from mlog import draw, drawflush`. |
| `print_buffer.py` / `.mlog` | **Print Semantics**: Preserves string literals and processor textBuffer flushes. |
| `memory_cell_io.py` / `.mlog` | **Cell Addressing**: Recovers `read` and `write` intrinsics. |
| `block_vs_variable.py` / `.mlog` | **Semantic Disambiguation**: Differentiates hardware strings (`"cell1"`) from variables (`b`). |
| `special_registers.py` / `.mlog` | **Special Registers**: Quotes special in-game constants (`"@this"`, `"@counter"`). |
| `function_procedure.py` / `.mlog` | **Procedure Recovery**: Detects return address patterns and call-site jumps. |
| `roundtrip_verify.py` | **Round-Trip Harness**: Verifies 100% bytecode and AST equivalence across decompilation and recompilation. |
| `sourcemap_debug.py` | **SourceMap Provenance**: Demonstrates bidirectional line mapping between MLog instructions and Python statements. |

Run the round-trip verification demo:
```bash
python3 examples/decompiler/roundtrip_verify.py
```
