# Task handoff

- **Updated**: 2026-11-07
- **Agent**: Antigravity / Gemini 3.8 Flash
- **Status**: done
- **Goal**: Complete P8 remediation (P8-REM-01): eliminate redundant conditional exit guards for compile-time constant true loops in `compiler.py:compile_while`, restore byte-identity and exact PC traces for `flare_miner`, `turret_radar`, and `scale_100/500/1000`, add regression tests, recalculate corpus metrics, document report in `p8_remediation_report.md`, and commit logically without pushing.

## Done

- Implemented P8-REM-01 in `src/compiler.py` and `mlog/compiler.py`: added `_is_constant_true(node)` to detect pure compile-time constant true conditions without side effects, and omitted the redundant `jump <while_end> equal true 0` guard in `compile_while()`.
- Synchronized `src/compiler.py` and `mlog/compiler.py` (SHA-256 identical).
- Updated existing regression expectations for loop instruction count in `tests/test_phase1f.py` (`test_14_backward_jump`) and `tests/test_decompiler_loops.py` (`test_loop_header_with_read_side_effect`, `test_loop_header_with_sensor_side_effect`).
- Added `tests/test_p8_remediation.py` with 16 pure compiler unit tests covering `while True:`, `while 1:`, constant folded expressions, `while False:` preservation, dynamic condition preservation, break/continue jump targets, nested loops, while-else blocks, and byte-identical roundtrips for all 5 affected corpus files.
- Added `tests/test_p8_remediation_jvm.py` with 8 Mindustry v160.7 engine runtime tests verifying exact tick counts (including `turret_radar` 200 ticks at 300 steps), variable states, unit bindings, and loop termination on JVM. Registered module in `run_tests.py`.
- Wrote `p8_remediation_report.md` detailing root cause, implementation, tests, before/after metrics, JVM evidence, and remaining out-of-scope differences.
- Recalculated full 32-file corpus metrics:
  - Decompile: 32/32 (100.0%)
  - AST parse: 32/32 (100.0%)
  - Recompile: 30/32 overall (93.75%), 30/30 compilable runnable (100.0%)
  - Recursion rejected: 2/2 (100.0% by design)
  - Byte-identical: 27/30 (90.00%, up from 22/30, +16.67%)
  - Normalized equal: 27/30 (90.00%, up from 22/30, +16.67%)
  - Address coverage: 2095/2095 (100.0%)
  - Statement coverage: 2088/2095 (99.67%)
  - Trace equal: 27/30 (90.00%, up from 22/30, +16.67%)
  - Final state equal: 30/30 (100.0%)

## Next

- none required. Optional future scope:
  - P8-REM-02: align function argument emission order for commutative independent variables in `large_compiler_program`.
  - P8-REM-03: align structurer terminal EOF jump vs idiomatic `end()` in `empty_branches`.
  - P8-REM-04: condition inversion polarity selection for `multi_func_math`.

## Blocked

- none

## Verification

- `python -m unittest tests.test_p8_remediation`: 16 tests, OK.
- `python -m unittest tests.test_p8_remediation_jvm`: 8 tests in 11.71s, OK.
- `python -m unittest tests.test_p7_remediation tests.test_p7_remediation_jvm`: 31 tests in 13.91s, OK.
- `python -m unittest tests.test_p8_remediation tests.test_p8_remediation_jvm`: 24 tests in 12.87s, OK.
- `python run_tests.py --fast`: 887 tests in 79.47s, OK (skipped=3).
- `python run_tests.py --jvm`: 637 tests in 51.52s, OK.
- `python -m mlog.metadata`: metadata stubs verified up-to-date.
- Dynamic Mindustry v160.7 engine validation: `turret_radar` tick count restored to 200 ticks; `flare_miner`, `scale_100`, `scale_500`, and `scale_1000` verified 100% byte-identical and trace-equal.
