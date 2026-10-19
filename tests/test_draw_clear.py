"""Regression tests for draw.clear(r=0, g=0, b=0, a=0) API, compiler, decompiler, and runtime."""

import unittest
from src.compiler import CompileError
from src.decompiler import decompile
from src.mlog import compile_py
import src.mlog as mlog


class TestDrawClear(unittest.TestCase):
    """Test draw.clear API with default, positional, keyword args and roundtrip."""

    def test_draw_clear_zero_args(self):
        """draw.clear() with no arguments defaults to r=0, g=0, b=0 (and a=0)."""
        code = "from mlog import draw\ndraw.clear()\n"
        res = compile_py(code)
        self.assertIn("draw clear 0 0 0 0 0 0", res.mlog)

    def test_draw_clear_one_arg(self):
        """draw.clear(255) defaults g=0, b=0."""
        code = "from mlog import draw\ndraw.clear(255)\n"
        res = compile_py(code)
        self.assertIn("draw clear 255 0 0 0 0 0", res.mlog)

    def test_draw_clear_two_args(self):
        """draw.clear(255, 128) defaults b=0."""
        code = "from mlog import draw\ndraw.clear(255, 128)\n"
        res = compile_py(code)
        self.assertIn("draw clear 255 128 0 0 0 0", res.mlog)

    def test_draw_clear_three_args(self):
        """draw.clear(255, 128, 64) emits RGB."""
        code = "from mlog import draw\ndraw.clear(255, 128, 64)\n"
        res = compile_py(code)
        self.assertIn("draw clear 255 128 64 0 0 0", res.mlog)

    def test_draw_clear_four_args(self):
        """draw.clear(255, 128, 64, 255) accepts alpha parameter safely for RGBA habit."""
        code = "from mlog import draw\ndraw.clear(255, 128, 64, 255)\n"
        res = compile_py(code)
        self.assertIn("draw clear 255 128 64 0 0 0", res.mlog)

    def test_draw_clear_keywords(self):
        """draw.clear supports r, g, b, a keywords in any order."""
        code = "from mlog import draw\ndraw.clear(b=64, r=255, g=128)\n"
        res = compile_py(code)
        self.assertIn("draw clear 255 128 64 0 0 0", res.mlog)

        code_rgba = "from mlog import draw\ndraw.clear(r=10, g=20, b=30, a=40)\n"
        res_rgba = compile_py(code_rgba)
        self.assertIn("draw clear 10 20 30 0 0 0", res_rgba.mlog)

    def test_draw_clear_mixed_pos_and_keywords(self):
        """Positional and keyword arguments can be mixed safely."""
        code = "from mlog import draw\ndraw.clear(10, b=30, g=20)\n"
        res = compile_py(code)
        self.assertIn("draw clear 10 20 30 0 0 0", res.mlog)

    def test_draw_clear_too_many_args_error(self):
        """Passing more than 4 arguments raises CompileError."""
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import draw\ndraw.clear(1, 2, 3, 4, 5)\n")
        self.assertIn("invalid arguments for draw.clear", str(ctx.exception))

    def test_draw_clear_invalid_keyword_error(self):
        """Passing unexpected keyword argument raises CompileError."""
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import draw\ndraw.clear(r=1, invalid_arg=2)\n")
        self.assertIn("invalid arguments for draw.clear", str(ctx.exception))

    def test_draw_clear_duplicate_arg_error(self):
        """Providing argument positionally and by keyword raises CompileError."""
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import draw\ndraw.clear(10, r=20)\n")
        self.assertIn("invalid arguments for draw.clear", str(ctx.exception))

    def test_draw_clear_decompiler_roundtrip(self):
        """Mlog 'draw clear r g b 0 0 0' decompiles to 'draw.clear(r, g, b)' and roundtrips."""
        mlog_in = "draw clear 255 128 0 0 0 0\n"
        py = decompile(mlog_in)
        self.assertIn("draw.clear(255, 128, 0)", py)
        recompiled = compile_py(py)
        self.assertIn("draw clear 255 128 0 0 0 0", recompiled.mlog)

    def test_draw_clear_zeros_decompiler_roundtrip(self):
        """Mlog 'draw clear 0 0 0 0 0 0' decompiles to 'draw.clear(0, 0, 0)' and roundtrips."""
        mlog_in = "draw clear 0 0 0 0 0 0\n"
        py = decompile(mlog_in)
        self.assertIn("draw.clear(0, 0, 0)", py)
        recompiled = compile_py(py)
        self.assertIn("draw clear 0 0 0 0 0 0", recompiled.mlog)

    def test_draw_clear_runtime_callable(self):
        """Runtime object supports calling clear with 0 to 4 arguments."""
        self.assertIsNone(mlog.draw.clear())
        self.assertIsNone(mlog.draw.clear(255))
        self.assertIsNone(mlog.draw.clear(255, 128))
        self.assertIsNone(mlog.draw.clear(255, 128, 64))
        self.assertIsNone(mlog.draw.clear(255, 128, 64, 255))
        self.assertIsNone(mlog.draw.clear(r=10, g=20, b=30, a=40))


if __name__ == "__main__":
    unittest.main()
