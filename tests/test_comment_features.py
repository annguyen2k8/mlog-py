"""Unit and regression tests for requested comment features:

1. `dest = getlink(index)` expression form (alongside statement form `getlink(dest, index)`).
2. `...` (Ellipsis) and `pass` statement support, with expression rejection for `...`.
3. `format(wScr, hScr, ...)` multi-argument formatting lowering to sequential `format` instructions.
4. `draw.print` text alignment support with `Align` enum, strings, numbers, and validation.
"""

import unittest

import src.metadata as metadata
import src.mlog as mlog
from src.errors import CompileError
from src.mlog import Align, compile_py
from src.mlog_registry import REG_ALIGN


class TestGetlinkSyntax(unittest.TestCase):
    """Test getlink expression and statement syntax."""

    def test_expression_form_lowering(self):
        code = "from mlog import getlink\nblock = getlink(0)\n"
        res = compile_py(code)
        self.assertEqual(res.mlog.strip(), "getlink block 0")

    def test_statement_form_lowering(self):
        code = "from mlog import getlink\ngetlink(block, 0)\n"
        res = compile_py(code)
        self.assertEqual(res.mlog.strip(), "getlink block 0")

    def test_expression_and_statement_forms_are_identical(self):
        res1 = compile_py("from mlog import getlink\nblock = getlink(i)\n")
        res2 = compile_py("from mlog import getlink\ngetlink(block, i)\n")
        self.assertEqual(res1.mlog.strip(), res2.mlog.strip())

    def test_expression_form_with_variable_index(self):
        code = "from mlog import getlink\nidx = 3\ncore = getlink(idx)\n"
        res = compile_py(code)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(lines[-1], "getlink core idx")

    def test_standalone_single_arg_without_dest_raises(self):
        code = "from mlog import getlink\ngetlink(0)\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("expected getlink(dest, index) or dest = getlink(index)", str(ctx.exception))

    def test_invalid_arity_zero_raises(self):
        code = "from mlog import getlink\ngetlink()\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("expected getlink(dest, index) or dest = getlink(index)", str(ctx.exception))

    def test_invalid_arity_three_raises(self):
        code = "from mlog import getlink\ngetlink(a, b, c)\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("expected getlink(dest, index) or dest = getlink(index)", str(ctx.exception))

    def test_runtime_helper_call(self):
        res1 = mlog.getlink(0)
        self.assertEqual(res1, 0)
        res2 = mlog.getlink("dest_block", 0)
        self.assertEqual(res2, 0)


class TestEllipsisAndPass(unittest.TestCase):
    """Test `...` (Ellipsis) and `pass` as statements and rejection of `...` as expressions."""

    def test_top_level_pass_and_ellipsis(self):
        code = "pass\n...\n"
        res = compile_py(code)
        self.assertEqual(res.mlog.strip(), "")

    def test_conditional_pass_and_ellipsis(self):
        code = (
            "x = 1\n"
            "if x == 1:\n"
            "    ...\n"
            "else:\n"
            "    pass\n"
        )
        res = compile_py(code)
        self.assertIn("jump", res.mlog)

    def test_loop_pass_and_ellipsis(self):
        code = (
            "for i in range(5):\n"
            "    pass\n"
            "while False:\n"
            "    ...\n"
        )
        res = compile_py(code)
        # Should compile without errors
        self.assertIsInstance(res.mlog, str)

    def test_function_body_pass_and_ellipsis(self):
        code = (
            "def stub_one():\n"
            "    ...\n"
            "def stub_two():\n"
            "    pass\n"
        )
        res = compile_py(code, allow_functions=True)
        self.assertIsInstance(res.mlog, str)

    def test_ellipsis_as_assignment_value_rejected(self):
        code = "x = ...\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("Ellipsis (...) is only supported as a placeholder statement", str(ctx.exception))

    def test_ellipsis_in_binary_op_rejected(self):
        code = "x = ... + 1\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("Ellipsis (...) is only supported as a placeholder statement", str(ctx.exception))

    def test_ellipsis_as_call_argument_rejected(self):
        snippets = [
            "print(...)\n",
            "from mlog import format\nformat(...)\n",
            "from mlog import getlink\nx = getlink(...)\n",
            "from mlog import draw\ndraw.color(..., 0, 0)\n",
        ]
        for snippet in snippets:
            with self.subTest(snippet=snippet):
                with self.assertRaises(CompileError) as ctx:
                    compile_py(snippet)
                self.assertIn("Ellipsis (...) is only supported as a placeholder statement", str(ctx.exception))

    def test_ellipsis_in_ternary_expressions_rejected(self):
        # BUG-02 regression tests: Ensure Ellipsis is rejected even when inside dead branches of ternary expressions
        ternary_cases = [
            ("y = 1 if True else ...\n", "ternary dead orelse branch with constant True"),
            ("z = ... if False else 1\n", "ternary dead body branch with constant False"),
            ("y = 1 if cond else ...\n", "ternary dynamic condition orelse branch"),
            ("z = ... if cond else 1\n", "ternary dynamic condition body branch"),
            ("a = (1 if True else ...) + 5\n", "ternary dead branch nested in binary op"),
            ("b = 2 * (... if False else 3)\n", "ternary dead branch nested in arithmetic"),
        ]
        for code, desc in ternary_cases:
            with self.subTest(case=desc):
                with self.assertRaises(CompileError) as ctx:
                    compile_py(code)
                self.assertIn("Ellipsis (...) is only supported as a placeholder statement", str(ctx.exception))

    def test_ellipsis_in_nested_expressions_rejected(self):
        nested_cases = [
            ("x = 1 + (2 * (... + 3))\n", "nested arithmetic expression"),
            ("while ...:\n    pass\n", "while condition expression"),
            ("if ...:\n    pass\n", "if condition expression"),
            ("sensor(..., '@health')\n", "sensor target expression"),
        ]
        for code, desc in nested_cases:
            with self.subTest(case=desc):
                with self.assertRaises(CompileError) as ctx:
                    compile_py(code)
                self.assertIn("Ellipsis (...) is only supported as a placeholder statement", str(ctx.exception))


class TestFormatMultiArgs(unittest.TestCase):
    """Test `format(val1, val2, ...)` multi-argument syntax and runtime buffer emulation."""

    def test_single_arg_format(self):
        code = "from mlog import format\nformat(42)\n"
        res = compile_py(code)
        self.assertEqual(res.mlog.strip(), "format 42")

    def test_two_args_format(self):
        code = "from mlog import format\nformat(wScr, hScr)\n"
        res = compile_py(code)
        expected = "format wScr\nformat hScr"
        self.assertEqual(res.mlog.strip(), expected)

    def test_many_args_format(self):
        code = "from mlog import format\nformat(1, 2, 3, 4)\n"
        res = compile_py(code)
        expected = "format 1\nformat 2\nformat 3\nformat 4"
        self.assertEqual(res.mlog.strip(), expected)

    def test_zero_arg_format_raises(self):
        code = "from mlog import format\nformat()\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("expected at least 1 value", str(ctx.exception))

    def test_runtime_format_buffer_emulation(self):
        metadata._rt_print_buffer.clear()
        mlog.print("Resolution: {0}x{1}, scale={2}")
        mlog.format(800, 600, 2)
        text = "".join(metadata._rt_print_buffer)
        self.assertEqual(text, "Resolution: 800x600, scale=2")

    def test_runtime_format_exceeding_placeholders(self):
        metadata._rt_print_buffer.clear()
        mlog.print("Single: {0}")
        mlog.format("first", "ignored_second")
        text = "".join(metadata._rt_print_buffer)
        self.assertEqual(text, "Single: first")

    def test_format_variadic_many_arguments(self):
        # Verify format supports any N >= 1 arguments, lowering sequentially to N format instructions
        args_str = ", ".join(f"val{i}" for i in range(12))
        code = f"from mlog import format\nformat({args_str})\n"
        res = compile_py(code)
        expected = "\n".join(f"format val{i}" for i in range(12))
        self.assertEqual(res.mlog.strip(), expected)

    def test_runtime_format_zero_arg_raises_type_error(self):
        # 0-arg format() at runtime raises TypeError matching standard Python call semantics
        with self.assertRaises(TypeError):
            metadata._rt_format()


class TestDrawPrintAlignEnum(unittest.TestCase):
    """Test `draw.print` text alignment Enum and token support."""

    def test_align_enum_members_exist(self):
        self.assertIn("Align", mlog.__all__)
        self.assertEqual(Align.CENTER.value, "@center")
        self.assertEqual(Align.TOP.value, "@top")
        self.assertEqual(Align.BOTTOM.value, "@bottom")
        self.assertEqual(Align.LEFT.value, "@left")
        self.assertEqual(Align.RIGHT.value, "@right")
        self.assertEqual(Align.TOP_LEFT.value, "@topLeft")
        self.assertEqual(Align.TOP_RIGHT.value, "@topRight")
        self.assertEqual(Align.BOTTOM_LEFT.value, "@bottomLeft")
        self.assertEqual(Align.BOTTOM_RIGHT.value, "@bottomRight")

    def test_align_enum_aliases(self):
        self.assertIs(Align.BOTTOM_LEFT, Align.BOTTOMLEFT)
        self.assertIs(Align.TOP_LEFT, Align.TOPLEFT)
        self.assertIs(Align.TOP_RIGHT, Align.TOPRIGHT)
        self.assertIs(Align.BOTTOM_RIGHT, Align.BOTTOMRIGHT)

    def test_draw_print_with_align_enum_positional(self):
        code = "from mlog import draw, Align\ndraw.print(0, 100, Align.BOTTOM_LEFT)\n"
        res = compile_py(code)
        self.assertEqual(res.mlog.strip(), "draw print 0 100 @bottomLeft 0 0 0")

    def test_draw_print_with_align_enum_keyword(self):
        code = "from mlog import draw, Align\ndraw.print(0, 100, align=Align.CENTER)\n"
        res = compile_py(code)
        self.assertEqual(res.mlog.strip(), "draw print 0 100 @center 0 0 0")

    def test_draw_print_with_string_align(self):
        code = 'from mlog import draw\ndraw.print(10, 20, "topRight")\n'
        res = compile_py(code)
        self.assertEqual(res.mlog.strip(), "draw print 10 20 @topRight 0 0 0")

    def test_draw_print_with_at_prefixed_string(self):
        code = 'from mlog import draw\ndraw.print(10, 20, "@center")\n'
        res = compile_py(code)
        self.assertEqual(res.mlog.strip(), "draw print 10 20 @center 0 0 0")

    def test_draw_print_with_numeric_align(self):
        # 12 is arc.util.Align.bottomLeft
        code = "from mlog import draw\ndraw.print(0, 100, 12)\n"
        res = compile_py(code)
        self.assertEqual(res.mlog.strip(), "draw print 0 100 12 0 0 0")

    def test_draw_print_default_align(self):
        code = "from mlog import draw\ndraw.print(0, 100)\n"
        res = compile_py(code)
        self.assertEqual(res.mlog.strip(), "draw print 0 100 0 0 0 0")

    def test_draw_print_invalid_align_string_raises(self):
        code = 'from mlog import draw\ndraw.print(0, 100, "middleSomewhere")\n'
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("unknown align 'middleSomewhere'", str(ctx.exception))

    def test_draw_print_invalid_keyword_raises(self):
        code = "from mlog import draw\ndraw.print(0, 100, foo=1)\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("unexpected keyword argument 'foo'", str(ctx.exception))

    def test_draw_print_all_canonical_aligns(self):
        expected_tokens = {
            Align.CENTER: "@center",
            Align.TOP: "@top",
            Align.BOTTOM: "@bottom",
            Align.LEFT: "@left",
            Align.RIGHT: "@right",
            Align.TOP_LEFT: "@topLeft",
            Align.TOP_RIGHT: "@topRight",
            Align.BOTTOM_LEFT: "@bottomLeft",
            Align.BOTTOM_RIGHT: "@bottomRight",
        }
        for enum_val, token in expected_tokens.items():
            with self.subTest(align=enum_val):
                code = f"from mlog import draw, Align\ndraw.print(0, 0, Align.{enum_val.name})\n"
                res = compile_py(code)
                self.assertEqual(res.mlog.strip(), f"draw print 0 0 {token} 0 0 0")


class TestDrawPrintDecompilerRoundtrip(unittest.TestCase):
    """Test roundtrip recovery of draw.print and Align enum (MLog -> Decompiler -> Python -> Compiler -> MLog)."""

    def test_roundtrip_all_nine_alignments(self):
        from src.decompiler import decompile
        expected_pairs = [
            ("@center", Align.CENTER),
            ("@top", Align.TOP),
            ("@bottom", Align.BOTTOM),
            ("@left", Align.LEFT),
            ("@right", Align.RIGHT),
            ("@topLeft", Align.TOP_LEFT),
            ("@topRight", Align.TOP_RIGHT),
            ("@bottomLeft", Align.BOTTOM_LEFT),
            ("@bottomRight", Align.BOTTOM_RIGHT),
        ]
        for token, enum_val in expected_pairs:
            with self.subTest(align=token):
                mlog_in = f"draw print 10 20 {token} 0 0 0\n"
                py_code = decompile(mlog_in)
                self.assertIn(f"draw.print(10, 20, Align.{enum_val.name})", py_code)
                self.assertIn("from mlog import Align, draw", py_code)
                recompiled = compile_py(py_code).mlog
                self.assertEqual(recompiled, mlog_in)

    def test_roundtrip_default_align_zero(self):
        from src.decompiler import decompile
        mlog_in = "draw print 10 20 0 0 0 0\n"
        py_code = decompile(mlog_in)
        self.assertIn("draw.print(10, 20)", py_code)
        recompiled = compile_py(py_code).mlog
        self.assertEqual(recompiled, mlog_in)

    def test_roundtrip_variable_align(self):
        from src.decompiler import decompile
        mlog_in = "draw print 10 20 my_align 0 0 0\n"
        py_code = decompile(mlog_in)
        self.assertIn("draw.print(10, 20, my_align)", py_code)
        recompiled = compile_py(py_code).mlog
        self.assertEqual(recompiled, mlog_in)

    def test_generic_draw_print_string_align_emits_unquoted_token(self):
        # Generic draw("print", 0, 0, "@bottomLeft", 0, 0, 0) should emit @bottomLeft without quotes
        code = 'from mlog import draw\ndraw("print", 0, 0, "@bottomLeft", 0, 0, 0)\n'
        res = compile_py(code)
        self.assertEqual(res.mlog.strip(), "draw print 0 0 @bottomLeft 0 0 0")

    def test_other_draw_commands_remain_standard_generic_draw(self):
        from src.decompiler import decompile
        mlog_in = "draw line 0 0 10 10 0 0\n"
        py_code = decompile(mlog_in)
        self.assertIn('draw("line", 0, 0, 10, 10, 0, 0)', py_code)
        recompiled = compile_py(py_code).mlog
        self.assertEqual(recompiled, mlog_in)


if __name__ == "__main__":
    unittest.main()
