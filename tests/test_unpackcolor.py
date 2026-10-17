"""Regression tests for `unpackcolor` tuple unpacking.

Mindustry lowering contract (core/src/mindustry/logic/LStatements.java
`UnpackColorStatement` + core/src/mindustry/logic/LExecutor.java `UnpackColorI`):

    unpackcolor <r> <g> <b> <a> <value>

Exactly 5 operands. Exactly 4 outputs, always written, in RGBA order. The engine reads
`value` into a local before writing `r`, so reusing the source variable as a target is
safe.

The DSL therefore offers two equivalent call conventions that must lower to the same
single instruction:

    1. Tuple unpacking form: r, g, b, a = unpackcolor(value)
    2. Statement form:        unpackcolor(r, g, b, a, value)
"""

import unittest

from src.errors import CompileError
from src.mlog import compile_py


class TestUnpackcolorTupleUnpacking(unittest.TestCase):
    """`r, g, b, a = unpackcolor(value)` lowers to the engine's 5-operand form."""

    def test_tuple_unpacking_lowers_to_single_instruction(self):
        src = (
            "from mlog import unpackcolor\n"
            "color = 12345\n"
            "r, g, b, a = unpackcolor(color)\n"
        )
        res = compile_py(src, filename="unpack.py")
        self.assertEqual(res.mlog.strip().splitlines()[-1], "unpackcolor r g b a color")

    def test_tuple_unpacking_and_statement_form_are_byte_identical(self):
        unpacked = compile_py(
            "from mlog import unpackcolor\nr, g, b, a = unpackcolor(color)\n",
            filename="a.py",
        )
        statement = compile_py(
            "from mlog import unpackcolor\nunpackcolor(r, g, b, a, color)\n",
            filename="b.py",
        )
        self.assertEqual(unpacked.mlog.strip(), statement.mlog.strip())
        self.assertEqual(unpacked.mlog.strip(), "unpackcolor r g b a color")

    def test_list_target_form_is_accepted(self):
        res = compile_py(
            'from mlog import unpackcolor\n[r, g, b, a] = unpackcolor("@color")\n',
            filename="unpack.py",
        )
        self.assertEqual(res.mlog.strip(), 'unpackcolor r g b a "@color"')

    def test_operand_order_follows_target_declaration_order(self):
        res = compile_py(
            "from mlog import unpackcolor\nred, green, blue, alpha = unpackcolor(team)\n",
            filename="unpack.py",
        )
        self.assertEqual(
            res.mlog.strip(), "unpackcolor red green blue alpha team"
        )

    def test_source_may_be_a_packcolor_result(self):
        res = compile_py(
            "from mlog import packcolor, unpackcolor\n"
            "packed = packcolor(0.25, 0.5, 0.75, 1.0)\n"
            "r, g, b, a = unpackcolor(packed)\n",
            filename="unpack.py",
        )
        lines = res.mlog.strip().splitlines()
        self.assertEqual(lines[0], "packcolor packed 0.25 0.5 0.75 1.0")
        self.assertEqual(lines[1], "unpackcolor r g b a packed")

    def test_source_may_be_a_sensor_result(self):
        res = compile_py(
            "from mlog import sensor, unpackcolor\n"
            "c = sensor(\"@unit\", \"@color\")\n"
            "r, g, b, a = unpackcolor(c)\n",
            filename="unpack.py",
        )
        self.assertIn("unpackcolor r g b a c", res.mlog)

    def test_source_may_be_reused_as_first_target(self):
        """Engine reads `value` before writing outputs, so aliasing the source is safe."""
        res = compile_py(
            "from mlog import unpackcolor\ncolor, g, b, a = unpackcolor(color)\n",
            filename="unpack.py",
        )
        self.assertEqual(res.mlog.strip(), "unpackcolor color g b a color")

    def test_target_may_overwrite_existing_variables(self):
        res = compile_py(
            "from mlog import unpackcolor\n"
            "r = 0\n"
            "g = 0\n"
            "b = 0\n"
            "a = 0\n"
            "r, g, b, a = unpackcolor(color)\n",
            filename="unpack.py",
        )
        self.assertEqual(
            res.mlog.strip().splitlines()[-1], "unpackcolor r g b a color"
        )

    def test_unpacking_inside_loop_and_conditionals(self):
        src = (
            "from mlog import unpackcolor\n"
            "for i in range(4):\n"
            "    if i > 1:\n"
            "        r, g, b, a = unpackcolor(color)\n"
            "        print(r)\n"
        )
        res = compile_py(src, filename="unpack.py")
        self.assertIn("unpackcolor r g b a color", res.mlog)

    def test_unpacking_inside_function_body(self):
        src = (
            "from mlog import unpackcolor\n"
            "def show(color):\n"
            "    r, g, b, a = unpackcolor(color)\n"
            "    return r\n"
            "out = show(1)\n"
        )
        res = compile_py(src, filename="unpack.py", allow_functions=True)
        self.assertIn("unpackcolor r g b a color", res.mlog)

    # -----------------------------------------------------------------------
    # Error handling
    # -----------------------------------------------------------------------

    def test_too_few_targets_rejected(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py(
                "from mlog import unpackcolor\nr, g, b = unpackcolor(color)\n",
                filename="unpack.py",
            )
        self.assertIn("expects exactly 4 target variables", str(ctx.exception))
        self.assertIn("got 3", str(ctx.exception))

    def test_too_many_targets_rejected(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py(
                "from mlog import unpackcolor\nr, g, b, a, extra = unpackcolor(color)\n",
                filename="unpack.py",
            )
        self.assertIn("expects exactly 4 target variables", str(ctx.exception))
        self.assertIn("got 5", str(ctx.exception))

    def test_duplicate_target_names_rejected(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py(
                "from mlog import unpackcolor\nr, g, b, r = unpackcolor(color)\n",
                filename="unpack.py",
            )
        self.assertIn("duplicate variable name 'r'", str(ctx.exception))

    def test_multiple_source_arguments_rejected(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py(
                "from mlog import unpackcolor\nr, g, b, a = unpackcolor(color, extra)\n",
                filename="unpack.py",
            )
        self.assertIn("expected unpackcolor(value), got 2 arguments", str(ctx.exception))

    def test_zero_source_arguments_rejected(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py(
                "from mlog import unpackcolor\nr, g, b, a = unpackcolor()\n",
                filename="unpack.py",
            )
        self.assertIn("expected unpackcolor(value), got 0 arguments", str(ctx.exception))

    def test_keyword_arguments_rejected(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py(
                "from mlog import unpackcolor\nr, g, b, a = unpackcolor(value=color)\n",
                filename="unpack.py",
            )
        self.assertIn("keyword", str(ctx.exception).lower())

    def test_single_target_assignment_rejected(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py(
                "from mlog import unpackcolor\nx = unpackcolor(color)\n",
                filename="unpack.py",
            )
        self.assertIn(
            "unpackcolor(r, g, b, a, value) or r, g, b, a = unpackcolor(value)",
            str(ctx.exception),
        )

    def test_expression_use_rejected(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py(
                "from mlog import unpackcolor\nx = unpackcolor(color) + 1\n",
                filename="unpack.py",
            )
        self.assertIn(
            "unpackcolor(r, g, b, a, value) or r, g, b, a = unpackcolor(value)",
            str(ctx.exception),
        )

    def test_bare_statement_use_rejected(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py(
                "from mlog import unpackcolor\nunpackcolor(color)\n",
                filename="unpack.py",
            )
        self.assertIn("invalid arguments for unpackcolor", str(ctx.exception))

    def test_tuple_unpacking_still_rejects_non_supported_calls(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py(
                "from mlog import sensor\na, b = sensor(\"@unit\", \"@health\")\n",
                filename="unpack.py",
            )
        self.assertIn("tuple unpacking is only supported", str(ctx.exception))

    def test_non_name_targets_rejected(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py(
                "from mlog import unpackcolor\nr, g, b, arr[0] = unpackcolor(color)\n",
                filename="unpack.py",
            )
        self.assertIn("simple variable names", str(ctx.exception))


class TestUnpackcolorPurePythonRuntime(unittest.TestCase):
    """The plain-Python runtime stub must support the tuple unpacking form."""

    def test_single_argument_form_returns_four_tuple(self):
        from mlog import ColorChannels, unpackcolor

        result = unpackcolor(12345)
        self.assertIsInstance(result, ColorChannels)
        self.assertEqual(len(result), 4)
        r, g, b, a = result
        self.assertEqual((r, g, b, a), (0.0, 0.0, 0.0, 0.0))

    def test_field_names_follow_rgba_order(self):
        from mlog import unpackcolor

        self.assertEqual(tuple(unpackcolor(1)._fields), ("r", "g", "b", "a"))

    def test_statement_form_is_a_noop(self):
        from mlog import unpackcolor

        self.assertIsNone(unpackcolor(1, 2, 3, 4, 5))

    def test_tuple_unpacking_statement_runs_in_pure_python(self):
        from mlog import unpackcolor

        color = 999
        r, g, b, a = unpackcolor(color)
        self.assertEqual((r, g, b, a), (0.0, 0.0, 0.0, 0.0))


class TestUnpackcolorDecompilerRoundtrip(unittest.TestCase):
    """The engine instruction form must survive mlog -> Python -> mlog unchanged."""

    def test_unpackcolor_instruction_roundtrips_byte_for_byte(self):
        from src.decompiler import decompile

        mlog = "unpackcolor r g b a col\n"
        py = decompile(mlog, filename="t.mlog")
        recompiled = compile_py(py, filename="t.py").mlog
        self.assertEqual(recompiled.strip(), mlog.strip())

    def test_packcolor_then_unpackcolor_roundtrips_byte_for_byte(self):
        from src.decompiler import decompile

        mlog = "packcolor col 1 0 0 1\nunpackcolor r g b a col\n"
        py = decompile(mlog, filename="t.mlog")
        recompiled = compile_py(py, filename="t.py").mlog
        self.assertEqual(recompiled.strip(), mlog.strip())

    def test_tuple_unpacking_form_and_decompiled_form_are_equivalent(self):
        from src.decompiler import decompile

        unpacked = compile_py(
            "from mlog import unpackcolor\nr, g, b, a = unpackcolor(col)\n",
            filename="a.py",
        ).mlog
        statement = compile_py(
            decompile("unpackcolor r g b a col\n", filename="t.mlog"),
            filename="b.py",
        ).mlog
        self.assertEqual(unpacked.strip(), statement.strip())


class TestUnpackcolorRepositoryExample(unittest.TestCase):
    """The shipped example must stay byte-for-byte reproducible."""

    def test_color_channels_example_is_byte_for_byte_reproducible(self):
        import os

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        py_path = os.path.join(repo_root, "examples", "compiler", "color_channels.py")
        mlog_path = os.path.join(repo_root, "examples", "compiler", "color_channels.mlog")

        with open(py_path, "r", encoding="utf-8") as f:
            source = f.read()
        with open(mlog_path, "r", encoding="utf-8") as f:
            expected = f.read()

        res = compile_py(source, filename="color_channels.py")
        self.assertEqual(res.mlog.strip(), expected.strip())


if __name__ == "__main__":
    unittest.main()