"""JVM-backed runtime regression tests for P8 remediation (P8-REM-01).

Runs original and decompiled/recompiled programs on real Mindustry v160.7 engine.
Verifies execution equivalence across all observable execution signatures:
step counts (RUN_OK:<steps>), scheduler ticks, registers/variables, bound unit,
message blocks, text buffer, displays, and graphic buffers.
"""

import os
import unittest
from pathlib import Path

from mlog import compile_py
from mlog.decompiler import decompile
from src.mindustry_validator import is_mindustry_available, run_with_mindustry

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "tests" / "corpus"


def _read_corpus(rel_path: str) -> str:
    return (CORPUS_DIR / rel_path).read_text(encoding="utf-8")


def _comparable_vars(run) -> dict:
    return {
        name: value
        for name, value in run.vars.items()
        if not name.startswith("__")
        and not name.startswith("___")
        and name not in ("@counter", "@time", "@tick")
    }


class TestP8RemediationJvm(unittest.TestCase):
    def setUp(self):
        if not is_mindustry_available():
            self.skipTest("Mindustry JVM harness is not available in this environment")

    def _assert_runtime_equal(self, original, new):
        """Compare all observable execution results."""
        self.assertEqual(original.message, new.message)
        self.assertEqual(original.ticks, new.ticks)
        self.assertEqual(original.bound_unit, new.bound_unit)
        self.assertEqual(_comparable_vars(original), _comparable_vars(new))
        self.assertEqual(original.messages, new.messages)
        self.assertEqual(original.text_buffer, new.text_buffer)
        self.assertEqual(original.displays, new.displays)
        self.assertEqual(original.graphics_buffer_size, new.graphics_buffer_size)

    def _roundtrip(self, mlog: str, max_steps: int = 300):
        py = decompile(mlog)
        recompiled = compile_py(py, allow_functions=True, validate=True).mlog
        original = run_with_mindustry(mlog, max_steps=max_steps)
        new = run_with_mindustry(recompiled, max_steps=max_steps)
        self.assertTrue(original.success, original.message)
        self.assertTrue(new.success, new.message)
        return py, recompiled, original, new

    def test_turret_radar_jvm_exact_ticks_and_state(self):
        """turret_radar now achieves exact tick equality (200 ticks at 300 steps).

        In P7, ticks diverged (200 vs 190) due to the redundant leading guard.
        With P8-REM-01 guard elimination, ticks and steps match 100%.
        """
        orig_mlog = _read_corpus("handwritten/turret_radar.mlog")
        py, recompiled, before, after = self._roundtrip(orig_mlog, max_steps=300)

        self._assert_runtime_equal(before, after)
        self.assertEqual(before.message, "RUN_OK:300")
        self.assertEqual(after.message, "RUN_OK:300")
        self.assertEqual(before.ticks, 200)
        self.assertEqual(after.ticks, 200)
        self.assertEqual(after.vars.get("dead"), 1.0)

    def test_flare_miner_jvm_exact_trace_and_state(self):
        """flare_miner achieves exact execution equivalence with bound flare unit."""
        orig_mlog = _read_corpus("handwritten/flare_miner.mlog")
        py, recompiled, before, after = self._roundtrip(orig_mlog, max_steps=300)

        self._assert_runtime_equal(before, after)
        self.assertEqual(before.message, "RUN_OK:300")
        self.assertEqual(after.message, "RUN_OK:300")
        self.assertEqual(before.ticks, 38)
        self.assertEqual(after.ticks, 38)
        self.assertEqual(after.bound_unit, "flare")
        self.assertEqual(after.vars.get("flag"), 1.0)
        self.assertEqual(after.vars.get("item"), 0.0)

    def test_scale_100_jvm_exact_state(self):
        """scale_100 achieves 100% JVM state and tick equivalence."""
        orig_mlog = _read_corpus("pathological/scale_100_instr.mlog")
        py, recompiled, before, after = self._roundtrip(orig_mlog, max_steps=300)

        self._assert_runtime_equal(before, after)
        self.assertEqual(before.ticks, 38)
        self.assertEqual(after.ticks, 38)
        self.assertEqual(after.vars.get("acc"), 8.001953125)
        self.assertEqual(after.vars.get("i"), 10.0)

    def test_scale_500_jvm_exact_state(self):
        """scale_500 achieves 100% JVM state and tick equivalence."""
        orig_mlog = _read_corpus("pathological/scale_500_instr.mlog")
        py, recompiled, before, after = self._roundtrip(orig_mlog, max_steps=300)

        self._assert_runtime_equal(before, after)
        self.assertEqual(before.ticks, 38)
        self.assertEqual(after.ticks, 38)
        self.assertEqual(after.vars.get("acc"), 8.001953125)
        self.assertEqual(after.vars.get("i"), 10.0)

    def test_scale_1000_jvm_exact_state(self):
        """scale_1000 achieves 100% JVM state and tick equivalence."""
        orig_mlog = _read_corpus("pathological/scale_1000_instr.mlog")
        py, recompiled, before, after = self._roundtrip(orig_mlog, max_steps=300)

        self._assert_runtime_equal(before, after)
        self.assertEqual(before.ticks, 38)
        self.assertEqual(after.ticks, 38)
        self.assertEqual(after.vars.get("acc"), 8.001953125)
        self.assertEqual(after.vars.get("i"), 10.0)

    def test_while_true_break_jvm(self):
        """while True: with break terminates at expected step count on JVM."""
        source = (
            "x = 0\n"
            "while True:\n"
            "    x = x + 1\n"
            "    if x >= 5:\n"
            "        break\n"
        )
        mlog = compile_py(source).mlog
        run = run_with_mindustry(mlog, max_steps=100)
        self.assertTrue(run.success)
        self.assertEqual(run.vars.get("x"), 5.0)

    def test_while_false_skipped_jvm(self):
        """while False: body is never executed at runtime."""
        source = (
            "x = 10\n"
            "while False:\n"
            "    x = 99\n"
        )
        mlog = compile_py(source).mlog
        run = run_with_mindustry(mlog, max_steps=50)
        self.assertTrue(run.success)
        self.assertEqual(run.vars.get("x"), 10.0)

    def test_while_dynamic_condition_jvm(self):
        """while i < 4: loops exactly 4 times and terminates."""
        source = (
            "i = 0\n"
            "acc = 0\n"
            "while i < 4:\n"
            "    acc = acc + 10\n"
            "    i = i + 1\n"
        )
        mlog = compile_py(source).mlog
        run = run_with_mindustry(mlog, max_steps=100)
        self.assertTrue(run.success)
        self.assertEqual(run.vars.get("i"), 4.0)
        self.assertEqual(run.vars.get("acc"), 40.0)

    def test_large_compiler_program_jvm_assignment_layout(self):
        """P8-REM-02: large_compiler_program achieves 100% JVM semantic equivalence.

        Proves that commutative assignment of distinct registers (a, b) produces
        identical observable runtime state (300 steps, 38 ticks, identical variables).
        """
        orig_mlog = _read_corpus("compiler_generated/large_compiler_program.mlog")
        py, recompiled, before, after = self._roundtrip(orig_mlog, max_steps=300)

        self._assert_runtime_equal(before, after)
        self.assertEqual(before.message, "RUN_OK:300")
        self.assertEqual(after.message, "RUN_OK:300")
        self.assertEqual(before.ticks, 38)
        self.assertEqual(after.ticks, 38)
        self.assertEqual(after.vars.get("s1"), 13.0)
        self.assertEqual(after.vars.get("z"), 3.0)
        self.assertEqual(after.vars.get("s2"), 33.0)
        self.assertEqual(after.vars.get("acc"), 108.0)
        self.assertEqual(after.vars.get("tmp"), 33.0)

    def test_empty_branches_jvm_eof_termination(self):
        """P8-REM-03: empty_branches EOF termination equivalence across input domain.

        Verifies that 'end' opcode and 'jump 7 always 0 0' produce identical
        runtime behavior across input partitions (val <= 100 and val > 100).
        """
        orig_mlog = _read_corpus("control_flow/empty_branches.mlog")

        # Case 1: val <= 100 (val = 42 default) -> enters then block, val becomes 200
        py, recompiled, before, after = self._roundtrip(orig_mlog, max_steps=100)
        self._assert_runtime_equal(before, after)
        self.assertEqual(before.message, "RUN_OK:6")
        self.assertEqual(after.message, "RUN_OK:6")
        self.assertEqual(before.ticks, 1)
        self.assertEqual(after.ticks, 1)
        self.assertEqual(after.vars.get("val"), 200.0)

        # Case 2: val > 100 (val = 150) -> skips then block, val stays 150
        orig_150 = orig_mlog.replace("set val 42", "set val 150")
        py_150, recompiled_150, before_150, after_150 = self._roundtrip(orig_150, max_steps=100)
        self._assert_runtime_equal(before_150, after_150)
        self.assertEqual(before_150.message, "RUN_OK:4")
        self.assertEqual(after_150.message, "RUN_OK:4")
        self.assertEqual(before_150.ticks, 1)
        self.assertEqual(after_150.ticks, 1)
        self.assertEqual(after_150.vars.get("val"), 150.0)


if __name__ == "__main__":
    unittest.main()
