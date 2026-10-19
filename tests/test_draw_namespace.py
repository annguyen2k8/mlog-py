"""Unit and regression tests for Draw Callable Namespace Object (draw.<method>).

Verifies Mindustry v160.7 Draw opcode format, parameter ordering, backward compatibility
with legacy draw(...) syntax, error checking for arity/unknown methods, and runtime execution.
"""

import unittest
from src.errors import CompileError
from src.mlog import DrawType, compile_py
import src.mlog as mlog


class TestDrawCallableNamespace(unittest.TestCase):
    """Test modern draw.<method>(...) syntax compilation and semantics."""

    def test_clear_method(self):
        code = "from mlog import draw\ndraw.clear(255, 128, 0)\n"
        res = compile_py(code)
        self.assertIn("draw clear 255 128 0 0 0 0", res.mlog)

    def test_color_method(self):
        # 4 args
        code4 = "from mlog import draw\ndraw.color(255, 128, 0, 200)\n"
        res4 = compile_py(code4)
        self.assertIn("draw color 255 128 0 200 0 0", res4.mlog)

        # 3 args (default alpha=255)
        code3 = "from mlog import draw\ndraw.color(10, 20, 30)\n"
        res3 = compile_py(code3)
        self.assertIn("draw color 10 20 30 255 0 0", res3.mlog)

        # keyword arg a
        code_kw = "from mlog import draw\ndraw.color(10, 20, 30, a=100)\n"
        res_kw = compile_py(code_kw)
        self.assertIn("draw color 10 20 30 100 0 0", res_kw.mlog)

    def test_col_method(self):
        code = "from mlog import draw\ndraw.col(16711935)\n"
        res = compile_py(code)
        self.assertIn("draw col 16711935 0 0 0 0", res.mlog)

    def test_stroke_method(self):
        code = "from mlog import draw\ndraw.stroke(3.5)\n"
        res = compile_py(code)
        self.assertIn("draw stroke 3.5 0 0 0 0", res.mlog)

    def test_line_method(self):
        code = "from mlog import draw\ndraw.line(0, 0, 100, 200)\n"
        res = compile_py(code)
        self.assertIn("draw line 0 0 100 200 0 0", res.mlog)

    def test_rect_method(self):
        code = "from mlog import draw\ndraw.rect(10, 20, 50, 60)\n"
        res = compile_py(code)
        self.assertIn("draw rect 10 20 50 60 0 0", res.mlog)

    def test_line_rect_method_and_alias(self):
        # snake_case
        code_snake = "from mlog import draw\ndraw.line_rect(5, 15, 40, 50)\n"
        res_snake = compile_py(code_snake)
        self.assertIn("draw lineRect 5 15 40 50 0 0", res_snake.mlog)

        # camelCase
        code_camel = "from mlog import draw\ndraw.lineRect(5, 15, 40, 50)\n"
        res_camel = compile_py(code_camel)
        self.assertIn("draw lineRect 5 15 40 50 0 0", res_camel.mlog)

    def test_poly_method(self):
        # 4 args (default rotation=0)
        code4 = "from mlog import draw\ndraw.poly(40, 40, 6, 20)\n"
        res4 = compile_py(code4)
        self.assertIn("draw poly 40 40 6 20 0 0", res4.mlog)

        # 5 args
        code5 = "from mlog import draw\ndraw.poly(40, 40, 6, 20, 45)\n"
        res5 = compile_py(code5)
        self.assertIn("draw poly 40 40 6 20 45 0", res5.mlog)

        # keyword arg rotation
        code_kw = "from mlog import draw\ndraw.poly(40, 40, 8, 25, rotation=30)\n"
        res_kw = compile_py(code_kw)
        self.assertIn("draw poly 40 40 8 25 30 0", res_kw.mlog)

    def test_line_poly_method_and_alias(self):
        # snake_case 4 args
        code_snake4 = "from mlog import draw\ndraw.line_poly(50, 50, 5, 15)\n"
        res_snake4 = compile_py(code_snake4)
        self.assertIn("draw linePoly 50 50 5 15 0 0", res_snake4.mlog)

        # snake_case 5 args
        code_snake5 = "from mlog import draw\ndraw.line_poly(50, 50, 5, 15, 60)\n"
        res_snake5 = compile_py(code_snake5)
        self.assertIn("draw linePoly 50 50 5 15 60 0", res_snake5.mlog)

        # camelCase
        code_camel = "from mlog import draw\ndraw.linePoly(50, 50, 5, 15, 60)\n"
        res_camel = compile_py(code_camel)
        self.assertIn("draw linePoly 50 50 5 15 60 0", res_camel.mlog)

    def test_triangle_method(self):
        code = "from mlog import draw\ndraw.triangle(0, 0, 20, 40, 40, 0)\n"
        res = compile_py(code)
        self.assertIn("draw triangle 0 0 20 40 40 0", res.mlog)

    def test_image_method(self):
        # 3 args (default size=32, rotation=0)
        code3 = "from mlog import draw\ndraw.image(30, 40, '@copper')\n"
        res3 = compile_py(code3)
        self.assertIn("draw image 30 40 @copper 32 0 0", res3.mlog)

        # 4 args (default rotation=0)
        code4 = "from mlog import draw\ndraw.image(30, 40, '@router', 64)\n"
        res4 = compile_py(code4)
        self.assertIn("draw image 30 40 @router 64 0 0", res4.mlog)

        # 5 args
        code5 = "from mlog import draw\ndraw.image(30, 40, '@lead', 64, 90)\n"
        res5 = compile_py(code5)
        self.assertIn("draw image 30 40 @lead 64 90 0", res5.mlog)

        # keywords
        code_kw = "from mlog import draw\ndraw.image(30, 40, '@titanium', rotation=180)\n"
        res_kw = compile_py(code_kw)
        self.assertIn("draw image 30 40 @titanium 32 180 0", res_kw.mlog)

    def test_print_method(self):
        # 2 args (default align=0)
        code2 = "from mlog import draw\ndraw.print(10, 20)\n"
        res2 = compile_py(code2)
        self.assertIn("draw print 10 20 0 0 0 0", res2.mlog)

        # 3 args
        code3 = "from mlog import draw\ndraw.print(10, 20, 2)\n"
        res3 = compile_py(code3)
        self.assertIn("draw print 10 20 2 0 0 0", res3.mlog)

        # keyword align
        code_kw = "from mlog import draw\ndraw.print(10, 20, align=1)\n"
        res_kw = compile_py(code_kw)
        self.assertIn("draw print 10 20 1 0 0 0", res_kw.mlog)

    def test_translate_method(self):
        code = "from mlog import draw\ndraw.translate(15, 25)\n"
        res = compile_py(code)
        self.assertIn("draw translate 15 25 0 0 0 0", res.mlog)

    def test_scale_method(self):
        code = "from mlog import draw\ndraw.scale(2, 3)\n"
        res = compile_py(code)
        self.assertIn("draw scale 2 3 0 0 0 0", res.mlog)

    def test_rotate_method_mindustry_layout(self):
        """Mindustry v160.7 LStatements.java maps angle to p1, leaving x=0, y=0."""
        code = "from mlog import draw\ndraw.rotate(45)\n"
        res = compile_py(code)
        self.assertIn("draw rotate 0 0 45 0 0 0", res.mlog)

    def test_reset_method(self):
        code = "from mlog import draw\ndraw.reset()\n"
        res = compile_py(code)
        self.assertIn("draw reset 0 0 0 0 0 0", res.mlog)

    def test_flush_method(self):
        code = "from mlog import draw\ndraw.flush('display1')\n"
        res = compile_py(code)
        self.assertIn("drawflush display1", res.mlog)


class TestDrawBackwardCompatibility(unittest.TestCase):
    """Test that legacy draw(...) calls remain 100% functional and unchanged."""

    def test_legacy_draw_string_type(self):
        code = "from mlog import draw\ndraw('line', 1, 2, 3, 4)\n"
        res = compile_py(code)
        self.assertIn("draw line 1 2 3 4 0 0", res.mlog)

    def test_legacy_draw_enum_type(self):
        code = "from mlog import draw, DrawType\ndraw(DrawType.CLEAR, 0, 0, 0)\n"
        res = compile_py(code)
        self.assertIn("draw clear 0 0 0 0 0 0", res.mlog)

    def test_legacy_draw_with_variables(self):
        code = "from mlog import draw\nx = 10\ny = 20\ndraw('rect', x, y, 50, 50)\n"
        res = compile_py(code)
        self.assertIn("draw rect x y 50 50 0 0", res.mlog)


class TestDrawErrorHandling(unittest.TestCase):
    """Test validation errors for invalid arity, unknown methods, and keywords."""

    def test_clear_invalid_arity(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import draw\ndraw.clear(1, 2, 3, 4, 5)\n")
        self.assertIn("invalid arguments for draw.clear", str(ctx.exception))


    def test_line_invalid_arity(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import draw\ndraw.line(1, 2, 3)\n")
        self.assertIn("expected draw.line(x1, y1, x2, y2)", str(ctx.exception))

    def test_rotate_invalid_arity(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import draw\ndraw.rotate()\n")
        self.assertIn("expected draw.rotate(degrees)", str(ctx.exception))

        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import draw\ndraw.rotate(1, 2)\n")
        self.assertIn("expected draw.rotate(degrees)", str(ctx.exception))

    def test_reset_invalid_arity(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import draw\ndraw.reset(1)\n")
        self.assertIn("expected draw.reset()", str(ctx.exception))

    def test_flush_invalid_arity(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import draw\ndraw.flush()\n")
        self.assertIn("expected draw.flush(display)", str(ctx.exception))

    def test_unknown_draw_method(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import draw\ndraw.circle(10, 10, 5)\n")
        self.assertIn("unknown draw method: 'draw.circle'", str(ctx.exception))

    def test_invalid_keyword_argument(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import draw\ndraw.clear(255, 0, 0, foo=1)\n")
        self.assertIn("invalid arguments for draw.clear", str(ctx.exception))


class TestDrawRuntimeCallability(unittest.TestCase):
    """Test direct Python execution of draw namespace object and methods."""

    def test_runtime_draw_call(self):
        self.assertIsNone(mlog.draw("clear", 0, 0, 0))
        self.assertIsNone(mlog.draw.clear(0, 0, 0))
        self.assertIsNone(mlog.draw.color(255, 255, 255, 255))
        self.assertIsNone(mlog.draw.col(12345))
        self.assertIsNone(mlog.draw.stroke(2))
        self.assertIsNone(mlog.draw.line(0, 0, 10, 10))
        self.assertIsNone(mlog.draw.rect(0, 0, 20, 20))
        self.assertIsNone(mlog.draw.line_rect(0, 0, 20, 20))
        self.assertIsNone(mlog.draw.lineRect(0, 0, 20, 20))
        self.assertIsNone(mlog.draw.poly(0, 0, 6, 10))
        self.assertIsNone(mlog.draw.line_poly(0, 0, 6, 10))
        self.assertIsNone(mlog.draw.linePoly(0, 0, 6, 10))
        self.assertIsNone(mlog.draw.triangle(0, 0, 10, 10, 20, 0))
        self.assertIsNone(mlog.draw.image(0, 0, "@copper"))
        self.assertIsNone(mlog.draw.print(0, 0))
        self.assertIsNone(mlog.draw.translate(10, 10))
        self.assertIsNone(mlog.draw.scale(2, 2))
        self.assertIsNone(mlog.draw.rotate(90))
        self.assertIsNone(mlog.draw.reset())
        self.assertIsNone(mlog.draw.flush("display1"))


if __name__ == "__main__":
    unittest.main()
