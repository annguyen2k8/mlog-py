"""Regression tests for decompiler modern aliases (ucontrol, draw) and FLAG RESET fixture."""

import unittest
from src.decompiler import decompile
from src.mlog import compile_py


class TestDecompilerUcontrolAliases(unittest.TestCase):
    """Verify decompiler converts raw ucontrol and draw instructions to modern Python DSL aliases."""

    def test_flag_reset_fixture(self):
        """FLAG RESET loop preserves lookup, ubind, ucontrol.flag, and loop control flow."""
        mlog = (
            "lookup unit uType i\n"
            "ubind uType\n"
            "sensor f @unit @flag\n"
            "jump 6 notEqual f 0\n"
            "ucontrol flag 0 0 0 0 0\n"
            "op add i i 1\n"
            "jump 0 lessThan i total\n"
        )
        py = decompile(mlog)

        # 1. Imports
        self.assertIn("ucontrol", py)
        self.assertIn("ubind", py)
        self.assertIn("lookup", py)
        self.assertIn("sensor", py)

        # 2. Modern method alias ucontrol.flag(0) instead of ucontrol("flag", ...)
        self.assertIn("ucontrol.flag(0)", py)
        self.assertNotIn('ucontrol("flag"', py)

        # 3. Canonical ubind and lookup
        self.assertIn("ubind(uType)", py)
        self.assertTrue('sensor("@unit", "@flag")' in py or "sensor('@unit', '@flag')" in py)


        # 4. Roundtrip compilation
        recompiled = compile_py(py)
        # Verify instructions present in recompiled mlog
        self.assertIn("lookup unit uType i", recompiled.mlog)
        self.assertIn("ubind uType", recompiled.mlog)
        self.assertIn("sensor f @unit @flag", recompiled.mlog)
        self.assertIn("ucontrol flag 0 0 0 0 0", recompiled.mlog)
        self.assertIn("op add i i 1", recompiled.mlog)

    def test_ucontrol_all_subcommands(self):
        """Verify decompiler output for all UnitControl actions."""
        mlog_actions = [
            ("ucontrol idle 0 0 0 0 0", "ucontrol.idle()"),
            ("ucontrol stop 0 0 0 0 0", "ucontrol.stop()"),
            ("ucontrol move 100 200 0 0 0", "ucontrol.move(100, 200)"),
            ("ucontrol approach 50 60 10 0 0", "ucontrol.approach(50, 60, 10)"),
            ("ucontrol pathfind 10 20 0 0 0", "ucontrol.pathfind(10, 20)"),
            ("ucontrol autoPathfind 0 0 0 0 0", "ucontrol.auto_pathfind()"),
            ("ucontrol boost 1 0 0 0 0", "ucontrol.boost(1)"),
            ("ucontrol target 100 200 1 0 0", "ucontrol.target(100, 200, 1)"),
            ("ucontrol targetp unit 1 0 0 0", "ucontrol.targetp(unit, 1)"),
            ("ucontrol itemDrop core1 50 0 0 0", 'ucontrol.item_drop("core1", 50)'),
            ("ucontrol itemTake core1 @copper 30 0 0", 'ucontrol.item_take("core1", "@copper", 30)'),
            ("ucontrol payDrop 0 0 0 0 0", "ucontrol.pay_drop()"),
            ("ucontrol payTake 1 0 0 0 0", "ucontrol.pay_take(1)"),
            ("ucontrol payEnter 0 0 0 0 0", "ucontrol.pay_enter()"),
            ("ucontrol mine 15 25 0 0 0", "ucontrol.mine(15, 25)"),
            ("ucontrol flag 999 0 0 0 0", "ucontrol.flag(999)"),
            ("ucontrol build 10 20 @router 0 0", 'ucontrol.build(10, 20, "@router", 0, 0)'),
            ("ucontrol deconstruct 10 20 0 0 0", "ucontrol.deconstruct(10, 20)"),
            ("ucontrol getBlock 10 20 out_t out_b out_f", "ucontrol.get_block(10, 20, out_t, out_b, out_f)"),
            ("ucontrol within 10 20 5 in_range 0", "ucontrol.within(10, 20, 5, in_range)"),
            ("ucontrol unbind 0 0 0 0 0", "ucontrol.unbind()"),
        ]
        for mlog_line, expected_py in mlog_actions:
            with self.subTest(action=mlog_line):
                py = decompile(mlog_line + "\n")
                self.assertIn(expected_py, py)
                # Verify recompiled mlog
                recompiled = compile_py(py)
                self.assertEqual(recompiled.mlog.strip(), mlog_line.strip())

    def test_draw_all_subcommands(self):
        """Verify decompiler output for all Draw subcommands."""
        draw_tests = [
            ("draw clear 0 0 0 0 0 0", "draw.clear(0, 0, 0)"),
            ("draw clear 255 128 64 0 0 0", "draw.clear(255, 128, 64)"),
            ("draw color 255 0 0 255 0 0", "draw.color(255, 0, 0)"),
            ("draw color 255 0 0 128 0 0", "draw.color(255, 0, 0, 128)"),
            ("draw col 123456 0 0 0 0 0", "draw.col(123456)"),
            ("draw stroke 2 0 0 0 0 0", "draw.stroke(2)"),
            ("draw line 10 20 30 40 0 0", "draw.line(10, 20, 30, 40)"),
            ("draw rect 0 0 80 80 0 0", "draw.rect(0, 0, 80, 80)"),
            ("draw lineRect 5 5 50 50 0 0", "draw.line_rect(5, 5, 50, 50)"),
            ("draw poly 40 40 6 20 0 0", "draw.poly(40, 40, 6, 20)"),
            ("draw poly 40 40 6 20 45 0", "draw.poly(40, 40, 6, 20, 45)"),
            ("draw linePoly 40 40 8 15 0 0", "draw.line_poly(40, 40, 8, 15)"),
            ("draw triangle 0 0 10 20 30 0", "draw.triangle(0, 0, 10, 20, 30, 0)"),
            ("draw image 50 50 @copper 32 0 0", 'draw.image(50, 50, "@copper")'),
            ("draw image 50 50 @copper 64 0 0", 'draw.image(50, 50, "@copper", 64)'),
            ("draw image 50 50 @copper 64 90 0", 'draw.image(50, 50, "@copper", 64, 90)'),
            ("draw translate 10 20 0 0 0 0", "draw.translate(10, 20)"),
            ("draw scale 2 2 0 0 0 0", "draw.scale(2, 2)"),
            ("draw rotate 0 0 45 0 0 0", "draw.rotate(45)"),
            ("draw reset 0 0 0 0 0 0", "draw.reset()"),

        ]
        for mlog_line, expected_py in draw_tests:
            with self.subTest(draw_op=mlog_line):
                py = decompile(mlog_line + "\n")
                self.assertIn(expected_py, py)
                recompiled = compile_py(py)
                self.assertEqual(recompiled.mlog.strip(), mlog_line.strip())


if __name__ == "__main__":
    unittest.main()
