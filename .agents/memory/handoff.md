# Task handoff

- **Updated**: 2026-11-03
- **Agent**: Antigravity / Gemini 3.8 Flash
- **Status**: done
- **Goal**: Implement P2 API Ergonomics: lookup namespace methods (item, block, unit, liquid), query namespace methods (circle, rect with automatic dummy height operand filling), and message namespace methods (announce, toast, notify) matching Mindustry v160.7.

## Done

- **P2 API Ergonomics Implementation**:
  - **A. `lookup` namespace**:
    - Added `lookup.item(index)`, `lookup.block(index)`, `lookup.unit(index)`, `lookup.liquid(index)` methods to `_LookupCallable`.
    - Supports both expression forms (`dest = lookup.item(idx)`) and statement forms (`lookup.item(idx, dest)`).
    - Preserves 100% backward compatibility for legacy positional `lookup(type, ...)` calls.
    - Added parser validation for lookup methods with close-match typo suggestions.
    - Pushed in commit `a4e91a3`.
  - **B. `query` namespace**:
    - Added `query.circle(type, team, x, y, radius)` and `query.rect(type, team, x, y, width, height)` to `_QueryCallable`.
    - Automatically injects trailing dummy operand `"0"` for `query.circle` matching upstream Mindustry v160.7 `QueryStatement.java` / `QueryI`.
    - Supports `QueryType` enum and strings (`"unit"`, `"building"`), `Teams` enum, string tokens (`"@sharded"`), variables, and `None`/`null`.
    - Preserves 100% backward compatibility for legacy 7-operand `query(shape, type, team, x, y, w, h)`.
    - Pushed in commit `b18cff3`.
  - **C. `message` namespace**:
    - Added `message.announce([duration=3], [out_success="@wait"])`, `message.toast([duration=3], [out_success="@wait"])`, and `message.notify([duration=3], [out_success="@wait"])` to `_MessageCallable`.
    - Supports both statement forms (defaulting to `@wait` for non-blocking message queueing) and expression forms (`success = message.announce(...)`).
    - Explicitly omits `message.mission()` per upstream semantics (`LStatements.FlushMessageStatement` sets scenario rules rather than a HUD message popup).
    - Preserves 100% backward compatibility for legacy `message(type, [duration], [out_success])`.
- **SSOT Metadata & Typing Stubs**:
  - Updated `src/metadata.py`, `mlog/metadata.py`, and `mlog/__init__.py`.
  - Exported `_LookupCallable`, `_QueryCallable`, and `_MessageCallable` in `MLOG_EXPORTS`.
  - Regenerated typing stubs (`mlog.pyi`, `mlog/__init__.pyi`, `src/mlog.pyi`) via `python -m mlog.metadata`.
- **Documentation**:
  - Updated `docs/compiler.md` with usage examples and descriptions for `lookup.<method>`, `query.<method>`, and `message.<method>`.
  - Updated `docs/mlog-command-coverage.md` detailing modern callable namespaces alongside legacy forms.
- **Testing & Verification**:
  - Created `tests/test_p2_ergonomics.py` with 16 comprehensive test methods covering:
    - `lookup` methods (item, block, unit, liquid, expression/statement forms, nested calls, invalid calls, runtime).
    - `query` methods (circle with dummy height 0, rect, team formatting, expression fallback, invalid calls, runtime).
    - `message` methods (announce, toast, notify, statement/expression forms, keyword args, mission rejection, invalid calls, runtime).
  - Validated all generated instructions against real Mindustry v160.7 JVM engine (`validate_with_jvm`).

## Next

- none

## Blocked

- none

## Verification

- `python -m unittest tests.test_p2_ergonomics tests.test_p1_ergonomics tests.test_imports_and_stub tests.test_compiler_examples tests.test_decompiler_examples tests.test_agent_memory`: 76/76 passed.
- `python run_tests.py --jvm`: 607/607 passed.
- `python run_tests.py --fast`: 791/791 passed.
- `git diff --check`: 0 whitespace errors.
