"""Regression tests for dataflow expression recovery, constant folding, and alias elimination.

Covers:
- Safe inline of single-use compiler temporaries (__tmpN) in nested operations
- Elimination of redundant alias assignments (e.g. b = g) replaced with direct references
- Preservation of meaningful user variables (wScr, hScr, r, g, x, y, size)
- Unsafe inline prevention: intervening variable overwrite
- Unsafe inline prevention: multiple uses of temporaries or aliases
- Unsafe inline prevention: side effects
- Constant folding for basic arithmetic, bitwise operations, and logic intrinsics
- Safe division handling: division by zero, non-exact fractions
- Full round-trip compilation and decompilation using render.mlog as fixture
"""

import unittest
from pathlib import Path

from src.decompiler import decompile
from src.mlog import compile_py

_FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestDecompilerDataflowAlias(unittest.TestCase):
    """Dataflow expression recovery and alias elimination test suite."""

    def test_render_mlog_fixture_alias_elimination_and_variable_preservation(self):
        """Fixture render.mlog: b = g alias eliminated, meaningful variables preserved."""
        render_path = _FIXTURES / "render.mlog"
        self.assertTrue(render_path.is_file(), f"Missing fixture: {render_path}")

        with open(render_path, "r", encoding="utf-8") as f:
            mlog_code = f.read()

        py_code = decompile(mlog_code)

        # 1. Alias 'b = g' must be eliminated
        self.assertNotIn("b = g", py_code)

        # 2. Direct reference in draw color: 'draw.color(r, g, g)'
        self.assertIn("draw.color(r, g, g)", py_code)


        # 3. Meaningful variables must NOT be renamed or merged away
        self.assertIn("wScr = sensor(", py_code)
        self.assertIn("hScr = sensor(", py_code)
        self.assertIn("size = 4", py_code)
        self.assertIn("x = 0", py_code)
        self.assertIn("y = 0", py_code)
        self.assertIn("r = 255 * y / hScr", py_code)
        self.assertIn("g = (1 - x / wScr) * r", py_code)

        # 4. Control flow structure must remain intact
        self.assertIn("while True:", py_code)
        self.assertIn("break", py_code)
        self.assertNotIn("[UNSTRUCTURED REGION]", py_code)

        # 5. Roundtrip compilation: must compile successfully to mlog
        res = compile_py(py_code, allow_functions=False, validate=True)
        self.assertTrue(len(res.mlog.strip().splitlines()) > 0)
        self.assertIn("draw color r g g 255 0 0", res.mlog)

    def test_safe_temporary_inlining_nested_operations(self):
        """Chained arithmetic ops using single-use temporaries produce clean nested expressions."""
        mlog = (
            "op add __tmp0 a b\n"
            "op mul __tmp1 __tmp0 c\n"
            "op div res __tmp1 d\n"
        )
        py = decompile(mlog)
        self.assertNotIn("__tmp0", py)
        self.assertNotIn("__tmp1", py)
        self.assertIn("res = (a + b) * c / d", py)

    def test_constant_folding_basic_arithmetic(self):
        """Constant folding reduces compile-time literal math to evaluated constants."""
        mlog = (
            "op add a 10 20\n"
            "op mul b 5 6\n"
            "op sub c 100 25\n"
            "op idiv d 50 7\n"
            "op emod e 50 7\n"
        )
        py = decompile(mlog)
        self.assertIn("a = 30", py)
        self.assertIn("b = 30", py)
        self.assertIn("c = 75", py)
        self.assertIn("d = 7", py)
        self.assertIn("e = 1", py)

    def test_constant_folding_bitwise_and_powers(self):
        """Constant folding handles bitwise shifts, logic, and exponentiation."""
        mlog = (
            "op shl a 1 4\n"
            "op shr b 32 2\n"
            "op and c 15 9\n"
            "op or d 10 5\n"
            "op xor e 12 6\n"
            "op pow f 2 5\n"
        )
        py = decompile(mlog)
        self.assertIn("a = 16", py)
        self.assertIn("b = 8", py)
        self.assertIn("c = 9", py)
        self.assertIn("d = 15", py)
        self.assertIn("e = 10", py)
        self.assertIn("f = 32", py)

    def test_constant_folding_through_inlined_temporaries(self):
        """Temporaries holding constants fold cleanly into subsequent operations."""
        mlog = (
            "op mul __tmp0 5 4\n"
            "op add res __tmp0 3\n"
        )
        py = decompile(mlog)
        self.assertNotIn("__tmp0", py)
        self.assertIn("res = 23", py)

    def test_constant_folding_exact_division(self):
        """Exact division folds cleanly to an integer result."""
        mlog = "op div res 20 4\n"
        py = decompile(mlog)
        self.assertIn("res = 5", py)

    def test_constant_folding_preserves_non_exact_fractions(self):
        """Non-exact divisions (e.g. 1 / 3) are preserved as expressions for readability."""
        mlog = "op div res 1 3\n"
        py = decompile(mlog)
        self.assertIn("res = 1 / 3", py)
        self.assertNotIn("0.3333333333333333", py)

    def test_constant_folding_division_by_zero_safety(self):
        """Division by zero does not crash or raise exceptions, keeping expression intact."""
        mlog = "op div res 10 0\n"
        py = decompile(mlog)
        self.assertIn("res = 10 / 0", py)

    def test_unsafe_inline_intervening_overwrite_prevents_inlining(self):
        """If the source variable is modified before the alias is read, inlining is forbidden."""
        mlog = (
            "set a 10\n"
            "set b a\n"
            "set a 20\n"
            "print b\n"
        )
        py = decompile(mlog)
        # 'b = a' must be kept because 'a' is overwritten before 'print(b)'
        self.assertIn("b = a", py)
        self.assertIn("a = 20", py)
        self.assertIn("print(b)", py)

    def test_unsafe_inline_multiple_uses_of_alias_prevents_removal(self):
        """If an alias is used more than once, it is retained to avoid altering variable bindings."""
        mlog = (
            "set b g\n"
            "draw color r g b 255 0 0\n"
            "draw color 0 0 b 255 0 0\n"
        )
        py = decompile(mlog)
        self.assertIn("b = g", py)
        self.assertEqual(py.count("b"), 3)  # b = g, and twice in draw

    def test_unsafe_inline_multiple_uses_of_temporary_retains_definition(self):
        """If a temporary is used multiple times, it is not duplicated across expressions."""
        mlog = (
            "op add __tmp0 x 1\n"
            "op mul y __tmp0 2\n"
            "op mul z __tmp0 3\n"
        )
        py = decompile(mlog)
        # Should not inline (x + 1) twice
        self.assertIn("tmp_val_0 = x + 1", py)
        self.assertIn("y = tmp_val_0 * 2", py)
        self.assertIn("z = tmp_val_0 * 3", py)

    def test_meaningful_variables_never_merged(self):
        """Variables representing domain data are never inlined into subsequent computations."""
        mlog = (
            "op div r y hScr\n"
            "op mul g r 2\n"
        )
        py = decompile(mlog)
        # 'r' must not be eliminated into 'g = (y / hScr) * 2'
        self.assertIn("r = y / hScr", py)
        self.assertIn("g = r * 2", py)


if __name__ == "__main__":
    unittest.main()
