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
| **Memory Arrays** | `arr = Array("cell1", size=10)`, `arr[i]`, `arr[i] = val`, `len(arr)` | Contiguous static allocation, `read`, `write` |
| **Augmented Assignments** | `x += 1`, `arr[i] += 5`, `x *= 2`, `flags[i] &= True` | In-place update `op add x x 1`, single-offset `read -> op -> write` |

### Explicitly Rejected Constructs

Features incompatible with Mindustry's flat processor memory model are rejected during AST validation:

- **Classes & Objects**: `class`, inheritance, methods
- **Data Collections**: Lists (`[]`), Dictionaries (`{}`), Sets, Tuples (Dynamic collections are unsupported; use fixed-size `Array` mapped to hardware memory blocks instead)
- **Container Iteration**: `for ... in <collection>` (only `range(...)` is supported), list comprehensions, generator expressions
- **Exceptions**: `try/except`, `raise`, `finally`
- **Asynchronous Code**: `async def`, `await`

### Static Memory Allocation & Array API

The compiler provides a high-level `Array` abstraction backed by hardware Memory Cells and Memory Banks:

```python
from mlog import Array

# Allocate array of 10 integers on cell1 (default dtype=int)
arr_int = Array("cell1", size=10)
arr_int[0] = 42

# Allocate array of 10 floating-point numbers on cell1 (dtype=float)
arr_float = Array("cell1", size=10, dtype=float)
arr_float[0] = 3.14159

# Allocate array of 10 booleans on cell1 (dtype=bool)
arr_bool = Array("cell1", size=10, dtype=bool)
arr_bool[0] = True
```

- **Hardware Capacities & Naming**:
  - Memory Cell (`cell`, `cell1`, `cell2`, ... matching `^cell\d*$`): maximum 64 slots (indices `0..63`).
  - Memory Bank (`bank`, `bank1`, `bank2`, ... matching `^bank\d*$`): maximum 512 slots (indices `0..511`).
  - Block names are normalized case-insensitively (`cell1` and `Cell1` reference the same physical block).
- **Data Types (`dtype`)**:
  - `dtype=int` (default): stores integers. Literal float, string, and boolean assignments are strictly rejected at compile time.
  - `dtype=float`: stores 64-bit IEEE 754 floating-point numbers. Supports float literals, integer literals, and runtime numeric expressions (e.g. `sensor(...)`). String and boolean literals are rejected.
  - `dtype=bool`: stores boolean flags encoded strictly as `False = 0`, `True = 1` (`0.0` and `1.0` in Mindustry double registers).
    - **Literal assignment**: only `True` and `False` are permitted; integer (`0`, `1`), float, and string literals are strictly rejected at compile time and runtime.
    - **Dynamic expression policy**: comparisons (`x > y`) and boolean operations (`not x`) write `0` or `1` directly. General dynamic expressions are automatically normalized via `op notEqual __bool_val expr 0` to preserve the `0`/`1` memory invariant.
    - **NaN / Infinity truthiness nuance**: in Mindustry Logic VM, `LVar.setnum` converts `NaN` and `Infinity` to object `null` (treated as `0.0` in numeric operations), so `op notEqual` normalizes them to `0` (False). In contrast, native Python evaluates `bool(float('nan'))` and `bool(float('inf'))` as `True`.
    - **Reading policy & foreign data divergence**:
      - In runtime Python emulation, reading an element returns `bool` (`True` or `False`). If memory contains a value other than `0` or `1` (e.g. from foreign processor memory corruption or raw `write`), runtime emulation strictly raises `ValueError`.
      - In compiled MLog, reading emits zero-overhead `read dest cell addr` without redundant normalization. If foreign data like `42` exists in the cell, MLog truthiness (`if arr[i]:` testing `!= 0`) evaluates to true, while exact equality (`if arr[i] == True:` testing `== 1`) evaluates to false.
  - Array indices (`arr[i]`): must always be integer slots (`0 <= i < size`) regardless of `dtype`.
- **Static Allocator (`src/allocator.py`)**:
  - Allocates non-overlapping contiguous slices in independent address spaces per block.
  - Slices are packed starting at offset `0`. Subsequent arrays on the same block advance the offset.
  - Enforces total allocated size $\le$ block capacity; raises compile-time errors if capacity is exceeded.
  - Top-level arrays are registered in a compiler pre-pass, ensuring full visibility inside procedures (`allow_functions=True`).
- **Index Bounds & Type Safety Limits**:
  - **Static bounds checking**: Literal indices outside `[0, size - 1]` trigger compile-time `CompileError`. Literal negative indices, floats, strings, and booleans are strictly rejected at compile time.
  - **Unchecked dynamic bounds**: For dynamic indices (`arr[i]` where `i` is a variable or runtime expression), bounds checking is not emitted by default to preserve processor instruction budget (1000 instruction limit). If a dynamic index exceeds `size` on a shared block, it may access or overwrite adjacent arrays on that block.
  - **Type enforcement limits**: Array elements must match the array's `dtype`. Dynamic expressions write their computed runtime value directly to the underlying memory block.
  - **Constant length**: `len(arr)` resolves at compile time to the static integer size.
- **Base Offset Optimization**:
  - When `base_offset == 0`, dynamic index reads/writes directly reference the index operand without an extra addition instruction.
  - When `base_offset > 0`, the compiler emits `op add __tmp index base_offset` before `read`/`write`.

### Augmented Assignment & Single-Evaluation Semantics

The compiler fully supports in-place augmented assignments on scalar variables and array elements:

```python
x += 1
total *= 2
arr[i] += 10
flags[0] ^= True
```

- **Supported Operators (12 total)**:
  - Arithmetic: `+=` (`add`), `-=` (`sub`), `*=` (`mul`), `/=` (`div`), `//=` (`idiv`), `%=` (`mod`), `**=` (`pow`)
  - Bitwise: `&=` (`and`), `|=` (`or`), `^=` (`xor`), `<<=` (`shl`), `>>=` (`shr`)
- **Unsupported Operators**:
  - Matrix multiplication `@=` (`ast.MatMult`) has no Mindustry Logic semantics and is strictly rejected at compile time (`CompileError: unsupported augmented assignment operator: '@='`).
- **Scalar Variables**:
  - Lowered directly to `op <opcode> <target> <target> <rhs_value>` without allocating unnecessary intermediate destination registers.
  - The right-hand side expression is evaluated first, preventing any clobbering of the target variable.
- **Array Elements (`arr[i] op= val`) & Single-Evaluation Guarantee**:
  - **Single Address Calculation**: When targeting array elements (`arr[expr] += val`), the index expression `expr` and physical base offset (`base_offset`) are evaluated **exactly once**.
  - **Shared Address Register**: The resolved address register is stored in a temporary variable and reused for both the initial `read` instruction and the subsequent `write` instruction. Subscript expressions with complex calculations or side effects are never recomputed.
  - **Dtype Type Safety Rules**:
    - `dtype=int`: supports all 12 operators; strictly rejects float, string, and boolean literal operands.
    - `dtype=float`: supports arithmetic operators; bitwise operators (`&=`, `|=`, `^=`, `<<=`, `>>=`) are rejected.
    - `dtype=bool`: supports boolean bitwise operators (`&=`, `|=`, `^=`); arithmetic operators (`+=`, etc.) and non-boolean literals are rejected. Dynamic RHS expressions are automatically normalized to boolean (0 or 1) via `op notEqual` before applying the bitwise operation.

### Sensor Properties & Hardware Attributes

The compiler supports all Mindustry `LAccess` properties via the `SensorProperty` registry enum and canonical string/identifier tokens:

```python
from mlog import sensor, SensorProperty

# Enum access (Recommended, fully typed)
hp = sensor(vault1, SensorProperty.HEALTH)
is_on = sensor(switch1, SensorProperty.ENABLED)
cfg = sensor(sorter1, SensorProperty.CONFIG)

# Canonical string token access
hp = sensor(vault1, "@health")
is_on = sensor(switch1, "@enabled")

# Statement form
sensor(hp, vault1, SensorProperty.HEALTH)
```

- **Dual-Purpose Controllable & Senseable Properties**:
  - Properties with parameter length $\le 1$ in Mindustry's engine (`@enabled`, `@config`, `@color`) are both controllable and senseable. The compiler fully recognizes them in both `sensor()` and `control()` contexts.
- **Supported Property Registry**:
  - Full set of item, liquid, block, unit, and world attributes (e.g. `@health`, `@maxHealth`, `@efficiency`, `@progress`, `@totalItems`, `@firstItem`, `@copper`, `@lead`, `@water`, `@cryofluid`, etc.).

---

## 2. Compilation Pipeline Passes

```text
Python Source (.py)
       │
       ▼
 [parser.py]          AST Validation & Whitelisting
       │
       ▼
 [compiler.py]        Compile-Time Constant Folding (AST Pass)
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

### Pass 2: Compile-Time Constant Folding & Symbolic IR Lowering (`src/compiler.py`)

#### Compile-Time Constant Folding (`ConstantFolder`)

Before lowering to IR, pure compile-time constant expressions are recursively evaluated:

- **Supported Operations**:
  - Arithmetic: `+`, `-`, `*`, `/`, `//`, `%`, `**`
  - Bitwise: `&`, `|`, `^`, `<<`, `>>`
  - Comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`
  - Boolean: `and`, `or`, `not`
  - String concatenation: `+` on string literals
- **Semantic Preservation (Mindustry & Python Fidelity)**:
  - **Safe Integer Limits**: Restricted to IEEE-754 double precision bounds `[-9007199254740991, 9007199254740991]` (`2^53 - 1`). Larger operations defer to runtime to preserve exact Mindustry engine precision behaviors.
  - **Modulo (`%`)**: Only non-negative modulo (`left >= 0 and right > 0`) is folded. Negative modulo operations defer to runtime to match Mindustry's truncated modulo.
  - **Division by Zero**: Skipped at compile time and emitted as `op div`/`op idiv` so Mindustry handles IEEE-754 `Infinity`/`NaN` at runtime.
  - **Shift Bounds**: Shift counts `< 0` or `>= 64` are left unfolded to allow standard compiler error validation.
  - **Intrinsics**: `min()` and `max()` function calls are never folded, preserving native `op min` and `op max` instruction dispatch.
  - **Standalone Literals**: Standalone negative numbers (`-5`) and bitwise inverts (`~5`) preserve native lowering (`op sub 0 5` and `op not 5 0`).
- **Array Static Resolution**:
  - `Array("cell1", size=2 * 8)`: Resolves array size statically to 16 before memory allocation.
  - `arr[1 + 2] = 42`: Folds index offset statically to slot 3, eliminating temporary variable creation and enabling static bounds checking.
- **Strictly No Dead Code Elimination**: Control flow structures (`If`, `While`, `For`) and dead branches are never stripped or pruned; conditional jumps and dead branch bodies remain fully preserved.

#### Symbolic IR Lowering

Lowers AST statements and expressions into symbolic IR nodes (`IRLabel`, `IRSet`, `IROp`, `IRJump`, `IRRaw`):

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

# Disable compile-time constant folding
mlog-py compile input.py -o output.mlog --no-fold-constants

# Validate with official Mindustry engine (requires Java)
mlog-py compile input.py --mindustry
```

### Python API

```python
from src.mlog import compile_py

python_source = """
from mlog import printflush
x = (10 + 20) * 2
print(x)
printflush("message1")
"""

# Standard compilation (with constant folding enabled by default)
result = compile_py(python_source, filename="example.py")
print(result.mlog)
# Output:
# set x 60
# print x
# printflush message1

# Disable constant folding
result_unfolded = compile_py(python_source, fold_constants=False)

# Compilation with functions enabled
result_fn = compile_py(python_source, allow_functions=True)
```
