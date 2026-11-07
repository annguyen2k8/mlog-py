# Task handoff

- **Updated**: 2026-11-07
- **Agent**: OpenCode / DeepSeek V4.1 Flash Free
- **Status**: done
- **Goal**: Complete P7 remediation from baseline `54179b5`: fix verified decompiler fidelity defects, prove execution equivalence on Mindustry v160.7, re-audit the 32-file corpus with separated metrics and exact PC traces, document results, and commit without pushing.

## Done

- Fixed P7-CRIT-01 dropped else edges in `mlog/decompiler/structurer.py` and `src/decompiler/structurer.py`. Exact deferred chains flatten into `if outer and inner: ... else: ...`; interleaved chains keep the conditional jump as an `UnstructuredNode`, preserving the else edge.
- Fixed P7-CRIT-02 bare `@` registers in `structured_ir.py` and `expression.py` (both trees). Generic value positions emit `raw("@counter")`, `raw("@time")`, `raw("@unit")`; quoted `"@..."` tokens remain Python strings.
- Fixed P7-HIGH-01 loop-exit gaps: when `loop.exit_address > loop.max_body_address + 1`, the whole loop region up to `exit_address` is emitted as raw code and structuring resumes exactly at `exit_address`. No addresses hardcoded.
- Fixed P7-MED-01/MED-02 in `sourcemap.py` (both trees): address 0 has a coarse `Preamble` mapping; `FunctionDef` mappings are coarse; added `coverage_summary`, `mapped_addresses`, `missing_addresses`; `mlog_to_python()` prefers non-coarse statement mappings.
- Fixed P7-LOW-02 corpus defects:
  - `tests/corpus/handwritten/base_manager_120.mlog` address 15 changed from `jump 19` to `jump 18` so the counter increment is reachable and the input exits the turret loop.
  - `tests/corpus/handwritten/flare_miner.mlog` changed `ulocate building container` to `ulocate building storage`; the input is now engine-valid.
- Added `tests/test_p7_remediation.py` (20 pure tests) and `tests/test_p7_remediation_jvm.py` (11 JVM tests); registered the JVM module in `run_tests.py`.
- Updated existing decompiler/P5/P6/tier-3 expectations for `raw()` register output and corrected loop fixtures.
- Updated docs: `docs/decompiler.md`, `docs/source-mapping.md`, `docs/semantic-arguments.md`, `SKILL.md`, new `docs/adr/0004-p7-decompiler-fidelity-contracts.md`, `docs/adr/README.md`. Corrected superseded P6 claims in `p6_remediation_report.md` and ADR-003.
- Wrote `p7_fidelity_audit.md` (read-only audit) and `p7_remediation_report.md` (root causes, before/after traces, metrics, limits, commits).
- Corpus metrics after remediation: decompile 32/32; recompile 30/32 (2 recursion rejections by design); byte-identical 22/30; normalized 22/30; address coverage 32/32 files and 2095/2095 instructions; statement coverage 2088/2095 (99.67%, missing only address 0 in 7 function files); trace-equal 22/30; final-state-equal 30/30.
- Exact external traces now equal for all dropped-else variants, the base-manager ratio variant, `computed_jump_counter`, and the register cases.
- Commit `fde8a92` (decompiler fixes), `49cc70f` (tests), `44952f4` (corpus fixes + LOW-02 tests). Docs/report/audit/handoff are committed separately after this file.

## Next

- none required. Optional follow-up: eliminate the always-false leading guards in `turret_radar`, `flare_miner`, and `scale_*` to improve trace/timing fidelity (P7-LOW-01); this needs instruction-budget/timing-aware structuring and is out of P7 scope.

## Blocked

- none

## Verification

- `python run_tests.py --fast`: Ran 871 tests, OK (skipped=3).
- `python run_tests.py --jvm`: Ran 629 tests, OK.
- `python run_tests.py --all`: Ran 1500 tests, OK (skipped=3).
- `python -m unittest tests.test_p7_remediation`: Ran 20 tests, OK.
- `python -m unittest tests.test_p7_remediation_jvm`: Ran 11 tests, OK.
- `python -m unittest tests.test_p6_remediation_jvm tests.test_p7_remediation_jvm`: Ran 22 tests, OK.
- 32-file corpus re-run with exact `TRACE:<step>:<pc>` harness on Mindustry v160.7; aggregate metrics above.
- `src/decompiler/` and `mlog/decompiler/` code files SHA-256 identical; no metadata change, so stubs were not regenerated.
- `git diff --check` clean.

## Remaining limitations

- 8/30 compiled files are not byte-identical and not trace-equal: `large_compiler_program`, `multi_func_math`, `empty_branches`, `flare_miner`, `turret_radar`, `scale_100`, `scale_500`, `scale_1000`. All have equal final state on tested inputs; differences are layout, always-false leading guards, or timing (`@tick`/instruction budget).
- Recursion remains rejected by design (`recursive_factorial`, `recursion`); no runtime comparison exists.
- JVM harness uses a synthetic world and a 300-step cap; exact trace harness is external to the repo and not part of CI.
- Statement-level source coverage intentionally excludes address 0 in function files; address-level coverage includes the coarse `Preamble` mapping.
