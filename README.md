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
# Compile to stdout (auto-copies to clipboard by default)
mlog-py compile input.py

# Compile and save to file
mlog-py compile input.py -o output.mlog
```

**Common Compiler Flags**:
- `-o, --output <file>`: Save compiled bytecode to a file instead of stdout.
- `--no-clipboard`: Disable automatic copying of compiled MLog to clipboard (auto-copy is enabled by default; overridable via `MLOG_NO_CLIPBOARD=1`).
- `--comments-to-print`: Convert Python `# comments` into runtime Mindustry `print` instructions.
- `--no-functions`: Reject `def` function definitions and `return` statements (functions are allowed by default).
- `--debug`: Print IR instructions, source locations, and resolved label addresses.

### 2. Decompile MLog to Python DSL

Use the `mlog-py decompile` CLI:

```bash
# Decompile from file (prints to stdout, or use -o to save)
mlog-py decompile input.mlog -o output.py

# Stream / piped input from stdin
cat input.mlog | mlog-py decompile
mlog-py decompile - < input.mlog

# Interactive paste in terminal (finish with Ctrl+D or type 'EOF' on an empty line)
mlog-py decompile
```

**Common Decompiler Flags**:
- `-o, --output <file>`: Output Python file path (`.py`). Prints to stdout if omitted (or prompts interactively in paste mode).
- `--debug`: Include instruction provenance comments (`# mlog[<addr>]`).
- **Dataflow Simplification** *(built-in)*: Expression inlining, constant folding, and alias elimination (previously noted as `--simplify-expressions`) are performed automatically by default.

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

# Decompile to structured Python DSL
py_code = decompile(mlog_code)
print(py_code)

# Decompile with debug comments showing original bytecode addresses
debug_code = decompile(mlog_code, debug=True)
```

---

## Example: Reactor Safety Controller

A real-world example protecting a Thorium reactor from exploding due to overheating:

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

### Resulting MLog Bytecode (`examples/compiler/reactor_safety.mlog`)

```text
sensor heat reactor1 @heat
jump 4 lessThanEq heat 0.8
control enabled reactor1 0 0 0 0
jump 5 always 0 0
control enabled reactor1 1 0 0 0
wait 0.5
```

### Load into Mindustry

1. Copy the compiled `.mlog` content to your clipboard.
2. In Mindustry, build a logic processor (Micro, Logic, or Hyper Processor) and link it to the reactor (`reactor1`).
3. Click the processor, choose **Edit**, then select **Import from clipboard**.

---

## Example Catalog

Explore complete paired examples in [`examples/`](examples/README.md):

- **Arithmetic & Bitwise**: [`arithmetic.py`](examples/compiler/arithmetic.py), [`bitwise.py`](examples/compiler/bitwise.py), [`min_max.py`](examples/compiler/min_max.py)
- **Control Flow**: [`for_loop.py`](examples/compiler/for_loop.py), [`while_loop.py`](examples/compiler/while_loop.py), [`conditionals.py`](examples/compiler/conditionals.py), [`nested_loops.py`](examples/compiler/nested_loops.py)
- **Hardware Interaction**: [`reactor_safety.py`](examples/compiler/reactor_safety.py), [`display_graphics.py`](examples/compiler/display_graphics.py), [`print_message.py`](examples/compiler/print_message.py), [`memory_cell.py`](examples/compiler/memory_cell.py), [`array_memory.py`](examples/compiler/array_memory.py)
- **Unit Operations (Canonical Unit APIs)**: [`unit_operations.py`](examples/compiler/unit_operations.py)
- **Interactive Demos**: [`roundtrip_demo.py`](examples/compiler/roundtrip_demo.py), [`roundtrip_verify.py`](examples/decompiler/roundtrip_verify.py)

---

## Key Features

- **Structured Control Flow**: Full support for `for` loops with `range(...)`, `while`, `break`, `continue`, `if`, `elif`, and `else` with automatic label and instruction address resolution.
- **Arithmetic, Bitwise & Math**: Full expression support (`+`, `-`, `*`, `/`, `//`, `%`, bitwise `&`, `|`, `^`, `~`, `<<`, `>>`, built-in `min` and `max`) lowered with deterministic temporary variable management and strict 64-bit integer hardening.
- **Compile-Time Constant Folding**: Recursively folds pure constant expressions (`+`, `-`, `*`, `/`, `//`, `%`, `**`, `&`, `|`, `^`, `<<`, `>>`, comparisons, boolean logic, and string concatenation) at compile time while preserving Mindustry IEEE-754 runtime semantics, eliminating runtime temporaries, and statically resolving `Array` allocation sizes and subscript bounds checks.
- **Conditional Selection & Python Ternary**: Pure ternary expressions (`a if cond else b`) lower directly to the Mindustry `select dest op comp0 comp1 a b` opcode (zero jumps). Expressions with side effects, division, or memory access safely fall back to short-circuiting jump ladders. Full intrinsic `select()` supports 3, 4, 5, and 6-argument conventions.
- **Color Operations (`packcolor`, `unpackcolor`)**: Pack 4 RGBA channels in `[0, 1]` into a 64-bit double color (`packcolor(r, g, b, a)` with full expression nesting), and unpack double colors into 4 destination variables (`unpackcolor(r, g, b, a, color)` or the equivalent tuple form `r, g, b, a = unpackcolor(color)`).
- **Character Output, Print Formatting & f-Strings**: Low-level character/emoji output via `printchar(val)`, print buffer placeholder substitution via `format(val)`, and native Python f-strings (`f"..."`) automatically compiled into optimized template print and format sequences with strict evaluation order preservation.
- **Processor Execution Rate (`setrate`)**: Direct configuration of processor instructions per tick (IPT) via `setrate(ipt)`.
- **Memory Arrays & Static Allocation**: High-level `Array("cell1", size=10, dtype=...)` abstraction supporting `int`, `float`, and `bool` dtypes with compile-time contiguous layout tracking, capacity validation (64 for cells, 512 for banks), base offset calculations, and static index bounds checking.
- **Augmented Assignment**: In-place assignment operators (`+=`, `-=`, `*=`, `/=`, `//=`, `%=`, `**=`, `&=`, `|=`, `^=`, `<<=`, `>>=`) for both scalar variables and memory arrays (`arr[i] += val`), featuring atomic single-offset address evaluation without redundant reads.
- **Short-Circuit Boolean Logic**: Full support for `and`, `or`, and `not` with standard Python short-circuit evaluation.
- **Mindustry Compiler Intrinsics**: Direct access to Mindustry instructions (`sensor`, `control`, `ucontrol`, `draw`, `read`, `write`, `print`, `ubind`, `lookup`, `packcolor`, `unpackcolor`, `printchar`, `format`, `setrate`, `select`, etc.).
- **Display & Graphics API**: Complete support for `draw` instructions, including `draw.clear(r=0, g=0, b=0, a=0)` (DSL accepts 0 to 4 arguments for color compatibility; compiles to canonical Mindustry RGB `draw clear r g b 0 0 0`), shape drawing, affine transforms, and `drawflush`.
- **Advanced Decompiler Control Flow**: Deterministic reconstruction of top-tested while loops with inlined temporaries, bottom-tested loops (`do-while`), nested loops, loop-scoped `break`/`continue`, loop invariant protection, and canonical method aliases (`ucontrol.<method>`, `draw.<method>`).
- **Comments to Print Buffer**: Compile-time `--comments-to-print` flag converting Python `# comments` directly into Mindustry `print` instructions.
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

## Testing & Verification

The project maintains a comprehensive automated test suite verifying both compiler and decompiler across a 3-tier verification architecture:

- **Tier 1 (AST & Semantics)**: Python AST parsing, type constraints, and semantic argument validation.
- **Tier 2 (Bytecode & Round-Trip)**: Assembler/disassembler equivalence and invariance under the `MLog → Python → MLog` round-trip.
- **Tier 3 (Runtime JVM Mindustry v160.7)**: Direct execution on official Mindustry bytecode engine (`LExecutor` + `LAssembler`), verifying variable registers, print buffer states, hardware interactions, and edge cases.

```bash
# Run entire test suite (using persistent Mindustry JVM daemon ~50-80s)
python3 run_tests.py --all

# Run fast tier (Pure Python: AST, Compiler, Decompiler, IR ~13s)
python3 run_tests.py --fast

# Run JVM tier (Real Mindustry runtime ~70s)
python3 run_tests.py --jvm

# Standard unittest command is also fully supported
python3 -m unittest discover -s tests -p "test_*.py"
```

The JVM harness is auto-discovered from `Mindustry`/`Mindustry-source` and `Arc` checkouts (including local `build/libs` and the Gradle cache). Build it once with `python3 tools/build_harness.py --test`; explicit paths can be supplied through `MINDUSTRY_CORE_PATH`, `ARC_JARS_PATH`, `MINDUSTRY_HARNESS_BUILD`, and `MINDUSTRY_ASSETS_PATH`, or through a `.mindustry.json` config file. When a dependency is missing, JVM tests skip with the specific reason.

- **1,298 Automated Tests**: 100% passing baseline across compiler, decompiler, registry, CFG, structuring, dataflow, function recovery, bitwise operators, min/max, for loops, memory arrays (int, float, bool), Memory Bank Header Protocol (inter-processor communication layout), Callable Namespace Objects (`draw.<method>`, `ucontrol.<method>`, `ulocate.<method>`, `op.<method>`), augmented assignment, constant folding, system clipboard, built-in variables (Vars API), Mindustry v8 modulo semantics, color packing/unpacking, printchar, format & f-strings, setrate, select & ternary expressions, comprehensive `is`/`is not` semantics, all 25 World Processor privileged statements, CLI stdin/paste decompile, user-defined `enum.IntEnum` named constants, source mapping, and real JVM runtime verification.
- **Real-World Test Corpus**: 32 representative programs across handwritten scripts, compiler-generated programs, control flow patterns, and pathological edge cases.
- **Round-Trip Verification**: Guarantees that `MLog → Decompiler → Compiler` produces valid, functionally equivalent instructions.

### Mindustry v160.7 Tier 3 Runtime Scorecard (28/28 Opcodes — 100%)

| Group | Opcode List | Tier 3 Status | Runtime Semantics Verified in Real Engine |
| :--- | :--- | :---: | :--- |
| **A: Core & Control** (9) | `select`, `packcolor`, `unpackcolor`, `noop`, `set`, `op`, `jump`, `stop`, `end` | **VERIFIED** | Conditional branching, RGBA color pack/unpack, cycle halt (`stop`), cycle reset (`end`), division by zero propagation (`null`), all arithmetic and comparison operators |
| **B: Text & Buffer** (4) | `print`, `printchar`, `format`, `printflush` | **VERIFIED** | String concatenation, 400-char buffer limit, unicode/surrogate characters, template format placeholder substitution, message block flush and buffer reset |
| **C: Timing & Rate** (2) | `wait`, `setrate` | **VERIFIED** | Virtual Clock tick scheduler, IPT execution rate clamping ([1, 120] micro/logic, [1, 1500] hyper, [1, 8000] world), zero/negative duration yield |
| **D: Hardware & Data** (6) | `read`, `write`, `getlink`, `sensor`, `radar`, `lookup` | **VERIFIED** | Memory Cell (64) & Bank (512) read/write, string character code extraction, game content table lookup, turret radar unit scanning, building property sensing, null/dead target safety |
| **E: Graphics & Units** (7) | `draw`, `drawflush`, `control`, `ubind`, `ucontrol`, `uradar`, `ulocate` | **VERIFIED** | Display draw command buffer, building enable/disable toggle via control, round-robin unit cycling, coordinate distance check (`within`), unit radar target acquisition, core/ore locating |

---

## Limitations

- **Identity Semantics (`is` vs `strictEqual`)**: Python `is` maps to Mindustry `strictEqual` (`===`), which checks object vs double category and exact numeric equality without epsilon. `is not` is implemented across assignment (`op strictEqual` + `op equal dest 0`), ternary (`select` with inverted operands), `if`, and `while` via `strictEqual` to avoid Mindustry's engine quirk where `notEqual 0 null` evaluates to false. Note that because Mindustry booleans are numeric `1.0`/`0.0`, `true is 1` evaluates to true in Mindustry, whereas Python treats `True` and `1` as distinct types; Mindustry does not maintain Python heap object identities.
- **Irreducible Control Flow**: Non-natural loops and indirect jumps (`set @counter ...`) are preserved as fallback comments and raw jumps instead of synthetic loops.
- **Flat Memory Model**: Mindustry Logic has no heap or object system; object-oriented constructs, classes, and Python collections (`list`, `dict`) are not reconstructed.
- **Multi-Use Temporaries**: Temporaries read multiple times or modified across basic blocks are preserved as explicit assignments to ensure semantic correctness.
- **World Processor / Privileged Opcodes**: All 25 World Processor privileged statements (`query`, `getblock`, `setblock`, `spawn`, `bullet`, `status`, `explosion`, `setrule`, `getflag`, `setflag`, `setprop`, `fetch`, `sync`, `weathersense`, `weatherset`, `spawnwave`, `effect`, `message`, `cutscene`, `playsound`, `playmusic`, `makemarker`, `setmarker`, `localeprint`, `clientdata`) are fully supported by `mlog-py` for custom map scripting. At in-game runtime, Mindustry requires a World Processor (`#processor: world`); executing privileged opcodes on standard survival processors (Micro, Logic, Hyper) will be rejected by the engine as `InvalidStatement`.

---

## Technical Documentation

Detailed architecture specifications are available in [`docs/`](docs/):

- [Architecture Overview](docs/architecture.md): End-to-end compiler and decompiler architecture.
- [Compiler Specification](docs/compiler.md): AST lowering, IR instructions, and label resolution.
- [Decompiler Specification](docs/decompiler.md): CFG reconstruction, structuring, and function recovery.
- [Semantic Argument Recovery](docs/semantic-arguments.md): Hardware link detection and quoting rules.
- [Source Mapping](docs/source-mapping.md): Provenance tracking, debug comments, and JSON export.
- [Mindustry Logic Command Coverage](docs/mlog-command-coverage.md): Comprehensive mapping of 53 in-game UI commands and 28 standard opcodes in Mindustry v160.7.
- [ADR-001: Modulo Operator Semantics](docs/adr/0001-modulo-semantics.md): Architectural decision on lowering `%` to `emod`.
- [Upstream Mindustry Sync Guide](docs/mindustry-updates.md): Guide for updating and syncing mlog-py when new Mindustry versions release.

---

## License

This project is licensed under the [MIT License](LICENSE).
