# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Unified Array Architecture (`mlog.beta`)**:
  - Introduced `LocalArray` backed directly by processor registers, eliminating memory cell/bank requirements on map for vector math, small lookup tables, and in-register buffers.
  - Introduced `BlockArray` backed by physical memory blocks (`cell` and `bank`) with native $O(1)$ read/write instructions and `.fill()` memory initialization.
  - Provided polymorphic `Array` factory in `mlog.beta` that automatically dispatches to `LocalArray` or `BlockArray` based on presence of a block argument.
  - Generic typing support via `Array[T]`, `LocalArray[T]`, and `BlockArray[T]`.
  - Compile-time constant folding for array properties (`len(arr)`, `arr.size`, `arr.capacity`).
  - Added paired compiler examples: `examples/compiler/beta_local_array.py` and `examples/compiler/beta_block_array.py`.
- **Architectural & Audit Documentation**:
  - Consolidated P9–P15 array subsystem specification in `docs/p9_p15_acceptance_report.md`.
  - Codified the Hybrid Array Architecture in `docs/adr/0005-p9-p12-hybrid-array-architecture.md`.

## [0.8.1] - 2026-11-01

### Added
- **PyPI Trusted Publishing (OIDC) Workflow**:
  - Automated GitHub Actions workflow (`.github/workflows/publish.yml`) to build, verify, and publish releases to PyPI without API tokens or passwords using short-lived OIDC tokens.
  - Multi-tier pre-publish validation: metadata verification with `twine check --strict`, wheel layout checks with `check-wheel-contents`, and isolated virtualenv smoke tests verifying CLI entrypoints and import cleanliness outside repository workspace.
  - Least-privilege permissions: top-level `permissions: contents: read` and job-scoped `permissions: id-token: write`.
  - Workflow validated using `actionlint` with active `shellcheck` and `pyflakes` rules.
- **Repository Ignore Rules Audit & Hardening**:
  - Comprehensive `.gitignore` audit adding test and type check caches (`.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.hypothesis/`).
  - Added test coverage artifacts (`.coverage`, `.coverage.*`, `htmlcov/`, `coverage.xml`, `*.cover`).
  - Added packaging caches (`.eggs/`, `*.whl`) and virtualenv backups (`env.bak/`, `venv.bak/`).
  - Added Mindustry harness local developer configurations (`.mindustry.json`) and alternate harness build directories (`.build/`).
  - Added IDE whitelisting allowing shared configurations (`.vscode/settings.json`, `.vscode/tasks.json`, `.vscode/launch.json`, `.vscode/extensions.json`, `.idea/runConfigurations/`, `.idea/codeStyles/`) while ignoring personal workspace states.
  - Added OS and editor artifacts (`*~`, `Thumbs.db`, `Desktop.ini`, `ehthumbs.db`, `._*`).
- **Documentation**:
  - Added official PyPI installation instructions (`pip install mlog-py`) in `README.md`.
  - Documented PyPI Trusted Publisher configuration steps in `README.md`.

## [0.8.0] - 2026-11-01

### Added
- **CLI Compile Stdin Streaming & Shell Piping**:
  - Full support for reading Python source code from standard input (`mlog compile -` or omitted input argument), bringing full symmetry with `mlog decompile`.
  - Automatic piped fallback when piping input without arguments (e.g. `cat script.py | mlog`).
  - Interactive TTY prompts with instructions, `Ctrl+D` (Unix) / `Ctrl+Z (Enter)` (Windows) guides, and `EOF` / `__EOF__` sentinel support on empty lines.
  - Interactive output destination prompt when running in an interactive terminal.
  - Dynamically configured CLI parser `prog` based on invoked script name (`mlog` or `mlog-py`).
- **Compiler Error Diagnostics & Typo Suggestions**:
  - Integrated `difflib.get_close_matches` across `ASTValidator` to suggest the closest matching identifier (`Did you mean '...'?`) on typos across `draw`, `control`, `ucontrol`, `ulocate`, `op`, `cutscene`, `sound`, `music`, `marker`, `Vars`, user-defined `IntEnum` members, and symbols imported from `mlog`.
  - Added user-defined function typo suggestions when `allow_functions=True`.
  - Added compiler-stage attribute typo suggestions for enum registry members (e.g. `Items.coall` -> `Items.COAL`).
  - Added actionable diagnostic hints for unsupported Python heap collections (`list`, `dict`, `set`), explaining Mindustry's flat register/hardware memory model and directing developers to `Array('cell1', size, dtype=...)`.
  - Preserved exact `CompileError` exception hierarchy, location metadata (`filename`, `line`, `col`), and error message prefixes for 100% backward compatibility.
- **`decompile()` Overload Typing & Pyright Verification**:
  - Added `@overload` signatures for `decompile()`: `return_source_map: Literal[False]` resolves strictly to `str`, `return_source_map: Literal[True]` resolves strictly to `Tuple[str, Any]`, and boolean fallback resolves to `Union[str, Tuple[str, Any]]`.
  - PEP 484 explicit re-export `from enum import Enum, IntEnum as IntEnum` in typing stubs.
  - Automated clean-wheel typing verification test (`test_pyright_clean_wheel_typing_verification`) validating the built wheel in an isolated virtual environment against Pyright 1.1.414 with 0 errors and 0 warnings.
- **Canonical Top-Level `mlog/` Package Architecture**:
  - Migrated primary distribution package to top-level `mlog/` namespace, eliminating internal `src` directory from wheel distribution and preventing site-packages pollution.
  - Packaged PEP 561 `py.typed` marker and canonical `mlog/__init__.pyi` typing stubs.
  - Maintained zero-breaking-change backward compatibility for existing `from src.mlog import ...` imports via transparent shim with exact object identity.
  - Dual CLI entrypoints `mlog` and `mlog-py` registered in `pyproject.toml`.
  - Full execution support for `python -m mlog` and `python -m mlog.metadata`.

### Changed
- CLI graceful cancellation: `KeyboardInterrupt` (Ctrl+C) during compilation, decompilation, and JVM engine validation cleanly exits with standard UNIX exit code `130` without raw stack traces.
- Symmetrical documentation in `examples/README.md` showcasing modern `mlog compile` and `mlog decompile` commands alongside piped shell usage.

## [0.7.0] - 2026-10-31

### Added
- **v160.7 `control` Namespace**:
  - Full support for canonical `control` namespace in Python DSL (`control.enabled()`, `control.shoot()`, `control.shootp()`, `control.config()`, `control.color()`) with automatic dummy operand padding matching Mindustry v160.7 engine signatures.
  - Decompiler round-trip recovery for `control` instructions into idiomatic `control.<prop>(...)` methods.
- **Cross-Platform Engine Harness Auto-Discovery & Resilient Windows Daemon**:
  - Auto-discovers compiled Mindustry core classes and Arc library jars across sibling folders, Gradle cache, and explicit configs (`.mindustry.json`).
  - Hardened Windows daemon lifecycle with strict discovery, process cleanup, and daemon reuse.
  - Replaced Termux-specific fixtures with cross-platform tests (preserving byte-identical BOM handling).
- **v160.7 Engine Semantics & Sensor Alignment**:
  - `status clear` boolean flag now strictly emits literal `"true"`/`"false"` matching `Boolean.valueOf()` parsing in the JVM engine, restoring exact decompiler round-trips.
  - `marker.texture` emits `p1=printFlush` and `p2=name` per upstream v160.7 `LMarkerControl.texture` signature.
  - Exposed privileged `@cameraX`, `@cameraY`, `@cameraWidth`, `@cameraHeight` in `SensorProperty` and registry extractor.
- **Complete Mindustry v160.7 Opcode Coverage Audit**:
  - Fully audited all 53 opcodes (28 standard, 25 world processor) in `docs/mlog-command-coverage.md`.
  - Updated World Processor table with 7-column matrix documenting exact v160.7 MLog syntax, compiler intrinsics, source references, and regression tests.
  - Documented deliberate architectural boundaries (World Processor `#processor: world` privilege requirement, 1:1 intrinsic mapping) and API gaps (`@queries` internal buffer protocol).
- **Shared Agent Memory & Handoff Protocol**:
  - Added filesystem Markdown shared agent memory (`AGENTS.md`, `.agents/memory/context.md`, `.agents/memory/handoff.md`, ADR index, and structural tests) facilitating pair-programming handover between Antigravity and OpenCode.
- **Documentation & Walkthrough Synchronization**:
  - Synchronized `README.md` decompiler flags and Thorium reactor safety controller walkthrough with exact CLI, API, and example files.
  - Added explicit note clarifying that decompiler output recovers semantic equivalence with minimal imports rather than character-for-character original formatting.

## [0.6.0] - 2026-10-19

### Added
- **`enum.IntEnum` Named Constants Support**:
  - Full support for `from enum import IntEnum` and `class State(IntEnum): ...` lowering member references directly to compile-time integer constants with zero runtime objects or heap allocations in Mlog.
  - Safe static evaluation for integer expressions, bitwise flags (`1 << 0`, `FLAG_A | FLAG_B`), arithmetic, unary inversion (`~`), and references to earlier members of the same enum.
  - Independent `NamedConstantRegistry` symbol table architecture keeping constant resolution decoupled from specific AST nodes.
  - Strict compile-time validation rejecting unsupported base classes (`Flag`, `StrEnum`, `Enum`), multiple inheritance, methods, decorators, member reassignments, dynamic expressions, or standalone enum values.
- **Ultra-Fast Persistent Mindustry JVM Daemon & Test Tiering**:
  - Re-architected `tools/harness/MindustryHarness.java` with a persistent `--daemon` protocol and isolated world reset (`resetWorld()`).
  - Implemented unbuffered raw binary IPC in `src/mindustry_validator.py` with automatic timeout handling, crash recovery, and seamless one-shot fallback.
  - Accelerated full test suite execution from ~29.4 minutes to ~50-80 seconds (over 20x speedup) on Termux/Android ARM64.
  - Added tiered test runner `run_tests.py` supporting `--fast` (pure Python in ~13s), `--jvm` (Mindustry runtime in ~70s), and `--all` (full suite in ~80s).
- **Tier 4 World Processor & Map Scripting (25 Privileged Statements)**:
  - Complete support across Validator, Registry, AST Parser, Compiler, Decompiler, and IDE Stubs for all 25 privileged statements:
    - **World State Manipulation**: `query`, `getblock`, `setblock`.
    - **Unit & Combat Spawning**: `spawn`, `bullet`, `status`, `explosion`.
    - **Rule Management & Entity Queries**: `setrule`, `getflag`, `setflag`, `setprop`, `fetch`, `sync`.
    - **Weather & World Effects**: `weathersense`, `weatherset`, `spawnwave`, `effect`.
    - **UI Messaging & Cutscenes**: `message`, `cutscene`, `setrate` (scaling to 1000 IPT on World Processor).
    - **Audio, Objective Markers & Network Data**: `playsound`, `playmusic`, `makemarker`, `setmarker`, `localeprint`, `clientdata`.
- **100% Opcode Coverage Verification (53/53 Statements)**: Direct parity with Mindustry v160.7 `LogicIO.allStatements` covering all 28 Standard opcodes and 25 World/Privileged statements with roundtrip decompilation and JVM execution.
- **JVM-Backed World Processor Test Harness**: Extended `MindustryHarness.java` with mock audio/assets, objective markers state export, dynamic rules, and world processor building configuration.
- **`unpackcolor` Tuple Unpacking**: `r, g, b, a = unpackcolor(color)` now lowers to the same single Mindustry `unpackcolor r g b a value` instruction as the existing statement form. Exactly 4 targets are required; target count, duplicate target names, keyword arguments, and non-name targets are rejected at parse time. `ColorChannels` (an `r`/`g`/`b`/`a` `NamedTuple`) is exported so the expression form also runs under plain CPython.
- **CLI `--no-functions` Flag**: Opt-out for function definitions and `return` statements.
- **`examples/compiler/color_channels.py`**: Paired `.py` / `.mlog` example for `packcolor` + `unpackcolor` unpacking.
- **Decompiler temporary inlining into raw instructions**: A single-use compiler temporary feeding a plain `OPERAND` position of a raw instruction is now folded into the Python expression, so `print __tmp2` recovers as `print(r + g + b + a)`. Gated by the new `semantics.is_safe_inline_expression` predicate shared with the renderer, so comparisons, booleans, calls, and other non-arithmetic values are never inlined and never re-quoted into strings. Control-flow opcodes (`jump`/`stop`/`end`) and non-`OPERAND` roles (destinations, hardware links, enum selectors) are never rewritten.
- **`src/decompiler/naming.py`**: Renames preserved compiler temporaries (`__tmpN`) to valid Mindustry Logic DSL identifiers (`tmp_val_N`) with a deterministic, collision-free, 1:1 mapping applied to every read, write, and instruction operand. Temporaries that exist only in an elidable `ulocate` output slot keep their original name so `instruction_to_python` can still drop them.
- **CLI Stdin & Copy-Paste Decompilation**:
  - `mlog-py decompile` without positional arguments or with `-` now reads MLog directly from `sys.stdin`.
  - Full support for piped streams (`cat code.mlog | mlog-py decompile`) and interactive terminal paste with guidance printed to `sys.stderr` and sentinel termination (`EOF` or `__EOF__`).
  - Standard exit codes: `0` on success, `1` on empty input or syntax error, `130` on `KeyboardInterrupt` (Ctrl+C).
  - Safe `-o` flag support when reading from stdin, and graceful `BrokenPipeError` handling.
- **Advanced Loop Decompiler & Semantic Control Flow**:
  - Deterministic reconstruction of top-tested `while` loops, inlining safe compiler-generated condition temporaries without moving loop-modified variables into conditions.
  - Safe handling of loop header I/O side-effects (`read`, `sensor`, `getlink`): reconstructed as `while True:` where pre-instructions execute before `if exit_cond: break`, completely eliminating `undefined variable` errors.
  - Robust bottom-tested loops (`do-while` / conditional latch) structured cleanly as `while True: ... if not (latch_cond): break`.
  - Scoped `break` and `continue` isolation across nested loops and conditional branches.
  - Clean unquoted fallback in `UnstructuredNode` emitting semantic `jump(...)` calls (`jump(1, "equal", y, 2)`) preserving exact round-trip bytecode without quoting identifiers.
- **Enhanced `draw.clear()` API**:
  - `draw.clear(r=0, g=0, b=0, a=0)` in both compiler and decompiler supporting 0 to 4 arguments (DSL accepts RGBA for color compatibility, compiling to standard Mindustry RGB opcode `draw clear r g b 0 0 0`) with complete typing stubs (`mlog.pyi`).
- **Comments to Print Compilation (`--comments-to-print`)**:
  - Added CLI and compiler flag `--comments-to-print` allowing Python `# comments` to be lowered into runtime Mindustry `print "comment"` instructions.
- **Dataflow Expression & Alias Simplification (`--simplify-expressions`)**:
  - Phase 3 dataflow pass safely inlining single-use temporaries into arithmetic/logic expressions, constant folding pure expressions, and eliminating redundant aliases (`b = g`).
- **Decompiler Canonical Method Aliases**:
  - Recovers idiomatic Pythonic method calls for `ucontrol` (`ucontrol.move()`, `ucontrol.approach()`, etc.) and `draw` (`draw.clear()`, `draw.color()`, etc.) instead of generic opcode calls.
- **Decompiler 53/53 Opcode Parity & Regression Suite**:
  - Comprehensive coverage test suite (`tests/test_decompiler_full_coverage.py`) verifying round-trip semantic equivalence across all 53 Mindustry v160.7 opcodes, structured control flow recovery, and parser error boundaries.
  - Automated CLI test suite (`tests/test_cli_decompile_stdin.py`) covering all stdin, piped, interactive, sentinel, and error scenarios.
  - Dedicated loop regression suite (`tests/test_decompiler_loops.py`) with 22 edge-case and roundtrip tests.
  - Automated test suite expanded to **1,249 automated tests** with 100% pass rate.

### Fixed
- **CLI Could Not Compile Function Definitions**: `mlog-py compile script.py` always ran with `allow_functions=False`, so every `def` statement failed with `unsupported Python feature: function definition` even though the compiler fully supports user-defined functions. The CLI now enables function support by default (matching the documented Python subset and `examples/compiler/functions.py`) and exposes `--no-functions` to restore the strict subset. The Python API default (`compile_py(..., allow_functions=False)`) is unchanged.
- **FunctionAnalyzer Loop Latch Truncation**: Loop latch detection in `FunctionAnalyzer` previously scanned forwards, mistaking early `continue` jumps targeting the loop header for the outer loop latch. This cut the loop body short and dropped all subsequent statements. Reversed latch search resolves the true bottom-most loop latch and preserves all instructions.
- **Decompiler Emitted Reserved Compiler Temporaries**: Preserved `__tmpN` assignments produced Python the compiler refused to recompile (`variable name '__tmp0' is reserved for compiler temporaries`), so `examples/compiler/array_memory.mlog`, `examples/compiler/aug_assign.mlog`, and `examples/compiler/color_channels.mlog` could not complete an MLog → Python → MLog round-trip. All compiler examples now decompile to valid, recompilable Python, and `color_channels.mlog` round-trips byte-for-byte.
- **Inlined Operands Silently Quoted Into Strings**: Without the shared predicate, folding a comparison or a boolean-bearing expression into an operand rendered it as a string literal (e.g. `write("i > 5", "cell1", 0)`), changing program semantics.
- **`src/parser.py` Missing `Union` Import**: `_validate_unpacking_assign` annotated its target with `Union`, which was never imported. This was masked by PEP 649 lazy annotation evaluation on Python 3.14 and would raise `NameError` at import time on Python 3.9-3.13.

### Known Issues
- `examples/compiler/special_constants.mlog` does not round-trip byte-for-byte: `set copper_name @copper` recovers as `copper_name = '@copper'` and recompiles to `set copper_name "@copper"`, a quoted string. At runtime the variable then holds `copper` instead of `@copper`. This is a pre-existing `@`-token quoting limitation, unrelated to compiler temporaries.

## [0.5.0] - 2026-10-12

### Added
- **Mindustry v8 Instructions & Intrinsics**:
  - `packcolor(r, g, b, a)` and `unpackcolor(r, g, b, a, color)` for 64-bit packed double color manipulation with multi-destination variable recovery in decompiler.
  - `printchar(val)` for single character and custom Mindustry emoji output into print buffer.
  - `format(val)` for replacing `{0}`..`{9}` placeholders in the print buffer.
  - `setrate(ipt)` for setting processor execution rate (up to 1000 instructions per tick).
  - Native `select(dest, op, comp0, comp1, a, b)` intrinsic matching Mindustry v8 selection instruction.
- **Python f-Strings (`ast.JoinedStr`)**:
  - Direct lowering of Python f-strings into optimized `print` text buffers and `format` sequences.
  - Strict left-to-right evaluation order preservation for expressions with side-effects.
  - Automatic brace escaping (`{{` -> `{`, `}}` -> `}`) and compile-time validation rejecting unsupported format specifiers or f-strings exceeding 10 placeholders.
- **Python Ternary Expressions (`a if cond else b`)**:
  - Lowering pure ternary expressions directly to branchless `select` instructions without jumps.
  - Conservative purity analysis automatically falling back to jump-based ladders for impure expressions (side-effects, function calls, memory writes, potential division by zero).
- **Sound `is` and `is not` Semantics**:
  - Lowering `is` to Mindustry `strictEqual` without float epsilon tolerance.
  - Sound lowering of `is not` across all expression and control-flow contexts (`if`, `while`, compound `and`/`or`, `not`, assignment) via `strictEqual` with safe inversion jumps, completely avoiding Mindustry engine's `notEqual 0 null` bug.
  - JVM runtime verification tests against Mindustry v160.7 engine.
- **Augmented Assignment Operators (`+=`, `-=`, etc.)**:
  - Full support for 12 augmented assignment operators (`+=`, `-=`, `*=`, `/=`, `//=`, `%=`, `**=`, `&=`, `|=`, `^=`, `<<=`, `>>=`) on scalars and memory array elements.
  - Strict single-evaluation for subscripted array elements (`arr[expr] += val`) reusing offset registers.
  - Compile-time dtype validation across `int`, `float`, and `bool` arrays.
- **Compile-Time Constant Folding**:
  - Static folding for pure arithmetic, bitwise, unary, and comparison expressions.
  - Guards against non-finite floats (`inf`, `-inf`, `nan`) and safe 64-bit integer boundaries.
- **Canonical `Vars` API**:
  - Type-safe object-oriented access to Mindustry built-in variables (`Vars.this`, `Vars.time`, `Vars.counter`, `@thisx`, `@thisy`, etc.) with decompiler round-trip recovery.
- **CLI & Packaging Enhancements**:
  - System clipboard integration (`--clipboard`, `-c`) across Linux, macOS, Windows, and Termux.
  - Dynamic `__version__` resolution and CLI `--version` / `-V` flags.
  - Synchronized typing stubs (`mlog.pyi`, `src/mlog.pyi`) and `MANIFEST.in`.
  - Automated test suite expanded from 446 tests (at `v0.4.0`) to **729 automated tests**.

### Fixed
- **Modulo Operator Semantics (`op emod`)**:
  - Mapped Python `%` and `%=` to Mindustry v8 `op emod` instruction to guarantee Python's floored modulo semantics for negative dividends.
- **Nested `packcolor` Expressions**:
  - Fixed temporary variable allocation when `packcolor` is nested inside expressions or function arguments.
- **String Literal CRLF Normalization**:
  - Standardized newline escaping in compiler and validator, normalizing CRLF/CR to `\n` to prevent Mindustry's in-game `Missing closing quote "` syntax error.
- **Unterminated String Validation**:
  - Added strict syntax checking in validator for unterminated string literals.
- **Dual-Purpose Sensor Properties**:
  - Supported automatic resolution for dual-purpose sensor properties and token normalization.

## [0.4.0] - 2026-10-10

### Added
- **Memory Cell/Bank Array Abstraction**:
  - High-level `Array("cell1", size=10, dtype=...)` abstraction supporting `int`, `float`, and `bool` dtypes.
  - Compile-time contiguous layout tracking, capacity validation (64 for cells, 512 for banks), base offset calculations, and static index bounds checking.
- Automated test suite expanded to 446 tests.
