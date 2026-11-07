# mlog-py Examples Directory

This directory contains paired, verified examples demonstrating both compilation (Python DSL $\to$ MLog) and decompilation (MLog $\to$ Python DSL). Every example is beginner-friendly, clean, and directly runnable.

---

## 1. Compiler Examples (`examples/compiler/`)

These examples show how to write Python code that compiles directly into Mindustry Logic bytecode (`.mlog`). Each example has a `.py` source file and its companion `.mlog` output.

| File | Topic | Beginner Description |
| :--- | :--- | :--- |
| [`arithmetic.py`](compiler/arithmetic.py) | Basic Math | Arithmetic operations (`+`, `-`, `*`, `/`, `//`, `%`) with automatic temporary register allocation. |
| [`bitwise.py`](compiler/bitwise.py) | Bitwise Logic | Integer bit manipulation (`&`, `\|`, `^`, `~`, `<<`, `>>`) with safe 64-bit boundaries. |
| [`min_max.py`](compiler/min_max.py) | Min / Max Math | Native `min()` and `max()` calls lowering directly to Mindustry `op min` and `op max`. |
| [`for_loop.py`](compiler/for_loop.py) | For Loops | Step-based loops `for i in range(start, stop, step)` with `continue` and `break` in `if` branches. |
| [`while_loop.py`](compiler/while_loop.py) | While Loops | Condition-based `while` loops with early `break` and loop skipping via `continue`. |
| [`conditionals.py`](compiler/conditionals.py) | If / Elif / Else | Decision-making branching with short-circuit evaluation. |
| [`nested_loops.py`](compiler/nested_loops.py) | Nested Loops | Multi-level matrix grid loops calculating 2D coordinates. |
| [`reactor_safety.py`](compiler/reactor_safety.py) | Reactor Controller | Thorium reactor safety monitor: reading `@heat` and toggling `control.enabled(...)`. |
| [`control_building.py`](compiler/control_building.py) | Building Control Modes | All five Mindustry v160.7 control modes (`enabled`, `shoot`, `shootp`, `config`, `color`) plus legacy `control(...)`. |
| [`display_graphics.py`](compiler/display_graphics.py) | Logic Displays | Drawing shapes (`clear`, `color`, `rect`, `line`) and flushing to display screens. |
| [`color_channels.py`](compiler/color_channels.py) | Color Channels | Packing RGBA with `packcolor` and unpacking it back with `r, g, b, a = unpackcolor(color)`. |
| [`print_message.py`](compiler/print_message.py) | Message Displays | Concatenating text into processor buffers and outputting to message blocks via `printflush`. |
| [`memory_cell.py`](compiler/memory_cell.py) | Memory Cells | Saving and loading persistent variables using `read()` and `write()` on memory cells. |
| [`array_memory.py`](compiler/array_memory.py) | Legacy Memory Arrays | Backward-compatible `Array` API with static contiguous packing on cells/banks (`from mlog import Array`). |
| [`beta_local_array.py`](compiler/beta_local_array.py) | Local Register Arrays | Modern register-backed `LocalArray` requiring zero memory blocks on map (`from mlog.beta import Array`). |
| [`beta_block_array.py`](compiler/beta_block_array.py) | Hardware Block Arrays | Modern hardware block `BlockArray` with dynamic loop indexing and `.fill()` (`from mlog.beta import Array`). |
| [`constant_folding.py`](compiler/constant_folding.py) | Constant Folding | Compile-time evaluation of pure constant expressions, bitwise masks, and static array subscripts. |
| [`aug_assign.py`](compiler/aug_assign.py) | Augmented Assignment | In-place variable and array element arithmetic & bitwise updates with single-offset evaluation. |
| [`block_vs_variable.py`](compiler/block_vs_variable.py) | Block Links vs Variables | Clear distinction between hardware link names (`"cell1"`) and dynamic variables (`b`). |
| [`special_constants.py`](compiler/special_constants.py) | Special Variables | Using built-in game constants and registers (`@this`, `@time`, `@counter`, `@health`). |
| [`unit_operations.py`](compiler/unit_operations.py) | Unit Control Operations | Canonical Mindustry unit logic APIs (`ubind`, `ulocate`, `uradar`, `ucontrol`) and combat tactics. |
| [`functions.py`](compiler/functions.py) | Custom Procedures | Defining reusable functions with arguments and return values. |
| [`roundtrip_demo.py`](compiler/roundtrip_demo.py) | Interactive Demo | Standalone script demonstrating live compilation of multiple beginner patterns. |

### How to Compile Any Example

From the repository root:

```bash
# Compile to console output (using mlog, mlog-py, or python -m mlog)
mlog compile examples/compiler/for_loop.py

# Or piped from stdin:
cat examples/compiler/for_loop.py | mlog compile

# Or run the integrated demonstration runner
python3 examples/compiler/roundtrip_demo.py
```

---

## 2. Decompiler Examples (`examples/decompiler/`)

These examples show how raw Mindustry Logic (`.mlog`) decompiles back into clean, readable Python code.

| File | Topic | Beginner Description |
| :--- | :--- | :--- |
| [`arithmetic.py`](decompiler/arithmetic.py) | Math Recovery | Folds temporary assembly variables into natural Python expressions (`x + y * 2`). |
| [`bitwise.py`](decompiler/bitwise.py) | Bitwise Recovery | Reconstructs raw `op and`, `op or`, `op xor`, `op not`, `op shl`, `op shr` to standard Python symbols. |
| [`min_max.py`](decompiler/min_max.py) | Min / Max Recovery | Recovers `op min` and `op max` to native Python `min()` and `max()` calls. |
| [`conditionals.py`](decompiler/conditionals.py) | Branch Structuring | Reconstructs spaghetti jump chains into clean `if-elif-else` code blocks. |
| [`nested_loops.py`](decompiler/nested_loops.py) | Loop Structuring | Detects backward jump edges and recreates structured `while` loops. |
| [`reactor_safety.py`](decompiler/reactor_safety.py) | Reactor Safety | Reconstructs real-world reactor logic with sensor reads and hardware controls. |
| [`display_graphics.py`](decompiler/display_graphics.py) | Display Graphics | Disassembles display drawing commands with clean `from mlog import draw, drawflush`. |
| [`print_message.py`](decompiler/print_message.py) | Message Printing | Recovers text buffer concatenation and message flushes. |
| [`memory_cell.py`](decompiler/memory_cell.py) | Memory Cell I/O | Recovers indexed `read()` and `write()` operations. |
| [`block_vs_variable.py`](decompiler/block_vs_variable.py) | Semantic Disambiguation | Quotes hardware blocks (`"cell1"`) while keeping program variables unquoted. |
| [`special_constants.py`](decompiler/special_constants.py) | Special Registers | Quotes special game variables (`"@this"`, `"@counter"`). |
| [`functions.py`](decompiler/functions.py) | Procedure Detection | Recovers function declarations (`def ...`) from call-site jumps. |
| [`roundtrip_verify.py`](decompiler/roundtrip_verify.py) | Verification Harness | Automated verification script confirming 100% round-trip bytecode equivalence. |
| [`sourcemap_debug.py`](decompiler/sourcemap_debug.py) | Source Mapping | Shows exact line-by-line provenance linking Python lines to MLog addresses. |

### How to Decompile Any Example

From the repository root:

```bash
# Decompile to console output (using mlog, mlog-py, or python -m mlog)
mlog decompile examples/decompiler/reactor_safety.mlog

# Or piped from stdin:
cat examples/decompiler/reactor_safety.mlog | mlog decompile

# Or run the round-trip verification suite
python3 examples/decompiler/roundtrip_verify.py
```

---

## 3. Array Programming in mlog-py: Legacy vs. Beta APIs

mlog-py provides two distinct array programming models tailored to different Mindustry processor architectures:

### Summary Comparison

| Feature | Legacy Array (`from mlog import Array`) | Modern LocalArray (`from mlog.beta import Array`) | Modern BlockArray (`from mlog.beta import Array`) |
| :--- | :--- | :--- | :--- |
| **Constructor** | `Array(block, size, dtype=...)` | `Array(size, dtype=...)` or `Array[T](size)` | `Array(block, size, dtype=...)` or `Array[T](block, size)` |
| **Backing Storage** | Hardware Memory Cell (64) / Bank (512) | Processor Registers (`name_0`, `name_1`, ...) | Hardware Memory Cell (64) / Bank (512) |
| **Hardware Link Required** | Yes (`cell1`, `bank1`, etc.) | **No** (Zero external blocks needed) | Yes (`cell1`, `bank1`, etc.) |
| **Dynamic Indexing (`arr[i]`)**| Yes (lowers to `read`/`write` with offset) | No (Static constants only: `arr[0]`, `arr[1]`) | Yes (lowers to native `read`/`write`) |
| **Capacity Limit** | Multiple arrays packed per block | Maximum 64 registers per array | Single block capacity (64 for cell, 512 for bank)|
| **Performance** | Memory I/O cycle latency | Ultra-fast direct register operations | Memory I/O cycle latency |
| **Recommended Use** | Backward compatibility | Math vectors, small LUTs, coordinate tuples | Large buffers, dynamic looping, hardware sharing |

### Architectural Boundaries & Limitations of `mlog.beta`

1. **LocalArray Static Indexing Boundary**: Processor registers in Mindustry Logic cannot be computed dynamically at runtime. Consequently, expressions like `coords[i]` on a `LocalArray` where `i` is a variable or runtime expression raise a compile-time `CompileError`. Use `BlockArray` whenever variable/loop indexing is needed.
2. **LocalArray Capacity Limit**: `LocalArray` size is constrained to $1 \le \text{size} \le 64$ to prevent exhausting the processor's variable pool and instruction budget.
3. **BlockArray Single Block Boundary**: Unlike the legacy allocator which packed multiple contiguous sub-arrays into one cell, each `BlockArray` instance binds exclusively to a dedicated physical memory block.
4. **LocalArray Has No `.block`**: Because `LocalArray` is purely register-backed and has no physical memory block on the map, accessing `.block` raises an `AttributeError`.
