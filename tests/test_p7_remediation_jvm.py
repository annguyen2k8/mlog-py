"""JVM-backed regression tests for P7 remediation.

Runs original and decompiled/recompiled programs on the real Mindustry v160.7
LExecutor. The exact PC trace is audited with the external trace harness; these
tests assert the equivalent observable execution signature available through the
public validator: run length (``RUN_OK:<steps>``), ticks, variables, message
blocks, text buffer, displays, and bound unit.
"""

import os
import unittest

from src.decompiler import decompile
from src.mindustry_validator import is_mindustry_available, run_with_mindustry
from src.mlog import compile_py

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(REPO_ROOT, "tests", "corpus")


def _read_corpus(relative_path):
    with open(os.path.join(CORPUS, relative_path), "r", encoding="utf-8") as handle:
        return handle.read()


def _normalized_lines(text):
    return [line.strip() for line in text.strip().splitlines()]


def _comparable_vars(run):
    return {
        name: value
        for name, value in run.vars.items()
        if not name.startswith("__")
        and not name.startswith("___")
        and name not in ("@counter", "@time", "@tick")
    }


class TestP7RemediationJvm(unittest.TestCase):
    def setUp(self):
        if not is_mindustry_available():
            self.skipTest("Mindustry JVM harness is not available in this environment")

    def _roundtrip(self, mlog, max_steps=300):
        py = decompile(mlog)
        recompiled = compile_py(py, allow_functions=True, validate=True).mlog
        original = run_with_mindustry(mlog, max_steps=max_steps)
        new = run_with_mindustry(recompiled, max_steps=max_steps)
        self.assertTrue(original.success, original.message)
        self.assertTrue(new.success, new.message)
        return py, recompiled, original, new

    def _assert_runtime_equal(self, original, new):
        """Compare every observable execution result, not only final vars."""
        self.assertEqual(original.message, new.message)
        self.assertEqual(original.ticks, new.ticks)
        self.assertEqual(original.bound_unit, new.bound_unit)
        self.assertEqual(_comparable_vars(original), _comparable_vars(new))
        self.assertEqual(original.messages, new.messages)
        self.assertEqual(original.text_buffer, new.text_buffer)
        self.assertEqual(original.displays, new.displays)
        self.assertEqual(original.graphics_buffer_size, new.graphics_buffer_size)

    # ------------------------------------------------------------------
    # P7-CRIT-01
    # ------------------------------------------------------------------

    def test_crit01_arithmetic_variant_runtime(self):
        original = _read_corpus("compiler_generated/arithmetic_dataflow.mlog")
        variant = original.replace("set a 10", "set a 30")

        py, recompiled, before, after = self._roundtrip(variant)
        self.assertIn("if y > 100 and x < 500:", py)
        self.assertEqual(_normalized_lines(recompiled), _normalized_lines(variant))
        self._assert_runtime_equal(before, after)

        # The dropped edge used to leave res unset here.
        self.assertEqual(before.message, "RUN_OK:18")
        self.assertEqual(before.vars.get("x"), 682.0)
        self.assertEqual(after.vars.get("res"), 0.0)

    def test_crit01_short_circuit_variant_runtime(self):
        original = _read_corpus("control_flow/short_circuit_ladder.mlog")
        variant = original.replace("set a 1", "set a 5").replace("set d 4", "set d 5")

        py, recompiled, before, after = self._roundtrip(variant)
        self.assertIn('jump(9, "lessThan", b, c)', py)
        self.assertEqual(_normalized_lines(recompiled), _normalized_lines(variant))
        self._assert_runtime_equal(before, after)

        # The inner false edge used to skip `flag = 0 - 1`.
        self.assertEqual(before.message, "RUN_OK:9")
        self.assertEqual(before.vars.get("flag"), -1.0)
        self.assertEqual(after.vars.get("flag"), -1.0)

    def test_crit01_reactor_variant_runtime(self):
        original = _read_corpus("handwritten/reactor_safety.mlog")
        variant = original.replace(
            "sensor heat reactor1 @heat", "set heat 0.5"
        ).replace("sensor cryo reactor1 @cryofluid", "set cryo 20")

        py, recompiled, before, after = self._roundtrip(variant)
        self.assertIn("if cryo >= 10 and heat <= 0.2:", py)
        self.assertEqual(_normalized_lines(recompiled), _normalized_lines(variant))
        self._assert_runtime_equal(before, after)

        # The hot-reactor path used to report nominal status.
        self.assertEqual(before.message, "RUN_OK:8")
        self.assertEqual(
            before.messages.get("message1"), "ALERT: Reactor Overheating"
        )
        self.assertEqual(
            after.messages.get("message1"), "ALERT: Reactor Overheating"
        )

    # ------------------------------------------------------------------
    # P7-CRIT-02
    # ------------------------------------------------------------------

    def test_crit02_computed_jump_counter_runtime(self):
        mlog = _read_corpus("pathological/computed_jump_counter.mlog")
        py, recompiled, before, after = self._roundtrip(mlog)

        self.assertIn('op("add", raw("@counter"), raw("@counter"), offset)', py)
        self.assertIn("op add @counter @counter offset", recompiled)
        self.assertEqual(_normalized_lines(recompiled), _normalized_lines(mlog))
        self._assert_runtime_equal(before, after)

        # The recompiled form used to jump to address 3 instead of 4.
        self.assertEqual(before.message, "RUN_OK:7")
        self.assertEqual(before.vars.get("r"), 2.0)
        self.assertEqual(after.vars.get("r"), 2.0)
        self.assertEqual(after.messages.get("message1"), "2")

    def test_crit02_set_register_value_runtime(self):
        mlog = "set x @counter\nprint x\nprintflush message1\n"
        py, _, before, after = self._roundtrip(mlog, max_steps=50)
        self.assertIn('x = raw("@counter")', py)
        self._assert_runtime_equal(before, after)
        self.assertEqual(before.vars.get("x"), 1.0)
        self.assertEqual(after.messages.get("message1"), "1")

    def test_crit02_op_register_operand_runtime(self):
        mlog = "op add x @time 1\nprint x\nprintflush message1\n"
        py, _, before, after = self._roundtrip(mlog, max_steps=50)
        self.assertIn('x = raw("@time") + 1', py)
        self._assert_runtime_equal(before, after)
        self.assertEqual(before.vars.get("x"), 1.0)
        self.assertEqual(after.vars.get("x"), 1.0)
        self.assertEqual(after.messages.get("message1"), "1")

    def test_crit02_jump_condition_register_runtime(self):
        mlog = "jump 2 equal @unit null\nset x 1\nset x 2\n"
        py, recompiled, before, after = self._roundtrip(mlog, max_steps=50)
        self.assertIn('if raw("@unit") != None:', py)
        self.assertEqual(_normalized_lines(recompiled), _normalized_lines(mlog))
        self._assert_runtime_equal(before, after)
        self.assertEqual(before.message, "RUN_OK:2")
        self.assertEqual(after.vars.get("x"), 2.0)

    def test_crit02_unit_register_runtime(self):
        mlog = "ubind @flare\nset u @unit\nprint u\nprintflush message1\n"
        py, _, before, after = self._roundtrip(mlog, max_steps=50)
        self.assertIn('u = raw("@unit")', py)
        self._assert_runtime_equal(before, after)
        self.assertEqual(before.bound_unit, "flare")
        self.assertEqual(after.bound_unit, "flare")
        self.assertEqual(after.vars.get("u"), "flare")
        self.assertEqual(after.messages.get("message1"), "flare")

    # ------------------------------------------------------------------
    # P7-HIGH-01
    # ------------------------------------------------------------------

    def test_high01_base_manager_ratio_variant_runtime(self):
        original = _read_corpus("handwritten/base_manager_120.mlog")
        # Operand-only change: makes t_hp_ratio < 0.4 so the turret loop exits.
        variant = original.replace(
            "op div t_hp_ratio t_hp t_max_hp", "op div t_hp_ratio 1 10"
        )
        self.assertNotEqual(variant, original)

        py, recompiled, before, after = self._roundtrip(variant)
        self.assertIn("Loop exit at address 22", py)
        self.assertIn("Loop exit at address 36", py)
        self._assert_runtime_equal(before, after)

        # The old output resumed at 20 and 33, executing the skipped gap.
        self.assertEqual(before.message, "RUN_OK:178")
        self.assertEqual(before.ticks, after.ticks)
        self.assertIsNone(before.bound_unit)
        self.assertIsNone(after.bound_unit)
        self.assertEqual(before.vars.get("u_flag"), after.vars.get("u_flag"))
        self.assertEqual(before.vars.get("bar_w"), after.vars.get("bar_w"))
        self.assertEqual(after.vars.get("u_flag"), "null")
        self.assertEqual(after.vars.get("bar_w"), "null")
        self.assertEqual(
            before.messages.get("message1"), "Status: Nominal"
        )
        self.assertEqual(after.messages.get("message1"), "Status: Nominal")

    # ------------------------------------------------------------------
    # P7-LOW-02
    # ------------------------------------------------------------------

    def test_low02_base_manager_corpus_terminates(self):
        mlog = _read_corpus("handwritten/base_manager_120.mlog")
        py, recompiled, before, after = self._roundtrip(mlog, max_steps=300)

        self.assertIn("Loop exit at address 22", py)
        self.assertIn("Loop exit at address 36", py)
        self.assertEqual(_normalized_lines(recompiled), _normalized_lines(mlog))
        self._assert_runtime_equal(before, after)

        # Before the corpus fix, address 15 skipped the counter increment and
        # the committed input looped until the step cap.
        self.assertEqual(before.message, "RUN_OK:184")
        self.assertEqual(before.ticks, 23)
        self.assertEqual(before.vars.get("turret_idx"), 4.0)
        self.assertEqual(before.vars.get("cell_idx"), 8.0)
        self.assertEqual(before.messages.get("message1"), "Status: Nominal")

    def test_low02_flare_miner_corpus_is_engine_valid(self):
        mlog = _read_corpus("handwritten/flare_miner.mlog")
        py, recompiled, before, after = self._roundtrip(mlog, max_steps=300)

        self.assertIn('ulocate.building("storage", 0)', py)
        self.assertIn(
            "ulocate building storage 0 @copper cx cy found cblock", recompiled
        )
        self._assert_runtime_equal(before, after)

        # Before the corpus fix, the engine rejected `ulocate building
        # container` on both forms.
        self.assertEqual(before.message, "RUN_OK:300")
        self.assertEqual(before.bound_unit, "flare")
        self.assertEqual(after.vars.get("flag"), 1.0)
        self.assertEqual(after.vars.get("item"), 0.0)


if __name__ == "__main__":
    unittest.main()
