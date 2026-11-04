# Task handoff

- **Updated**: 2026-11-04
- **Agent**: OpenCode / DeepSeek V4.1 Flash Free
- **Status**: done
- **Goal**: Implement P6 remediation for P6-CRIT-01 (unconditional jump preservation), P6-CRIT-02 (function return destination), P6-CRIT-03 (source-map jump operands), and P6-HIGH-01 (recursion rejection), with regression tests, JVM verification, corpus metrics, and a remediation report.

## Done

- Reproduced all four findings against baseline `0896679`; before/after evidence is in `scratch/p6_before_evidence.txt` and `scratch/p6_after_evidence.txt` (untracked scratch artifacts).
- **P6-CRIT-01** (`src/decompiler/structurer.py`, `mlog/decompiler/structurer.py`):
  - Jumps past the final instruction emit `end()`.
  - A jump to the exclusive range end is consumed only when it is the range's final instruction.
  - Other cross-boundary jumps are preserved as `UnstructuredNode`.
  - Jumps to an unconditional loop latch become `continue`.
  - `base_manager_120.mlog` now maps 120/120 source addresses; address 15 maps to `Continue`.
- **P6-CRIT-02** (`src/compiler.py`, `mlog/compiler.py`): value-producing user calls without `target_dest` capture `__retval_<fn>` into a fresh temporary; statement-only calls still do not allocate a capture.
- **P6-CRIT-03** (`src/decompiler/structured_ir.py`, `src/decompiler/sourcemap.py`, and `mlog/` copies): shared `format_jump_arguments()` formats jump operands semantically in both plain and source-map output. `spaghetti_goto.mlog` recompiles byte-for-byte and runs with identical state.
- **P6-HIGH-01** (`src/compiler.py`, `mlog/compiler.py`): post-fold call-graph cycle detection rejects direct and indirect recursion with the full cycle path. Non-recursive nested calls still compile and run.
- Added `tests/test_p6_remediation.py` (21 pure tests) and `tests/test_p6_remediation_jvm.py` (11 JVM tests); registered the JVM module in `run_tests.py`.
- Updated `tests/test_corpus_hardening.py` so recursive corpus files assert the documented `CompileError` contract.
- Wrote `p6_remediation_report.md` with root causes, before/after evidence, separate fidelity/coverage/runtime metrics, commits, and limitations.
- Recorded the durable contracts in `docs/adr/0003-p6-control-flow-and-recursion-contracts.md` and `docs/adr/README.md`.
- Updated `docs/compiler.md`, `docs/decompiler.md`, `docs/source-mapping.md`, and `SKILL.md`.
- Corpus metrics: byte-for-byte 16/32 -> 17/32; normalized 16/32 -> 17/32; source-map coverage mean 0.9836 -> 0.9884 (full 23/32 -> 25/32); JVM final-state equivalence 29/32 -> 30/32 (2 recursion files rejected by design; `flare_miner.mlog` invalid in both engine runs).
- Commits: `90e8139`, `e04941c`, `7710605`, `f09222a`, `f817459`, plus the docs/report/handoff commit.

## Next

- none

## Blocked

- none

## Verification

- `python run_tests.py --all`: 1468/1468 passed.
- `python run_tests.py --fast`: 850/850 passed.
- `python run_tests.py --jvm`: 618/618 passed on Mindustry v160.7.
- `python -m unittest tests.test_p6_remediation`: 21/21 passed.
- `python -m unittest tests.test_p6_remediation_jvm`: 11/11 passed.
- `python -m unittest tests.test_agent_memory`: 6/6 passed.
- `git diff --check`: clean.
- `src/` and `mlog/` compiler/decompiler files are byte-identical; `semantics.py` differs only by import style as intended.
- No metadata changes, so stubs were not regenerated.

## Remaining limitations

- P6-HIGH-02 (pre-existing, out of scope): `base_manager_120.mlog` recompiled loop exit reaches addresses 20-21 before address 22, while the original exits directly to 22. JVM final state and messages match, but static reachability and unit binding differ. See `p6_remediation_report.md` section 8.2.
- 15 non-byte-equal corpus programs remain (2 recursion rejected by design, 1 engine-invalid, 12 pre-existing expression/temporary differences). All engine-accepted programs have matching final JVM state. See report section 8.1.
- Function-body source-map gaps remain in 7 corpus files (0.9231-0.9756); pre-existing and listed in report section 8.3.
