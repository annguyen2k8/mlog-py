"""Comprehensive regression tests for ADR-001 modulo semantics (% and emod).

Verifies compiler lowering, constant folding, decompiler round-trip,
and runtime execution on real Mindustry v8 engine classes.
"""

import ast
import unittest

from src.compiler import CompileError
from src.decompiler import decompile
from src.mindustry_validator import is_mindustry_available, run_with_mindustry
from src.mlog import compile_py


class TestModuloCompilerLowering(unittest.TestCase):
    """Verify % and %= lower to canonical v8 op emod, while op() intrinsic preserves op mod."""

    def test_binary_modulo_lowering(self):
        """Python x = a % b lowers to op emod."""
        res = compile_py("x = a % b")
        self.assertEqual(res.mlog.strip(), "op emod x a b")

    def test_aug_assign_modulo_lowering(self):
        """Python x %= b lowers to op emod x x b."""
        res = compile_py("x = 10\nx %= b")
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        self.assertIn("op emod x x b", lines)

    def test_array_modulo_aug_assign_lowering(self):
        """Array element modulo augmented assignment lowers to emod."""
        source = """
from mlog import Array
arr = Array("cell1", 10)
arr[2] %= 5
"""
        res = compile_py(source)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        self.assertTrue(any("op emod" in l for l in lines), f"Expected op emod in {lines}")

    def test_direct_intrinsic_op_mod_preserved(self):
        """Direct op('mod', ...) intrinsic retains op mod for C/Java truncated remainder."""
        res1 = compile_py('op("mod", d, a, b)')
        self.assertEqual(res1.mlog.strip(), "op mod d a b")

        res2 = compile_py('d = op("mod", a, b)')
        self.assertEqual(res2.mlog.strip(), "op mod d a b")

    def test_direct_intrinsic_op_emod_supported(self):
        """Direct op('emod', ...) intrinsic produces op emod."""
        res1 = compile_py('op("emod", d, a, b)')
        self.assertEqual(res1.mlog.strip(), "op emod d a b")

        res2 = compile_py('d = op("emod", a, b)')
        self.assertEqual(res2.mlog.strip(), "op emod d a b")


class TestModuloConstantFolding(unittest.TestCase):
    """Verify compile-time constant folding for % conforms to Python floored semantics."""

    def test_positive_integers_folded(self):
        res = compile_py("x = 7 % 3")
        self.assertIn("set x 1", res.mlog)
        self.assertNotIn("op emod", res.mlog)

    def test_negative_dividend_folded(self):
        """-7 % 3 == 2 in Python; folds to 2 (matches Mindustry emod)."""
        res = compile_py("x = -7 % 3")
        self.assertIn("set x 2", res.mlog)
        self.assertNotIn("op emod", res.mlog)

    def test_negative_divisor_folded(self):
        """7 % -3 == -2 in Python; folds to -2 (matches Mindustry emod)."""
        res = compile_py("x = 7 % -3")
        self.assertIn("set x -2", res.mlog)
        self.assertNotIn("op emod", res.mlog)

    def test_both_negative_folded(self):
        """-7 % -3 == -1 in Python; folds to -1 (matches Mindustry emod)."""
        res = compile_py("x = -7 % -3")
        self.assertIn("set x -1", res.mlog)
        self.assertNotIn("op emod", res.mlog)

    def test_float_modulo_folded(self):
        """Floating point modulo matches Python IEEE-754 precision."""
        res1 = compile_py("x = 7.5 % 3.0")
        self.assertIn("set x 1.5", res1.mlog)

        res2 = compile_py("x = -7.5 % 3.0")
        self.assertIn("set x 1.5", res2.mlog)

        res3 = compile_py("x = 7.5 % -3.0")
        self.assertIn("set x -1.5", res3.mlog)

    def test_zero_dividend_folded(self):
        res = compile_py("x = 0 % 3")
        self.assertIn("set x 0", res.mlog)

    def test_literal_modulo_by_zero_raises_compile_error(self):
        """Constant division or modulo by literal zero is rejected with CompileError."""
        with self.assertRaises(CompileError) as ctx1:
            compile_py("x = 7 % 0")
        self.assertIn("modulo by zero", str(ctx1.exception))

        with self.assertRaises(CompileError) as ctx2:
            compile_py("x = -7 % 0")
        self.assertIn("modulo by zero", str(ctx2.exception))

        with self.assertRaises(CompileError) as ctx3:
            compile_py("x = 7.5 % 0.0")
        self.assertIn("modulo by zero", str(ctx3.exception))

        with self.assertRaises(CompileError) as ctx4:
            compile_py("x = 0 % 0")
        self.assertIn("modulo by zero", str(ctx4.exception))

    def test_runtime_unfolded_when_optimizer_disabled(self):
        """When fold_constants=False, negative modulo generates op emod."""
        res = compile_py("x = -7 % 3", fold_constants=False)
        self.assertIn("op emod", res.mlog)


class TestModuloDecompilerRoundTrip(unittest.TestCase):
    """Verify decompiler converts emod to % and preserves mod as op('mod', ...)."""

    def test_decompile_emod_to_python_operator(self):
        mlog = "op emod res a b\n"
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("res = a % b", py)

    def test_decompile_legacy_mod_to_intrinsic(self):
        mlog = "op mod res a b\n"
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn('res = op("mod", a, b)', py)

    def test_roundtrip_python_modulo(self):
        source = "x = a % b\n"
        compiled = compile_py(source)
        self.assertIn("op emod x a b", compiled.mlog)

        decompiled = decompile(compiled.mlog)
        ast.parse(decompiled)
        self.assertIn("x = a % b", decompiled)

        recompiled = compile_py(decompiled)
        self.assertEqual(compiled.mlog.strip(), recompiled.mlog.strip())

    def test_roundtrip_legacy_op_mod(self):
        mlog = 'op mod x a b\n'
        decompiled = decompile(mlog)
        ast.parse(decompiled)
        self.assertIn('x = op("mod", a, b)', decompiled)

        recompiled = compile_py(decompiled)
        self.assertEqual(mlog.strip(), recompiled.mlog.strip())


class TestModuloEngineExecution(unittest.TestCase):
    """Execute compiled instructions directly inside Mindustry v8 JVM runtime."""

    @unittest.skipUnless(is_mindustry_available(), "Mindustry runtime classpath not available")
    def test_engine_emod_execution(self):
        mlog_code = """
op emod pos 7 3
op emod neg_div -7 3
op emod neg_divs 7 -3
op emod both_neg -7 -3
op emod float_pos 7.5 3.0
op emod float_neg -7.5 3.0
op emod float_neg_divs 7.5 -3.0
op emod zero_div 7 0
"""
        ok, res, msg = run_with_mindustry(mlog_code)
        self.assertTrue(ok, f"Harness run failed: {msg}")

        self.assertEqual(res.get("pos"), 1.0)
        self.assertEqual(res.get("neg_div"), 2.0)
        self.assertEqual(res.get("neg_divs"), -2.0)
        self.assertEqual(res.get("both_neg"), -1.0)
        self.assertEqual(res.get("float_pos"), 1.5)
        self.assertEqual(res.get("float_neg"), 1.5)
        self.assertEqual(res.get("float_neg_divs"), -1.5)
        self.assertEqual(res.get("zero_div"), "null")

    @unittest.skipUnless(is_mindustry_available(), "Mindustry runtime classpath not available")
    def test_engine_mod_execution(self):
        mlog_code = """
op mod pos 7 3
op mod neg_div -7 3
op mod neg_divs 7 -3
op mod both_neg -7 -3
op mod zero_div 7 0
"""
        ok, res, msg = run_with_mindustry(mlog_code)
        self.assertTrue(ok, f"Harness run failed: {msg}")

        self.assertEqual(res.get("pos"), 1.0)
        self.assertEqual(res.get("neg_div"), -1.0)
        self.assertEqual(res.get("neg_divs"), 1.0)
        self.assertEqual(res.get("both_neg"), -1.0)
        self.assertEqual(res.get("zero_div"), "null")


if __name__ == "__main__":
    unittest.main()
