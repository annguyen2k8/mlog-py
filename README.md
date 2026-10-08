# mlog-py: Python-to-Mindustry Logic (mlog) Transpiler / Compiler & Decompiler

A robust, verified compiler and decompiler suite connecting a strongly-typed subset of Python with vanilla Mindustry Logic (mlog).

---

## What is mlog-py?

`mlog-py` enables developers to write readable, strongly-typed Python code that compiles directly into optimized Mindustry Logic (`.mlog`) instructions, as well as decompile raw `.mlog` bytecode back into structured Python DSL.

- **Compile (Python DSL → MLog)**: Write loops, conditionals, expressions, and hardware interactions in Python; compile directly to vanilla mlog processor instructions.
- **Decompile (MLog → Python DSL)**: Reverse-engineer existing in-game logic into clean, readable Python code with structured `while`/`if` blocks and recovered expressions.
- **Round-Trip Verification**: Decompiled Python code re-compiles cleanly back into valid, functionally identical mlog bytecode.
- **Strong Typing & IDE Stubs**: Full auto-complete, signature help, and inline documentation in VS Code and Pylance via `mlog.pyi`.

---

## Quick Start

### Installation

Install from source or local wheel:

```bash
git clone https://github.com/annguyen2k8/mlog-py.git
cd mlog-py
pip install .
```

### 1. Compile Python to MLog

Use the installed `mlog-py` CLI (or `python3 compiler.py` directly from source):

```bash
# Compile to stdout
mlog-py input.py

# Compile and output to a file
mlog-py input.py -o output.mlog

# Debug mode: view IR instructions and resolved label addresses
mlog-py input.py --debug
```

### 2. Decompile MLog to Python DSL

Use the Python API:

```python
from src.decompiler import decompile

mlog_code = """
sensor heat reactor1 @heat
jump 4 lessThanEq heat 0.5
control enabled reactor1 0 0 0 0
end
control enabled reactor1 1 0 0 0
"""

# Decompile to clean Python DSL
py_code = decompile(mlog_code)
print(py_code)

# Decompile with inline provenance comments (# mlog[<addr>])
debug_code = decompile(mlog_code, debug=True)
```

---

## Example

### Python DSL (`reactor.py`)

```python
from mlog import sensor, control, wait, SensorProperty, ControlProperty

while True:
    heat = sensor("reactor1", SensorProperty.HEAT)
    if heat > 0.8:
        control(ControlProperty.ENABLED, "reactor1", 0)
    else:
        control(ControlProperty.ENABLED, "reactor1", 1)
    wait(0.5)
```

### Compiled MLog Output (`reactor.mlog`)

```text
jump 8 equal true 0
sensor heat reactor1 @heat
jump 5 lessThanEq heat 0.8
control enabled reactor1 0 0 0 0
jump 6 always 0 0
control enabled reactor1 1 0 0 0
wait 0.5
jump 0 always 0 0
```

---

## Key Features

- **Structured Control Flow**: `while`, `break`, `continue`, `if`, `elif`, and `else` with automatic label and instruction address resolution.
- **Arithmetic & Comparison**: Expressions (`+`, `-`, `*`, `/`, `//`, `%`, `==`, `!=`, `<`, `<=`, `>`, `>=`) lowered with deterministic temporary variable management.
- **Short-Circuit Boolean Logic**: Full support for `and`, `or`, and `not` with standard Python short-circuit evaluation.
- **Mindustry Compiler Intrinsics**: Direct access to Mindustry instructions (`sensor`, `control`, `ucontrol`, `draw`, `read`, `write`, `print`, `ubind`, `lookup`, etc.).
- **Verified Registry & Enums**: Enums (`SensorProperty`, `ControlProperty`, `UnitControl`, `DrawType`, `LogicOp`, `Condition`, `Units`, etc.) verified against vanilla Mindustry source.
- **Source Mapping**: Bi-directional provenance tracking between Python statements and mlog instruction addresses.
- **Semantic Argument Recovery**: Disambiguates named hardware links (quoted strings like `"reactor1"`) from program variables during decompilation.
- **Safe Zero Guessing Fallback**: Unstructured jumps, computed jump counters, and irreducible loops fall back safely to `UnstructuredNode` comments rather than speculative loops.
- **VS Code / Pylance Stubs**: Official `from mlog import ...` entry point backed by comprehensive typing stubs (`mlog.pyi`).

---

## Architecture

```text
Compilation:    Python DSL   ──►   AST Lowering   ──►   IR   ──►   Address Resolution   ──►   MLog Bytecode
Decompilation:  MLog Bytecode  ──►   CFG Rebuild   ──►   Structurer & Dataflow   ──►   Python DSL
```

Detailed architectural specifications:
- [Unified System Architecture](docs/architecture.md)
- [Compiler Pipeline & Lowering](docs/compiler.md)
- [Decompiler Pipeline & Structuring](docs/decompiler.md)

---

## Project Structure

```text
mlog-py/
├── compiler.py          # Standalone CLI entry point
├── mlog.py / mlog.pyi   # Runtime DSL module and IDE typing stubs
├── pyproject.toml       # Package metadata and build configuration
├── src/                 # Core compiler and decompiler source code
│   ├── compiler.py      # AST -> IR lowering
│   ├── emitter.py       # Two-pass address resolution
│   ├── metadata.py      # Single Source of Truth (SSOT)
│   ├── validator.py     # Static verification & processor limits
│   └── decompiler/      # Decompiler pipeline (CFG, structurer, dataflow)
├── docs/                # Technical specifications and documentation
├── examples/            # Paired compiler and decompiler examples
└── tests/               # Automated test suite and corpus
```

---

## Testing

The project maintains a comprehensive automated test suite verifying both compiler and decompiler:

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

- **281 Automated Tests**: 100% passing baseline across compiler, registry, CFG, structuring, dataflow, function recovery, and source mapping.
- **Real-World Test Corpus**: 32 representative programs across handwritten scripts, compiler-generated programs, control flow patterns, and pathological edge cases.
- **Round-Trip Verification**: Guarantees that MLog → Decompiler → Compiler produces valid, identical instructions.

---

## Limitations

- **Irreducible Control Flow**: Non-natural loops and indirect jumps (`set @counter ...`) are preserved as fallback comments and raw jumps instead of synthetic loops.
- **Flat Memory Model**: Mindustry Logic has no heap or object system; object-oriented constructs, classes, and Python collections (`list`, `dict`) are not reconstructed.
- **Multi-Use Temporaries**: Temporaries read multiple times or modified across basic blocks are preserved as explicit assignments to ensure semantic correctness.

---

## Documentation

Detailed architecture specifications are available in [`docs/`](docs/):

- [Architecture Overview](docs/architecture.md): End-to-end compiler and decompiler architecture.
- [Compiler Specification](docs/compiler.md): AST lowering, IR instructions, and label resolution.
- [Decompiler Specification](docs/decompiler.md): CFG reconstruction, structuring, and function recovery.
- [Semantic Argument Recovery](docs/semantic-arguments.md): Hardware link detection and quoting rules.
- [Source Mapping](docs/source-mapping.md): Provenance tracking, debug comments, and JSON export.

---

## License

This project is licensed under the [MIT License](LICENSE).
