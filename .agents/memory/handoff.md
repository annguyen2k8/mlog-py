# Task handoff

- **Updated**: 2026-11-03
- **Agent**: Antigravity / Gemini 3.8 Flash
- **Status**: done
- **Goal**: Implement comprehensive P3 API Ergonomics, Argument Binding validations, and Expression Forms for mlog-py based on Mindustry v160.7.

## Done

- **P3 API Ergonomics & Argument Binding**:
  - **CRIT-01 (Reject invalid keywords on flat intrinsics and marker/sound/music)**:
    - Added `validate_no_keywords(call, intrinsic_name)` across all flat intrinsics in `compile_call`.
    - Enforced keyword rejection on `sound.play`, `sound.play_at`, `music.play`, `marker.make`, and all `marker.<method>` controls.
  - **CRIT-02 (Duplicate argument validation in `status.apply` & `status.clear`)**:
    - Added comprehensive duplicate checking between positional arguments and keyword arguments (`unit`, `effect`, `duration`).
  - **CRIT-03 (Positional argument shifting fix in `Array()`)**:
    - Fixed `_parse_array_call` to bind positional parameters (`block`, `size`, `dtype`) directly without list popping shifts.
    - Added duplicate argument detection between positional and keyword arguments for `block`, `size`, and `dtype`.
  - **MED-04 (Marker arity validation)**:
    - Enforced parameter arity validation for all `marker.<method>` control sub-actions matching `expected_params` in `ctrl_map`.
  - **Expression Forms (`ucontrol.within`)**:
    - Added support for 3-argument expression form `ucontrol.within(x, y, radius)` binding directly into destination register (`target_dest`) or temp variable.
    - Preserved 100% backward compatibility for 4-argument statement form `ucontrol.within(x, y, radius, out_result)`.
  - **Tuple Unpacking & Keyword Support (`ucontrol.get_block` & `ulocate`)**:
    - Added tuple unpacking support for `b_type, b_build, b_floor = ucontrol.get_block(x, y)` (and alias `getBlock`) with strict 3-target validation.
    - Added keyword argument support for `ulocate.building(group=..., enemy=...)` and `ulocate.ore(ore=...)` tuple unpacking with duplicate argument detection.
  - **Output Destination Keywords (`dest=` / `out=`)**:
    - Added keyword destination support (`dest=` / `out=`) to `sensor`, `read`, and `uradar`.
    - Enforced mutual exclusion between `dest` and `out`, duplicate argument detection against positional destinations, and unexpected keyword rejection.
  - **Metadata & IDE Typing Stubs**:
    - Added `@overload` statement forms for all `_FetchCallable` methods in `metadata.py`.
    - Disambiguated `_MessageCallable` `@overload` signatures between canonical `out_success` and alias `outSuccess`.
    - Added `@overload` expression and statement forms for `_UnitControlCallable.within` and `_UnitControlCallable.get_block`.
    - Added keyword destination overloads for `sensor`, `read`, `uradar`.
    - Updated runtime mock implementations in `metadata.py` (`_rt_sensor`, `_rt_read`, `_rt_uradar`, `get_block`, `within`) to return matching types without keyword errors.
    - Regenerated `mlog.pyi`, `mlog/__init__.pyi`, and `src/mlog.pyi` via `python -m mlog.metadata`.
  - **Documentation & Tests**:
    - Added comprehensive regression suite `tests/test_p3_ergonomics.py` (15 test methods).
    - Updated `docs/compiler.md` and `docs/mlog-command-coverage.md`.

## Next

- none

## Blocked

- none

## Verification

- `python run_tests.py --fast`: 807/807 passed.
- `python run_tests.py --jvm`: 607/607 passed.
- `python -m unittest tests.test_p3_ergonomics tests.test_unit_namespace tests.test_p2_ergonomics tests.test_p1_ergonomics`: 86/86 passed.
- `git diff --check`: 0 whitespace errors.
