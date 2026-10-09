"""Unit and regression tests for Python min(a, b) and max(a, b) support.

Covers:
- Basic compilation of min(a, b) and max(a, b) to 'op min' / 'op max'.
- Constant expressions: no compile-time folding of Python min/max, preserves MLog runtime semantics.
- Argument validation: exactly 2 arguments required.
- User-defined function precedence: local/user functions shadow intrinsic min/max.
- Nested expressions: min(a, max(b, c)), max(min(x, y), z).
- Safe temporary inlining / data-flow validation (single-use vs multi-use vs intervening mutation).
- Variable shadowing and in-place reassignment: x = min(x, 10).
- Control flow usage: inside 'if' conditions, 'while' loops.
- Decompiler recovery: op min / op max -> min(a, b) / max(a, b).
- Round-trip fidelity: Python -> MLog -> Python -> MLog.
- Mindustry real Java engine validation via MindustryHarness if available.
"""

import ast
import unittest

from src.compiler import CompileError
from src.decompiler import decompile
from src.mlog import compile_py
from src.mindustry_validator import is_mindustry_available, validate_with_mindustry


class TestMinMaxCompiler(unittest.TestCase):
    """Compiler test suite for min() and max() intrinsics."""

    def test_basic_min_max_compilation(self):
        code = """
x = min(a, b)
y = max(c, d)
"""
        res = compile_py(code)
        self.assertIn("op min x a b", res.mlog)
        self.assertIn("op max y c d", res.mlog)

    def test_constant_expressions_not_evaluated_at_compile_time(self):
        """Must emit MLog op min/max instead of folding constants at compile time."""
        code = """
res1 = min(10, 20)
res2 = max(50, 100)
"""
        res = compile_py(code)
        # Should NOT evaluate to set res1 10 or set res2 100
        self.assertIn("op min res1 10 20", res.mlog)
        self.assertIn("op max res2 50 100", res.mlog)

    def test_argument_count_validation(self):
        """MLog op min/max takes exactly 2 arguments; single or 3+ args should fail."""
        with self.assertRaises(CompileError) as ctx:
            compile_py("x = min(a)")
        self.assertIn("takes exactly 2 arguments", str(ctx.exception))

        with self.assertRaises(CompileError) as ctx:
            compile_py("x = min(a, b, c)")
        self.assertIn("takes exactly 2 arguments", str(ctx.exception))

        with self.assertRaises(CompileError) as ctx:
            compile_py("y = max()")
        self.assertIn("takes exactly 2 arguments", str(ctx.exception))

    def test_user_defined_function_precedence(self):
        """User defined min/max functions must take precedence over built-in intrinsics."""
        code = """
def min(x, y):
    if x < y:
        return x
    return y

z = min(10, 20)
"""
        res = compile_py(code, allow_functions=True)
        # Should compile user function call, NOT emit 'op min'
        self.assertNotIn("op min", res.mlog)
        self.assertIn("__retval_min", res.mlog)

    def test_nested_expressions_compilation(self):
        code = """
val = min(a, max(b, c))
"""
        res = compile_py(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines() if line.strip()]
        # First op max __tmp0 b c, then op min val a __tmp0
        max_idx = next(i for i, line in enumerate(lines) if line.startswith("op max"))
        min_idx = next(i for i, line in enumerate(lines) if line.startswith("op min"))
        self.assertLess(max_idx, min_idx)
        self.assertIn("val", lines[min_idx])

    def test_variable_reassignment(self):
        code = """
x = 10
x = min(x, 5)
x = max(0, x)
"""
        res = compile_py(code)
        self.assertIn("op min x x 5", res.mlog)
        self.assertIn("op max x 0 x", res.mlog)

    def test_control_flow_conditions(self):
        code = """
if min(a, b) > 10:
    c = 1
while max(x, y) < 100:
    x = x + 1
"""
        res = compile_py(code)
        self.assertIn("op min", res.mlog)
        self.assertIn("op max", res.mlog)
        self.assertIn("jump", res.mlog)


class TestMinMaxDecompiler(unittest.TestCase):
    """Decompiler test suite for op min and op max."""

    def test_basic_op_min_max_recovery(self):
        mlog = """
op min res1 a b
op max res2 c d
"""
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("res1 = min(a, b)", py)
        self.assertIn("res2 = max(c, d)", py)
        # min/max are Python builtins, no import header should be generated
        self.assertNotIn("from mlog", py)

    def test_operand_order_preservation(self):
        mlog = """
op min r1 100 x
op max r2 y 50
"""
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("r1 = min(100, x)", py)
        self.assertIn("r2 = max(y, 50)", py)

    def test_nested_expression_recovery(self):
        """Temporary variables used once immediately should collapse into nested min/max."""
        mlog = """
op max __tmp0 b c
op min val a __tmp0
"""
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("val = min(a, max(b, c))", py)
        self.assertNotIn("__tmp0", py)

    def test_no_inline_on_multi_use(self):
        """If a temporary variable is used multiple times, it must NOT be inlined."""
        mlog = """
op min t a b
op add r1 t 10
op add r2 t 20
"""
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("t = min(a, b)", py)
        self.assertIn("r1 = t + 10", py)
        self.assertIn("r2 = t + 20", py)

    def test_no_inline_on_intervening_write(self):
        """If an operand is modified between definition and use, do NOT collapse."""
        mlog = """
op min t a b
set a 99
op add res t a
"""
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("t = min(a, b)", py)
        self.assertIn("a = 99", py)
        self.assertIn("res = t + a", py)

    def test_inlined_in_loop_condition(self):
        """Min/max temporaries should be inlined into loop headers safely."""
        mlog = """
set x 0
op min __tmp0 x 10
jump 5 greaterThanEq __tmp0 10
op add x x 1
jump 1 always 0 0
"""
        py = decompile(mlog)
        ast.parse(py)
        # Should be a while loop with min(x, 10) in condition
        self.assertIn("while min(x, 10) < 10:", py)


class TestMinMaxRoundTripAndEngine(unittest.TestCase):
    """End-to-end roundtrip and Mindustry engine validation."""

    def test_roundtrip_simple(self):
        original_py = "res = min(a, max(b, c))\n"
        compiled = compile_py(original_py)
        decompiled = decompile(compiled.mlog)
        ast.parse(decompiled)
        self.assertIn("res = min(a, max(b, c))", decompiled)

        # Recompile second time
        recompiled = compile_py(decompiled)
        self.assertEqual(compiled.mlog.strip(), recompiled.mlog.strip())

    def test_roundtrip_with_clamping_idiom(self):
        py_code = """
clamped = max(0, min(val, 100))
"""
        compiled = compile_py(py_code)
        decompiled = decompile(compiled.mlog)
        ast.parse(decompiled)
        self.assertIn("clamped = max(0, min(val, 100))", decompiled)

    def test_mindustry_engine_validation(self):
        """Verify generated MLog bytecode parses and runs cleanly against the official Mindustry parser/engine."""
        if not is_mindustry_available():
            self.skipTest("Mindustry harness not available in this environment")

        py_code = """
a = 15
b = 42
c = min(a, b)
d = max(a, b)
e = min(100, max(0, c))
"""
        res = compile_py(py_code)
        ok, msg, count = validate_with_mindustry(res.mlog)
        self.assertTrue(ok, f"Mindustry parser validation failed: {msg}")
        self.assertGreaterEqual(count, 5)


if __name__ == "__main__":
    unittest.main()
