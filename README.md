# mlog-py: Python-to-Mindustry Logic (mlog) Compiler & Decompiler

A robust, verified compiler and decompiler suite connecting a strongly-typed subset of Python with vanilla Mindustry Logic (mlog).

---

## What is mlog-py?

In the strategy game **Mindustry**, logic processors execute low-level assembly-like instructions (`.mlog`) to automate factories, defense units, and reactors. Writing logic by hand in the in-game editor is tedious and prone to errors.

`mlog-py` bridges Python and Mindustry Logic in both directions:

- **Compile (Python DSL → MLog)**: Write loops, conditionals, expressions, and hardware controls in Python; compile directly to vanilla `.mlog` instructions ready to paste into any processor.
- **Decompile (MLog → Python DSL)**: Reverse-engineer existing in-game logic into clean, readable Python code with structured `if`/`while` blocks, math expressions, and functions.
- **Round-Trip Verification**: Decompiled Python code recompiles cleanly into valid, functionally identical MLog bytecode.
- **Strong Typing & IDE Stubs**: Full autocomplete, signature help, and inline documentation in VS Code and Pylance via `mlog.pyi`.

---

## Quick Start

### Installation

From GitHub:

```bash
pip install git+https://github.com/annguyen2k8/mlog-py.git
```

From source:

```bash
git clone https://github.com/annguyen2k8/mlog-py.git
cd mlog-py
pip install .
```

### 1. Compile Python to MLog

Use the `mlog-py compile` CLI:

```bash
# Compile to stdout
mlog-py compile input.py

# Compile and output to a file
mlog-py compile input.py -o output.mlog

# Debug mode: view IR instructions and resolved label addresses
mlog-py compile input.py --debug
```

### 2. Decompile MLog to Python DSL

Use the `mlog-py decompile` CLI:

```bash
# Decompile to stdout
mlog-py decompile input.mlog

# Decompile and output to a file
mlog-py decompile input.mlog -o output.py

# Decompile with inline provenance comments (# mlog[<addr>])
mlog-py decompile input.mlog --debug
```

Or via Python API:

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

## Example: Reactor Safety Controller

A complete beginner-friendly example protecting a Thorium reactor from overheating:

### Python Source (`examples/compiler/reactor_safety.py`)

```python
from mlog import sensor, control, wait, SensorProperty, ControlProperty

heat = sensor("reactor1", SensorProperty.HEAT)

if heat > 0.8:
    control(ControlProperty.ENABLED, "reactor1", 0)
else:
    control(ControlProperty.ENABLED, "reactor1", 1)

wait(0.5)
```

### Compile to MLog

```bash
mlog-py compile examples/compiler/reactor_safety.py
```

### Compiled Output (`examples/compiler/reactor_safety.mlog`)

```text
sensor heat reactor1 @heat
jump 4 lessThanEq heat 0.8
control enabled reactor1 0 0 0 0
jump 5 always 0 0
control enabled reactor1 1 0 0 0
wait 0.5
```

### How to Use in Mindustry

1. Copy the compiled `.mlog` output above to your clipboard.
2. In Mindustry, build a Micro/Logic/Hyper Processor and connect it to your reactor (`reactor1`).
3. Click the processor, click **Edit**, and select **Import from clipboard**.

---

## Examples Catalog

Explore our comprehensive, paired examples in [`examples/`](examples/README.md):

- **Arithmetic & Bitwise**: [`arithmetic.py`](examples/compiler/arithmetic.py), [`bitwise.py`](examples/compiler/bitwise.py), [`min_max.py`](examples/compiler/min_max.py)
- **Control Flow**: [`for_loop.py`](examples/compiler/for_loop.py), [`while_loop.py`](examples/compiler/while_loop.py), [`conditionals.py`](examples/compiler/conditionals.py), [`nested_loops.py`](examples/compiler/nested_loops.py)
- **Game Hardware**: [`reactor_safety.py`](examples/compiler/reactor_safety.py), [`display_graphics.py`](examples/compiler/display_graphics.py), [`print_message.py`](examples/compiler/print_message.py), [`memory_cell.py`](examples/compiler/memory_cell.py), [`array_memory.py`](examples/compiler/array_memory.py)
- **Interactive Demos**: [`roundtrip_demo.py`](examples/compiler/roundtrip_demo.py), [`roundtrip_verify.py`](examples/decompiler/roundtrip_verify.py)

---

## Key Features

- **Structured Control Flow**: `for` loops with `range(...)`, `while`, `break`, `continue`, `if`, `elif`, and `else` with automatic label and instruction address resolution.
- **Arithmetic, Bitwise & Math**: Full expression support (`+`, `-`, `*`, `/`, `//`, `%`, bitwise `&`, `|`, `^`, `~`, `<<`, `>>`, built-in `min` and `max`) lowered with deterministic temporary variable management and strict 64-bit integer hardening.
- **Memory Arrays & Static Allocation**: High-level `Array("cell1", size=10)` abstraction with compile-time contiguous layout tracking, capacity validation (64 for cells, 512 for banks), base offset calculations, and static index bounds checking.
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
├── docs/                # Technical documentation and specifications
├── examples/            # Paired compiler and decompiler examples
└── tests/               # Automated test suite and corpus
```

---

## Testing

The project maintains a comprehensive automated test suite verifying both compiler and decompiler:

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

- **380 Automated Tests**: 100% passing baseline across compiler, registry, CFG, structuring, dataflow, function recovery, bitwise operators, min/max, for loops, and source mapping.
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
- [Upstream Mindustry Sync Guide](docs/mindustry-updates.md): Guide for updating and syncing mlog-py when new Mindustry versions release.

---

## License

This project is licensed under the [MIT License](LICENSE).
