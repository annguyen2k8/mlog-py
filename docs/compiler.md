# Python → MLog Compiler

This document details the architecture and operational passes of the `mlog-py` compiler subsystem.

---

## 1. Supported Language Subset

The compiler targets a strict, strongly-typed subset of Python designed for Mindustry processor execution:

| Feature | Supported Syntax | Output MLog Example |
| :--- | :--- | :--- |
| **Assignments** | `x = 10`, `b = a` | `set x 10`, `set b a` |
| **Arithmetic** | `+`, `-`, `*`, `/`, `//`, `%`, `**` | `op add`, `op sub`, `op mul`, `op div`, `op idiv`, `op mod`, `op pow` |
| **Bitwise Operators** | `&`, `\|`, `^`, `~`, `<<`, `>>` | `op and`, `op or`, `op xor`, `op not`, `op shl`, `op shr` |
| **Math Functions** | `min(a, b)`, `max(a, b)` | `op min dest a b`, `op max dest a b` |
| **Comparisons** | `==`, `!=`, `<`, `<=`, `>`, `>=` | `op equal`, `op notEqual`, `op lessThan`, `op lessThanEq` |
| **Boolean Logic** | `and`, `or`, `not` | Short-circuit conditional jumps |
| **Control Flow** | `if`, `elif`, `else`, `while`, `for ... in range(...)`, `break`, `continue` | Forward and backward numeric jumps |
| **Built-in Registers** | `@counter`, `@time`, `@tick`, `@unit` | Runtime processor registers |
| **Intrinsics** | `sensor()`, `control()`, `draw()`, `read()`, `write()`, etc. | Canonical Mindustry Logic instructions |

### Explicitly Rejected Constructs

Features incompatible with Mindustry's flat processor memory model are rejected during AST validation:

- **Classes & Objects**: `class`, inheritance, methods
- **Data Collections**: Lists (`[]`), Dictionaries (`{}`), Sets, Tuples
- **Container Iteration**: `for ... in <collection>` (only `range(...)` is supported), list comprehensions, generator expressions
- **Exceptions**: `try/except`, `raise`, `finally`
- **Asynchronous Code**: `async def`, `await`

---

## 2. Compilation Pipeline Passes

```text
Python Source (.py)
       │
       ▼
 [parser.py]          AST Validation & Whitelisting
       │
       ▼
 [compiler.py]        AST Lowering to Symbolic IR & Temporary Variable Generation
       │
       ▼
 [optimizer.py]       PassThrough Optimization Interface
       │
       ▼
 [emitter.py]         Two-Pass Address Resolution (Labels -> Numeric Line Targets)
       │
       ▼
 [validator.py]       Static Grammar & Processor Limits Validation
       │
       ▼
 [Mindustry Harness]  Live Mindustry Engine Assembly (LParser & LAssembler)
       │
       ▼
Vanilla MLog (.mlog)
```

### Pass 1: AST Parsing & Whitelisting (`src/parser.py`)

Validates that every AST node belongs to the supported subset. Reports syntax errors with precise source coordinates (`filename:line:col`).

### Pass 2: Symbolic IR Lowering (`src/compiler.py`)

Lowers Python AST statements and expressions into symbolic IR nodes (`IRLabel`, `IRSet`, `IROp`, `IRJump`, `IRRaw`).

- **Temporary Generation**: Deterministic naming (`__tmp0`, `__tmp1`, ...) for nested expression intermediate values.
- **Short-Circuit Evaluation**: Translates `and` / `or` chains into conditional branch ladders:
  - `a and b`: if `a` is false, jumps immediately to end without evaluating `b`.
  - `a or b`: if `a` is true, jumps immediately to then-branch without evaluating `b`.
- **Loop Scoping**: Maintains loop context stacks so `break` and `continue` jump accurately to the loop's exit label and latch label respectively.

### Pass 3: Optimization Pass (`src/optimizer.py`)

The `PassThroughOptimizer` verifies IR integrity and preserves instruction sequencing and register assignments.

### Pass 4: Two-Pass Address Resolution (`src/emitter.py`)

MLog jump instructions require 0-indexed numeric line numbers, whereas labels occupy 0 slots in the final output:

1. **Pass 1 (Label Table Construction)**: Scans all IR nodes. When encountering an `IRLabel`, records its symbolic name mapped to the current instruction index without incrementing the instruction pointer.
2. **Pass 2 (Address Substitution)**: Iterates over non-label instructions. Replaces all symbolic jump targets with their resolved integer line targets.

### Pass 5: Static Validation (`src/validator.py`)

Validates the emitted MLog against vanilla Mindustry processor constraints:

- Maximum 1000 instructions per processor.
- Maximum 500 jump instructions per processor.
- Maximum 16 arguments/tokens per instruction.
- Opcode and argument validity checks.

---

## 3. Compiler CLI & API

### Command Line Interface

```bash
# Compile Python file to stdout
mlog-py compile input.py

# Compile Python file to output mlog
mlog-py compile input.py -o output.mlog

# Inspect IR instructions and resolved label table
mlog-py compile input.py --debug
```

### Python API

```python
from src.mlog import compile_py

python_source = """
from mlog import printflush
print("hello world")
printflush("message1")
"""

# Standard compilation
result = compile_py(python_source, filename="example.py")
print(result.mlog)

# Compilation with functions enabled
result = compile_py(python_source, allow_functions=True)
```
