# mlog-py: Python-to-Mindustry Logic (mlog) Transpiler / Compiler & Decompiler

A robust, verified compiler and decompiler suite connecting a strongly-typed subset of Python with vanilla Mindustry Logic (mlog).

## Project Structure

```text
mlog-py/
├── SKILL.md                 # Master operational skill manual for agents
├── README.md                # Quick-start, CLI, and architecture overview
├── compiler.py              # CLI entry point for the compiler
├── mlog.py / mlog.pyi       # Runtime DSL module and IDE typing stubs
├── docs/                    # Deep-dive architecture and pass specifications
│   ├── architecture.md      # Unified system architecture & pipeline
│   ├── compiler.md          # AST lowering, two-pass resolution, validator
│   ├── decompiler.md        # CFG, structurer, dataflow, function recovery
│   ├── source-mapping.md    # Provenance tracking, debug comments & JSON
│   └── semantic-arguments.md# Semantic role recovery & device quoting
├── examples/                # Runnable, verified paired examples
│   ├── compiler/            # Python DSL -> MLog examples
│   └── decompiler/          # MLog -> Python DSL examples
├── src/                     # Core compiler and decompiler source code
│   ├── metadata.py          # Single Source of Truth (SSOT)
│   ├── compiler.py          # AST -> IR lowering
│   ├── emitter.py           # Two-pass address resolution
│   ├── validator.py         # Static grammar & processor limits
│   └── decompiler/          # Decompiler subsystem (Phases 1–5)
└── tests/                   # 281 automated test cases
    └── corpus/              # 32-case real-world corpus
```

## Quick Start

### 1. Compile Python to MLog
```bash
# Compile a Python DSL script to stdout
python3 compiler.py examples/compiler/reactor_control.py

# Compile and output to a file
python3 compiler.py examples/compiler/reactor_control.py -o reactor.mlog

# Run compiler demonstration script
python3 examples/compiler/roundtrip_demo.py
```

### 2. Decompile MLog to Python DSL
```python
from src.decompiler import decompile, decompile_with_source_map

# Decompile MLog to Python DSL
py_code = decompile("sensor heat reactor1 @heat\njump 4 lessThanEq heat 0.5\n")

# Decompile with inline provenance comments (# mlog[<addr>])
debug_code = decompile(mlog_text, debug=True)

# Run decompiler SourceMap & round-trip verification scripts
python3 examples/decompiler/sourcemap_debug.py
python3 examples/decompiler/roundtrip_verify.py
```

## Features Supported

- **Variables & Assignments**:
  - `x = 10`, `y = 3.14`, `msg = "hello"`
  - `b = a`
- **Arithmetic Operators**:
  - `+` (`op add`), `-` (`op sub`), `*` (`op mul`), `/` (`op div`), `//` (`op idiv`), `%` (`op mod`)
  - Nested expressions automatically lowered with deterministic compiler temporaries (`__tmp0`, `__tmp1`, ...)
- **Comparisons**:
  - `==`, `!=`, `<`, `<=`, `>`, `>=`
- **Boolean Logic with Short-Circuiting**:
  - `if a and b:` short-circuits: does not evaluate `b` if `a` is false
  - `if a or b:` short-circuits: does not evaluate `b` if `a` is true
  - `if not a:` inverts condition
- **Control Flow**:
  - `if`, `elif`, `else`
  - `while` loops
  - `break` and `continue`
  - Arbitrarily nested loops and conditionals
  - Internal label generation (`__while_start_N`, `__while_end_N`, `__if_else_N`, `__if_end_N`) automatically resolved to 0-indexed numeric instruction addresses
- **@counter Semantics**:
  - Fully preserved: `set("@counter", x)`, `at_counter = 10`, or `counter = 0`
  - Never unsafely reordered or optimized away
- **Mindustry Compiler Intrinsics**:
  - Memory I/O: `read()`, `write()`, `getlink()`
  - Graphics: `draw()`, `drawflush()`, `packcolor()`
  - Text: `print()`, `printflush()`
  - Sensing & Control: `sensor()`, `control()`
  - Unit Control: `ubind()`, `ucontrol()`, `radar()`, `uradar()`, `ulocate()`, `lookup()`
  - Execution: `wait()`, `stop()`, `end()`
  - Direct ops: `op()`, `set()`, `jump()`
- **Verified Registry & Python DSL Enums**:
  - Extracted directly from Mindustry source (`LAccess.java`, `LUnitControl.java`, `LogicOp.java`, `ConditionOp.java`, `Items.java`, `Liquids.java`, `UnitTypes.java`, `Team.java`, etc.)
  - Python DSL Enums: `SensorProperty`, `ControlProperty`, `UnitControl`, `DrawType`, `LogicOp`, `Condition`, `Items`, `Liquids`, `Units`, `Teams`, `RadarTarget`, `RadarSort`, `LookupType`
  - Strict typo rejection with source location: e.g. `sensor(b, "@healht")` -> `unknown sensor property '@healht'`
  - Clear distinction between Python identifier (`SensorProperty.HEALTH`), compiler value (`"@health"`), and emitted mlog token (`@health`)
  - Explicit forward-compatibility escape hatch: `raw("@newProperty")` bypasses validation for custom/unreleased properties without compromising default validation
- **Official Import API & VS Code / Pylance IDE Stubs**:
  - Official DSL import entry point:
    ```python
    from mlog import jump, set, op, sensor, control, ucontrol, draw, read, write, wait, stop, end
    from mlog import SensorProperty, ControlProperty, UnitControl, DrawType, LogicOp, Condition, Units, raw, null
    ```
  - Full Pylance / VS Code autocompletion, signature help, and parameter tooltips powered by `mlog.pyi`.
  - Single Source of Truth (`src/metadata.py`) keeps compiler AST checks, runtime module, and typing stubs strictly synchronized.
- **Precise Source Locations**:
  - Every error reports exact `file:line:col: message`
  - Unsupported Python features (lists, dicts, def, class, non-mlog imports, etc.) rejected with clear explanations

## Decompiler Pipeline (mlog → Python DSL)

```text
Vanilla mlog Source (.mlog)
       ↓
 [parser.py]          Phase 1: Mlog Parser & Instruction IR (Tokenization, Opcode Validation)
       ↓
   [cfg.py]           Phase 1: CFG Reconstruction (Basic Blocks, Edges: Fallthrough, Conditional, Unconditional)
       ↓
[structurer.py]       Phase 2: Control-Flow Structuring (Dominance Analysis, Loop Back-edges, If/Else, While)
       ↓
 [dataflow.py]        Phase 3: Expression & Dataflow Recovery (Use-Def analysis, Safe Inlining, Temp Collapsing)
       ↓
[function_analyzer.py] Phase 4: Function Recovery (FunctionDef, CallNode, ReturnNode, Calling Conventions)
       ↓
[sourcemap.py]        Phase 4.5: Source Mapping & Debug Mode (Provenance Tracking, Bi-directional Lookup, Debug Comments)
       ↓
[semantics.py]        Phase 5: SSOT Semantic Argument Recovery (Named Hardware Links, @constants, Program Variables)
       ↓
Python DSL Source (.py) / SourceMap (.json)
```

### Decompiler Capabilities
- **Phase 1 (Parser & CFG)**: Strict line-by-line parsing with source location tracking, BasicBlock decomposition, and CFG edge reconstruction.
- **Phase 2 (Structured Control Flow)**: Natural loop header/latch recovery (`while`), branching (`if`, `elif`, `else`), `break` and `continue` resolution.
- **Phase 3 (Expression & Dataflow)**: Single-use compiler temporary collapsing (`__tmp0`), arithmetic/comparison expression tree recovery, constant and copy propagation with zero guessing.
- **Phase 4 (Function Recovery)**: Calling convention detection (`call`, `set __ret_addr`, parameter binding, return value recovery), whole-program `FunctionProgram` structure.
- **Phase 4.5 (Source Mapping & Debug Mode)**:
  - Provenance tracking across the entire pipeline from MLog addresses to Python statements.
  - Multi-instruction provenance preservation when collapsing temporaries (e.g. `x = a + 1` preserves all `[set, op, set]` addresses).
  - Debug mode (`debug=True` / `decompile(mlog, debug=True)`): emits non-intrusive `# mlog[<addr>]` or `# mlog[<addr>-<addr>]` comments above each statement.
  - Machine-readable SourceMap JSON serialization (`to_json()`, `from_json()`, version `1.0`).
  - Bi-directional source lookup: `python_to_mlog(python_line)` and `mlog_to_python(mlog_addr)`.
- **Phase 5 (Semantic Argument Recovery & Real-World Hardening)**:
  - SSOT-backed classification of arguments into 6 distinct semantic roles using `src/metadata.py`:
    1. **MLog program variables**: `x`, `val`, `total`, `idx`
    2. **Named hardware links**: physical devices (`"cell1"`, `"display1"`, `"message1"`, `"vault1"`, `"reactor1"`) emitted as quoted string literals
    3. **Special constants**: `"@unit"`, `"@counter"`, `"@health"`, `"@copper"`
    4. **DSL Enums/keywords**: `DrawType.CLEAR`, `SensorProperty.HEALTH`
    5. **Literals**: numeric and string literals preserved verbatim
    6. **Variables holding block references**: dynamic variables bound via `getlink(b, 0)` remain unquoted identifiers
  - Structured 32-program test corpus across 6 categories: `handwritten`, `compiler_generated`, `control_flow`, `functions`, `mindustry_api`, and `pathological`.
  - 100% round-trip verification: MLog → Python DSL (`ast.parse`, `py_compile`) → `compile_py` → valid canonical MLog bytecode.
  - Linear scaling performance benchmark: 100, 500, and 1000 instructions scale strictly linearly $O(N)$ with zero quadratic blowup (1000 instructions decompile in ~0.44s with ~2.27MB peak memory).
  - Strict **Zero Guessing** hardened: Irreducible loops, computed jumps, and unstructured spaghetti jumps fall back safely to `UnstructuredNode`.

## Python API

### Compiler API
```python
from src.mlog import compile_py

# Basic compilation
result = compile_py(python_source, filename="script.py")
print(result.mlog)

# Compilation with functions enabled
result = compile_py(python_source, allow_functions=True)
```

### Decompiler API
```python
from src.decompiler import decompile, decompile_with_source_map

# Standard decompilation to clean Python DSL source
py_code = decompile(mlog_text)

# Decompilation with inline provenance comments (# mlog[<addr>])
debug_py_code = decompile(mlog_text, debug=True)

# Decompilation with complete SourceMap object
clean_py_code, sourcemap = decompile_with_source_map(mlog_text)

# Querying bi-directional line mappings
mlog_addrs = sourcemap.python_to_mlog(python_line=3)
py_line = sourcemap.mlog_to_python(mlog_address=2)

# Exporting SourceMap to JSON
json_str = sourcemap.to_json(indent=2)
```

## Semantic Argument Recovery & Python DSL Consumption

In Mindustry Logic, hardware links (`cell1`, `display1`, `message1`) and program variables occupy the same token space. However, in Python DSL:
- Hardware blocks must be referenced as string literals (e.g. `drawflush("display1")`, `read(val, "cell1", idx)`, `printflush("message1")`). Passing unquoted `display1` causes `NameError: name 'display1' is not defined` in Python and Pylance.
- Dynamic block references obtained via `b = getlink(0)` are variables, so `b` remains an unquoted identifier.

### Contrast Example
```python
# Direct named block reference: emitted as quoted string literal
read(val, "cell1", idx)
write(val, "cell1", 63)
printflush("message1")
drawflush("display1")

# Dynamic block reference obtained via getlink: emitted as unquoted variable
b = getlink(0)
hp = sensor(b, "@health")
```

## Round-Trip Verification Workflow

The compiler and decompiler form a closed, verified round-trip loop:

$$\text{MLog Source} \xrightarrow{\text{decompile()}} \text{Python DSL} \xrightarrow{\text{compile\_py()}} \text{Vanilla MLog}$$

1. Decompiles MLog into standard Python DSL syntax.
2. Validates that the generated Python passes standard `ast.parse` and `compile()`.
3. Recompiles the Python DSL using `compile_py()` to produce identical, valid MLog instructions.

## Supported Patterns & Known Limitations

### Supported Patterns
- Structured control flow: `while`, `break`, `continue`, `if`, `elif`, `else`
- Complex conditions: short-circuit `and`, `or`, `not`
- Expression trees: arithmetic (`+`, `-`, `*`, `/`, `//`, `%`), comparisons (`<`, `<=`, `==`, `!=`, `>`, `>=`)
- Temporary variable collapsing: single-use `__tmp0` chains collapsed into nested expressions
- Whole-program functions: `def` functions, parameter passing, return values, recursion
- Mindustry intrinsics: all 22 official intrinsics and enums
- Source mapping: statement-to-instruction bi-directional tracking

### Known Limitations (Zero Guessing)
- **Irreducible Control Flow**: Non-natural loops and indirect jumps (`set @counter ...`) fall back safely to `UnstructuredNode` comments and raw jumps rather than synthesizing speculative while loops.
- **Multi-Use Temporaries**: Temporaries read multiple times or modified across basic block boundaries are preserved as explicit assignments to guarantee side-effect correctness.
- **Flat Memory Model**: Mindustry Logic has no heap or object system; object-oriented constructs, classes, and Python collections (`list`, `dict`) are not reconstructed.

## CLI Usage

```bash
# Compile to stdout
python3 compiler.py input.py

# Compile to an output mlog file
python3 compiler.py input.py -o output.mlog

# Debug mode: displays IR instructions with source locations and resolved label table
python3 compiler.py input.py --debug
```

## Running Tests

```bash
cd mlog-py
python3 -m unittest discover -s tests -p "test_*.py"
```

Current test suite contains **281 comprehensive tests** (148 compiler/registry/import tests + 133 decompiler tests across Phases 1, 2, 3, 4, 4.5, and 5 with Semantic Argument Recovery), all passing.



