# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
