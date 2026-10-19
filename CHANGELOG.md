# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
