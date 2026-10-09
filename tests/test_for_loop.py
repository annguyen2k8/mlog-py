"""Tests for Python for-loop support in mlog-py compiler and Mindustry runtime.

Covers:
- for i in range(stop)
- for i in range(start, stop)
- for i in range(start, stop, step) (positive, negative, and dynamic steps)
- Nested for loops
- break and continue inside for loops (continue executes step latch)
- range step == 0 error
- Invalid iterators rejected (e.g. lists, tuples, general functions)
- Non-Name targets rejected
- Full 3-7segments.py real-world display driver regression test
- Mindustry engine validation and runtime execution assertions
"""

import os
import unittest

from src.errors import CompileError
from src.mindustry_validator import (
    is_mindustry_available,
    run_with_mindustry,
    validate_with_mindustry,
)
from src.mlog import compile_py


class TestForLoopCompiler(unittest.TestCase):
    """Unit tests for for-loop compilation."""

    def test_for_range_single_arg(self):
        """for i in range(5) compiles to start=0, step=1 loop."""
        code = """
s = 0
for i in range(5):
    s = s + i
"""
        res = compile_py(code)
        self.assertIn("set i 0", res.mlog)
        self.assertIn("jump", res.mlog)
        self.assertIn("op add i i 1", res.mlog)

        if is_mindustry_available():
            ok, vars_d, msg = run_with_mindustry(res.mlog + "\nend")
            self.assertTrue(ok, f"Runtime error: {msg}")
            self.assertEqual(vars_d.get("s"), 10.0)  # 0+1+2+3+4 == 10
            self.assertEqual(vars_d.get("i"), 5.0)

    def test_for_range_two_args(self):
        """for i in range(2, 6) compiles to start=2, stop=6, step=1 loop."""
        code = """
s = 0
for i in range(2, 6):
    s = s + i
"""
        res = compile_py(code)
        self.assertIn("set i 2", res.mlog)

        if is_mindustry_available():
            ok, vars_d, msg = run_with_mindustry(res.mlog + "\nend")
            self.assertTrue(ok, f"Runtime error: {msg}")
            self.assertEqual(vars_d.get("s"), 14.0)  # 2+3+4+5 == 14
            self.assertEqual(vars_d.get("i"), 6.0)

    def test_for_range_positive_step(self):
        """for i in range(1, 10, 2) compiles with step=2."""
        code = """
s = 0
for i in range(1, 10, 2):
    s = s + i
"""
        res = compile_py(code)
        self.assertIn("set i 1", res.mlog)
        self.assertIn("op add i i 2", res.mlog)

        if is_mindustry_available():
            ok, vars_d, msg = run_with_mindustry(res.mlog + "\nend")
            self.assertTrue(ok, f"Runtime error: {msg}")
            self.assertEqual(vars_d.get("s"), 25.0)  # 1+3+5+7+9 == 25

    def test_for_range_negative_step(self):
        """for i in range(10, 0, -2) compiles with negative step and lessThanEq check."""
        code = """
s = 0
for i in range(10, 0, -2):
    s = s + i
"""
        res = compile_py(code)
        self.assertIn("set i 10", res.mlog)

        if is_mindustry_available():
            ok, vars_d, msg = run_with_mindustry(res.mlog + "\nend")
            self.assertTrue(ok, f"Runtime error: {msg}")
            self.assertEqual(vars_d.get("s"), 30.0)  # 10+8+6+4+2 == 30

    def test_for_range_dynamic_step(self):
        """for i in range(start, stop, step) handles variable step correctly."""
        code = """
start = 1
stop = 5
step = 1
s = 0
for i in range(start, stop, step):
    s = s + i
"""
        res = compile_py(code)
        self.assertIsNotNone(res.mlog)

        if is_mindustry_available():
            ok, vars_d, msg = run_with_mindustry(res.mlog + "\nend")
            self.assertTrue(ok, f"Runtime error: {msg}")
            self.assertEqual(vars_d.get("s"), 10.0)  # 1+2+3+4 == 10

    def test_for_loop_break_and_continue(self):
        """continue in for loop must hit step increment latch before repeating."""
        code = """
s = 0
for i in range(10):
    if i == 2:
        continue
    if i == 6:
        break
    s = s + i
"""
        res = compile_py(code)
        if is_mindustry_available():
            ok, vars_d, msg = run_with_mindustry(res.mlog + "\nend")
            self.assertTrue(ok, f"Runtime error: {msg}")
            # i = 0 (s=0), 1 (s=1), 2 (skip), 3 (s=4), 4 (s=8), 5 (s=13), 6 (break)
            self.assertEqual(vars_d.get("s"), 13.0)
            self.assertEqual(vars_d.get("i"), 6.0)

    def test_for_loop_nested(self):
        """Nested for loops must maintain independent loop stacks and latches."""
        code = """
total = 0
for i in range(3):
    for j in range(4):
        total = total + 1
"""
        res = compile_py(code)
        if is_mindustry_available():
            ok, vars_d, msg = run_with_mindustry(res.mlog + "\nend")
            self.assertTrue(ok, f"Runtime error: {msg}")
            self.assertEqual(vars_d.get("total"), 12.0)

    def test_for_range_zero_step_rejected(self):
        """range() with step 0 must be rejected."""
        code = "for i in range(0, 10, 0): pass"
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("range() step argument must not be zero", str(ctx.exception))

    def test_for_non_range_iter_rejected(self):
        """Only range(...) is supported as for loop iterator."""
        cases = [
            ("for i in [1, 2, 3]: pass", "for loop only supports 'range(...)' as iterator"),
            ("for i in (1, 2): pass", "for loop only supports 'range(...)' as iterator"),
            ("for i in get_items(): pass", "for loop only supports 'range(...)' as iterator"),
            ("for i in range(): pass", "range() expects 1 to 3 arguments in for loop"),
            ("for i in range(1, 2, 3, 4): pass", "range() expects 1 to 3 arguments in for loop"),
            ("for i in range(10, step=2): pass", "range() does not support keyword arguments"),
            ("for a, b in range(10): pass", "for loop target must be a simple variable name"),
        ]
        for src, err_sub in cases:
            with self.subTest(src=src):
                with self.assertRaises(CompileError) as ctx:
                    compile_py(src)
                self.assertIn(err_sub, str(ctx.exception))

    def test_3_7segments_regression(self):
        """Verify the exact user script 3-7segments.py compiles and runs in Mindustry."""
        sample_path = "/data/data/com.termux/files/home/mlogs/3-7segments.py"
        if not os.path.exists(sample_path):
            self.skipTest(f"{sample_path} not found")

        with open(sample_path, "r", encoding="utf-8") as f:
            code = f.read()

        res = compile_py(code)
        self.assertIsNotNone(res.mlog)

        if is_mindustry_available():
            val_ok, vmsg, count = validate_with_mindustry(res.mlog)
            self.assertTrue(val_ok, f"Mindustry assembly validation failed: {vmsg}")
            self.assertGreater(count, 80)

            run_ok, vars_d, rmsg = run_with_mindustry(res.mlog)
            self.assertTrue(run_ok, f"Mindustry runtime execution failed: {rmsg}")
            # Variable assertions after 3 loop iterations:
            # i should be 3, x offset accumulated: offsetx + 3 * (w + padding) == 7 + 3*(20+12) = 103
            self.assertEqual(vars_d.get("i"), 3.0)
            self.assertEqual(vars_d.get("x"), 103.0)
            self.assertEqual(vars_d.get("n"), 0.0)


if __name__ == "__main__":
    unittest.main()
