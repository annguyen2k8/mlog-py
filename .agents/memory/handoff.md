# Task handoff

- **Updated**: 2026-11-03
- **Agent**: Antigravity / Gemini 3.8 Flash
- **Status**: done
- **Goal**: Implement comprehensive P4 Remediation (Semantic & Runtime Correctness) for mlog-py based on p4_discovery_audit.md and Mindustry v160.7.

## Done

- **P4 Remediation (Semantic & Runtime Correctness)**:
  - **CRIT-01 (Identifier collision - remove counter/@counter auto-aliasing)**:
    - Removed automatic mapping of `counter` and `_counter` to `@counter` in `format_name` in both `mlog/compiler.py` and `src/compiler.py`.
    - User variables named `counter` or `_counter` now lower to regular Mindustry variables (`set counter ...`), allowing normal Python usage.
    - Preserved `Vars.counter` as the explicit, canonical way to access and modify `@counter`.
    - Aligned existing test suites (`test_phase1a.py`, `test_phase1f.py`, `test_aug_assign.py`, `test_builtins_and_properties.py`, `test_phase2_semantics.py`) to test explicit `Vars.counter` vs normal user variable `counter`.
  - **CRIT-02 (Boolean short-circuit destination corruption)**:
    - Updated `compile_expr` for `ast.BoolOp` (`and`, `or`) to evaluate branches into a dedicated temporary accumulator register (`accum = self.new_temp(loc)`).
    - Prevents premature mutation of `target_dest` when subsequent branches in the boolean chain read or evaluate against `target_dest`.
    - Emitted `set target_dest accum` only after the `boolop_end` label.
    - Updated `examples/compiler/arithmetic.mlog` golden bytecode to match safe boolean lowering.
  - **HIGH-01 (Team normalization & dynamic spawn)**:
    - Added helper methods `format_team_operand` and `format_unit_type_operand` in `Compiler`.
    - Enabled dynamic variables and runtime expressions for unit `type` and `team` in `spawn`, matching Mindustry v160.7 `SpawnUnitI` (which reads operands dynamically as `LVar type` and `LVar team`).
    - Fixed team identifier collision in `fetch` and `bullet` where user variables matching team names (e.g. `sharded`, `crux`) were incorrectly normalized to team constants.
  - **MED-01 (`draw.clear` signature alignment)**:
    - Aligned `draw.clear` with Mindustry v160.7 `LStatements.java:163` (`draw clear r g b 0 0 0`), strictly accepting at most 3 operands (`r, g, b`) or keywords `r=, g=, b=`.
    - Enforced `CompileError` on 4th positional argument or keyword `a=`.
    - Updated `mlog/metadata.py`, `src/metadata.py`, and regenerated typing stubs (`mlog.pyi`, `mlog/__init__.pyi`, `src/mlog.pyi`).
    - Updated `docs/compiler.md` and `README.md`.
  - **INFO-01 (Division by zero documentation & runtime verification)**:
    - Documented runtime differences between Python `ZeroDivisionError` and Mindustry Logic floating-point evaluation in `docs/compiler.md`.
    - Verified in Mindustry JVM engine that division and modulo by zero (`/`, `//`, `%`, `op div/idiv/emod`) evaluate safely to `null` via `Double.isNaN` / `Double.isInfinite` checks in `LExecutor.java:LVar.setnum` without halting processor execution.
  - **Regression Test Suite**:
    - Created `tests/test_p4_remediation.py` containing 13 tests covering CRIT-01, CRIT-02, HIGH-01, MED-01, and INFO-01 with JVM harness execution and bytecode validation.

## Next

- none

## Blocked

- none

## Verification

- `python run_tests.py --fast`: 820/820 passed (pure-Python tier).
- `python run_tests.py --jvm`: 607/607 passed (Mindustry v160.7 JVM engine tier).
- `python run_tests.py --all`: 1427/1427 passed (full test suite).
- `git diff --check`: 0 whitespace errors.
- `git diff --no-index src/compiler.py mlog/compiler.py`: 0 diff.
- `git diff --no-index src/metadata.py mlog/metadata.py`: 0 diff.
