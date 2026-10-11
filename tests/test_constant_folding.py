"""Tests for compile-time constant folding in Python DSL -> MLog compiler.

Validates that:
- Pure constant expressions (+, -, *, /, //, %, **, &, |, ^, <<, >>) are folded at compile time.
- Comparison expressions (==, !=, <, <=, >, >=) on constants are folded to boolean values.
- Boolean operations (and, or, not) on constants are folded.
- String concatenation with '+' on string literals is folded.
- Safe boundaries are respected:
  - Division by zero is deferred to runtime.
  - Modulo with negative operands is deferred to runtime (Mindustry/Python divergence).
  - Integer boundaries (IEEE-754 safe range 2^53 - 1) are preserved.
  - Shift counts >= 64 or negative are skipped.
  - Intrinsics min() and max() are NOT folded (emitted as op min/max).
  - Standalone unary minus (-x) and bitwise not (~x) preserve native instruction emission.
- Array static size (Array("cell1", size=4 * 4)) and subscript bounds checks (arr[1 + 2])
  resolve folded constants at compile time.
- Dead code elimination is strictly NOT implemented (all control flow branches are preserved).
- The fold_constants toggle and CLI flag '--no-fold-constants' properly disable folding.
- Mindustry LExecutor runtime execution matches expected results.
"""

import io
import math
import sys
import tempfile
import unittest
from pathlib import Path

from src.compiler import (
    Compiler,
    CompileError,
    ConstantFolder,
    fold_constants,
    compile_source_to_ir,
    MAX_SAFE_INT,
    MIN_SAFE_INT,
)
from src.mlog import compile_py, main
from src.optimizer import ConstantFolder as OptConstantFolder, fold_constants as opt_fold_constants
from src.mindustry_validator import (
    is_mindustry_available,
    run_with_mindustry,
    validate_with_mindustry,
)


class TestArithmeticConstantFolding(unittest.TestCase):
    """Test folding of arithmetic operations on numeric and string literals."""

    def test_basic_arithmetic_folding(self):
        code = """
a = 10 + 25
b = 50 - 15
c = 6 * 7
d = 100 / 4
e = 7 // 2
f = 10 % 3
g = 2 ** 5
"""
        res = compile_py(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        self.assertIn("set a 35", lines)
        self.assertIn("set b 35", lines)
        self.assertIn("set c 42", lines)
        self.assertIn("set d 25.0", lines)
        self.assertIn("set e 3", lines)
        self.assertIn("set f 1", lines)
        self.assertIn("set g 32", lines)

        # Ensure no runtime arithmetic ops were generated
        for op in ("add", "sub", "mul", "div", "idiv", "mod", "emod", "pow"):
            for line in lines:
                self.assertFalse(line.startswith(f"op {op}"), f"Unexpected opcode 'op {op}' in: {line}")

    def test_float_arithmetic_folding(self):
        code = """
x = 1.5 + 2.5
y = 10.0 / 4.0
z = 2.5 * 4.0
w = 7.5 // 2.0
"""
        res = compile_py(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        self.assertIn("set x 4.0", lines)
        self.assertIn("set y 2.5", lines)
        self.assertIn("set z 10.0", lines)
        self.assertIn("set w 3.0", lines)

    def test_string_concatenation_folding(self):
        code = 'msg = "hello " + "world"'
        res = compile_py(code)
        self.assertIn('set msg "hello world"', res.mlog)
        self.assertNotIn("op add", res.mlog)

    def test_nested_arithmetic_folding(self):
        code = "res = (2 + 3) * (10 - 4) + 10 // 2"
        res = compile_py(code)
        # (5) * (6) + 5 = 30 + 5 = 35
        self.assertIn("set res 35", res.mlog)
        self.assertNotIn("op", res.mlog)

    def test_arithmetic_with_negative_literals(self):
        code = """
x = 5 + (-3)
y = (-10) * 3
z = (-8) // 2
"""
        res = compile_py(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        self.assertIn("set x 2", lines)
        self.assertIn("set y -30", lines)
        self.assertIn("set z -4", lines)


class TestBitwiseConstantFolding(unittest.TestCase):
    """Test folding of bitwise operations."""

    def test_bitwise_operators(self):
        code = """
a = 15 & 7
b = 8 | 3
c = 15 ^ 5
d = 1 << 4
e = 64 >> 2
"""
        res = compile_py(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        self.assertIn("set a 7", lines)
        self.assertIn("set b 11", lines)
        self.assertIn("set c 10", lines)
        self.assertIn("set d 16", lines)
        self.assertIn("set e 16", lines)

        for op in ("and", "or", "xor", "shl", "shr"):
            for line in lines:
                self.assertFalse(line.startswith(f"op {op}"), f"Unexpected opcode 'op {op}' in: {line}")

    def test_boolean_bitwise_folding(self):
        code = """
x = True & False
y = True | False
z = True ^ True
"""
        res = compile_py(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        self.assertIn("set x false", lines)
        self.assertIn("set y true", lines)
        self.assertIn("set z false", lines)

    def test_nested_bitwise_folding(self):
        code = "mask = (1 << 3) | (1 << 1)"
        res = compile_py(code)
        # 8 | 2 = 10
        self.assertIn("set mask 10", res.mlog)


class TestComparisonAndLogicalFolding(unittest.TestCase):
    """Test folding of comparisons and boolean logic."""

    def test_comparison_folding(self):
        code = """
c1 = 10 > 5
c2 = 10 < 5
c3 = 5 == 5
c4 = 5 != 5
c5 = 4 <= 4
c6 = 4 >= 5
c7 = "abc" == "abc"
c8 = "abc" != "def"
"""
        res = compile_py(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        self.assertIn("set c1 true", lines)
        self.assertIn("set c2 false", lines)
        self.assertIn("set c3 true", lines)
        self.assertIn("set c4 false", lines)
        self.assertIn("set c5 true", lines)
        self.assertIn("set c6 false", lines)
        self.assertIn("set c7 true", lines)
        self.assertIn("set c8 true", lines)

    def test_boolean_and_or_not_folding(self):
        code = """
b1 = True and False
b2 = False or True
b3 = not True
b4 = not False
b5 = not 0
b6 = not 10
"""
        res = compile_py(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        self.assertIn("set b1 false", lines)
        self.assertIn("set b2 true", lines)
        self.assertIn("set b3 false", lines)
        self.assertIn("set b4 true", lines)
        self.assertIn("set b5 true", lines)
        self.assertIn("set b6 false", lines)

    def test_and_or_returns_operand_not_bool(self):
        """Python 'and' and 'or' evaluate to the operand value, not a coerced bool."""
        code = """
r1 = 10 and 20
r2 = 0 and 20
r3 = 0 or 42
r4 = 10 or 20
b1 = True and False
b2 = False or True
"""
        res = compile_py(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        self.assertIn("set r1 20", lines)
        self.assertIn("set r2 0", lines)
        self.assertIn("set r3 42", lines)
        self.assertIn("set r4 10", lines)
        self.assertIn("set b1 false", lines)
        self.assertIn("set b2 true", lines)

    def test_string_truthiness_deferred_to_runtime(self):
        """String truthiness in 'not' and 'and/or' is deferred to runtime to preserve Mindustry object semantics."""
        # 'not ""' is not folded to true, emits op equal
        res_not = compile_py('s = not ""')
        self.assertIn("op equal", res_not.mlog)

        # '"" or "fallback"' is not folded, emits jump control flow
        res_or = compile_py('s = "" or "fallback"')
        self.assertIn("jump", res_or.mlog)

    def test_bool_vs_int_bitwise(self):
        """Bitwise between booleans preserves bool type; mixed bool and int produces int."""
        code = """
b1 = True & False
b2 = True | False
b3 = True ^ False
i1 = True & 1
i2 = True & 0
i3 = False | 1
i4 = True ^ 1
"""
        res = compile_py(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        # bool & bool -> bool literal in mlog ("true" / "false")
        self.assertIn("set b1 false", lines)
        self.assertIn("set b2 true", lines)
        self.assertIn("set b3 true", lines)
        # bool & int -> int literal in mlog ("1" / "0")
        self.assertIn("set i1 1", lines)
        self.assertIn("set i2 0", lines)
        self.assertIn("set i3 1", lines)
        self.assertIn("set i4 0", lines)

    def test_unary_uadd_folding(self):
        code = "x = +42"
        res = compile_py(code)
        self.assertIn("set x 42", res.mlog)


class TestEdgeCasesAndPreservedSemantics(unittest.TestCase):
    """Verify that operations with runtime semantics or potential errors are NOT folded."""

    def test_division_by_zero_not_folded(self):
        """Division and floor division by zero must defer to runtime (Mindustry Infinity/NaN)."""
        code_div = "x = 10 / 0"
        res_div = compile_py(code_div)
        self.assertIn("op div x 10 0", res_div.mlog)

        code_idiv = "y = 10 // 0"
        res_idiv = compile_py(code_idiv)
        self.assertIn("op idiv y 10 0", res_idiv.mlog)

    def test_negative_floor_division(self):
        """Floor division with negative operands matches Python and Mindustry runtime floor semantics."""
        code = """
d1 = -7 // 3
d2 = 7 // -3
d3 = -7 // -3
d4 = -7.0 // 3.0
"""
        res = compile_py(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        self.assertIn("set d1 -3", lines)
        self.assertIn("set d2 -3", lines)
        self.assertIn("set d3 2", lines)
        self.assertIn("set d4 -3.0", lines)

    def test_negative_exponent_and_domain(self):
        """Negative power produces float; zero with negative exponent and complex results are deferred."""
        code = """
p1 = 2 ** -1
p2 = (-2) ** -1
p3 = (-2) ** -2
"""
        res = compile_py(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        self.assertIn("set p1 0.5", lines)
        self.assertIn("set p2 -0.5", lines)
        self.assertIn("set p3 0.25", lines)

        # 0 ** -1 must not fold (avoid ZeroDivisionError at compile time)
        res_zero = compile_py("p4 = 0 ** -1")
        self.assertIn("op pow p4", res_zero.mlog)

        # (-2) ** 0.5 must not fold (complex in Python, NaN in Mindustry)
        res_comp = compile_py("p5 = (-2) ** 0.5")
        self.assertIn("op pow p5", res_comp.mlog)

    def test_float_nan_inf_not_folded(self):
        """Operations that would yield Infinity or NaN are not folded to preserve Mindustry runtime semantics."""
        code = "x = 1e308 * 10"
        res = compile_py(code)
        self.assertIn("op mul", res.mlog)

    def test_no_side_effects_evaluated(self):
        """Expressions containing function calls are not folded and preserve runtime evaluation."""
        code = """
def get_val():
    return 10
x = get_val() + 5
"""
        res = compile_py(code, allow_functions=True)
        self.assertIn("op add", res.mlog)

    def test_compile_error_preserved_for_invalid_types(self):
        """Bitwise operations on float literals raise CompileError without being suppressed by folding."""
        with self.assertRaises(CompileError) as ctx:
            compile_py("x = 1.5 & 2")
        self.assertIn("float literal", str(ctx.exception))

        with self.assertRaises(CompileError) as ctx:
            compile_py("x = ~1.5")
        self.assertIn("float literal", str(ctx.exception))

    def test_modulo_folding_and_zero_divisor(self):
        """Modulo is folded consistently across positive and negative operands in v8 (emod)."""
        # 1. Negative operands fold consistently with Python floored semantics
        res_neg1 = compile_py("x = -7 % 3")
        self.assertIn("set x 2", res_neg1.mlog)

        res_neg2 = compile_py("x = 7 % -3")
        self.assertIn("set x -2", res_neg2.mlog)

        res_neg3 = compile_py("x = -7 % -3")
        self.assertIn("set x -1", res_neg3.mlog)

        res_float = compile_py("x = -7.5 % 3.0")
        self.assertIn("set x 1.5", res_float.mlog)

        # 2. When constant folding is disabled, emits runtime op emod
        res_unfolded = compile_py("x = -7 % 3", fold_constants=False)
        self.assertIn("op emod", res_unfolded.mlog)

        # 3. Literal modulo by zero raises CompileError
        with self.assertRaises(CompileError) as ctx1:
            compile_py("x = 7 % 0")
        self.assertIn("modulo by zero", str(ctx1.exception))

        with self.assertRaises(CompileError) as ctx2:
            compile_py("x = -7 % 0")
        self.assertIn("modulo by zero", str(ctx2.exception))

        with self.assertRaises(CompileError) as ctx3:
            compile_py("x = 7.0 % 0.0")
        self.assertIn("modulo by zero", str(ctx3.exception))

    def test_large_shift_not_folded(self):
        """Shift by >= 64 is rejected by semantic checks or deferred."""
        code = "x = 1 << 65"
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("shift count 65 >= 64 exceeds 64-bit integer width", str(ctx.exception))

    def test_safe_integer_boundaries(self):
        """Integers exceeding 2^53 - 1 are not folded to preserve Mindustry IEEE-754 precision loss."""
        code = """
r1 = 9007199254740993 & 1
end
"""
        res = compile_py(code)
        self.assertIn("op and r1 9007199254740993 1", res.mlog)

    def test_min_max_intrinsics_not_folded(self):
        """min() and max() are Mindustry intrinsics and must emit op min/max."""
        code = """
x = min(10, 20)
y = max(50, 100)
"""
        res = compile_py(code)
        self.assertIn("op min x 10 20", res.mlog)
        self.assertIn("op max y 50 100", res.mlog)

    def test_standalone_unary_minus_and_invert_preserved(self):
        """Standalone -5 and ~5 preserve native lowering."""
        code = "x = -5\ny = ~5"
        res = compile_py(code)
        self.assertIn("op sub x 0 5", res.mlog)
        self.assertIn("op not y 5 0", res.mlog)


class TestNoDeadCodeElimination(unittest.TestCase):
    """Verify strictly that dead code elimination (DCE) is NOT implemented."""

    def test_if_with_constant_false_preserves_both_branches(self):
        code = """
if 1 == 2:
    x = 1
else:
    x = 2
"""
        res = compile_py(code)
        # Condition folds to false and emits jump to else branch
        self.assertIn("jump 3 equal false 0", res.mlog)
        # Body (dead branch) must still be present!
        self.assertIn("set x 1", res.mlog)
        # Else branch must be present!
        self.assertIn("set x 2", res.mlog)
        # Check IR preserves internal labels and jumps
        jump_nodes = [node for node in res.ir if hasattr(node, "target")]
        self.assertTrue(any(j.target.startswith("__if_else") for j in jump_nodes))

    def test_while_false_loop_preserved(self):
        code = """
while 1 == 2:
    x = 99
"""
        res = compile_py(code)
        self.assertIn("jump 3 equal false 0", res.mlog)
        self.assertIn("set x 99", res.mlog)
        jump_nodes = [node for node in res.ir if hasattr(node, "target")]
        self.assertTrue(any(j.target.startswith("__while_end") for j in jump_nodes))


class TestArrayStaticResolution(unittest.TestCase):
    """Test that folded constants resolve statically for Array declarations and indexing."""

    def test_array_size_folded(self):
        code = """
arr = Array("cell1", size=2 * 8)
"""
        res = compile_py(code)
        c = Compiler(fold_constants=True)
        import ast
        tree = ast.parse(code)
        c.compile(tree)
        self.assertIn("arr", c.allocator.arrays)
        self.assertEqual(c.allocator.arrays["arr"].size, 16)

    def test_array_indexing_folded(self):
        code = """
arr = Array("cell1", 10)
arr[1 + 2] = 42
"""
        res = compile_py(code)
        self.assertIn("write 42 cell1 3", res.mlog)
        # Verify no runtime temporary was created for index computation
        self.assertNotIn("op add", res.mlog)

    def test_array_bounds_check_with_folded_constant(self):
        code = """
arr = Array("cell1", 10)
arr[5 + 5] = 99
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("array index out of bounds: index 10 is outside valid range", str(ctx.exception))


class TestCompilerFlagAndOptimizerExport(unittest.TestCase):
    """Test programmatic fold_constants=False toggle and CLI --no-fold-constants flag."""

    def test_fold_constants_disabled_programmatically(self):
        code = "x = 10 + 20"
        res_folded = compile_py(code, fold_constants=True)
        self.assertIn("set x 30", res_folded.mlog)
        self.assertNotIn("op add", res_folded.mlog)

        res_unfolded = compile_py(code, fold_constants=False)
        self.assertIn("op add x 10 20", res_unfolded.mlog)
        self.assertNotIn("set x 30", res_unfolded.mlog)

    def test_optimizer_exports(self):
        self.assertIs(ConstantFolder, OptConstantFolder)
        self.assertIs(fold_constants, opt_fold_constants)

    def test_cli_no_fold_constants_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "test.py"
            out_folded = Path(tmpdir) / "folded.mlog"
            out_unfolded = Path(tmpdir) / "unfolded.mlog"

            src_file.write_text("x = 20 + 30\n", encoding="utf-8")

            # 1. Compile with default (folded)
            exit_code = main(["compile", str(src_file), "-o", str(out_folded), "--no-clipboard"])
            self.assertEqual(exit_code, 0)
            self.assertIn("set x 50", out_folded.read_text(encoding="utf-8"))

            # 2. Compile with --no-fold-constants
            exit_code = main(["compile", str(src_file), "-o", str(out_unfolded), "--no-fold-constants", "--no-clipboard"])
            self.assertEqual(exit_code, 0)
            self.assertIn("op add x 20 30", out_unfolded.read_text(encoding="utf-8"))


class TestMindustryEngineExecutionWithFolding(unittest.TestCase):
    """Validate folded bytecode using Mindustry LExecutor runtime."""

    def test_folded_arithmetic_runtime(self):
        if not is_mindustry_available():
            self.skipTest("Mindustry harness not available in this environment")

        code = """
a = 15 + 27
b = 100 - 42
c = 8 * 9
d = 120 / 4
e = 45 // 4
f = 37 % 5
g = 3 ** 4
h = (1 << 3) | (1 << 1)
i = 10 > 5
end
"""
        res = compile_py(code)
        ok, msg, count = validate_with_mindustry(res.mlog)
        self.assertTrue(ok, f"Validation failed: {msg}")

        ok, vars_dict, msg = run_with_mindustry(res.mlog)
        self.assertTrue(ok, f"Execution failed: {msg}")

        self.assertEqual(vars_dict.get("a"), 42.0)
        self.assertEqual(vars_dict.get("b"), 58.0)
        self.assertEqual(vars_dict.get("c"), 72.0)
        self.assertEqual(vars_dict.get("d"), 30.0)
        self.assertEqual(vars_dict.get("e"), 11.0)
        self.assertEqual(vars_dict.get("f"), 2.0)
        self.assertEqual(vars_dict.get("g"), 81.0)
        self.assertEqual(vars_dict.get("h"), 10.0)
        self.assertEqual(vars_dict.get("i"), 1.0)

    def test_folded_array_operations_validation(self):
        if not is_mindustry_available():
            self.skipTest("Mindustry harness not available in this environment")

        code = """
arr = Array("cell1", size=4 * 4)
arr[0] = 10 + 5
arr[1 + 2] = 20 * 3
val0 = arr[0]
val3 = arr[3]
end
"""
        res = compile_py(code)
        ok, msg, count = validate_with_mindustry(res.mlog)
        self.assertTrue(ok, f"Validation failed: {msg}")

        self.assertIn("write 15 cell1 0", res.mlog)
        self.assertIn("write 60 cell1 3", res.mlog)
        self.assertIn("read val0 cell1 0", res.mlog)
        self.assertIn("read val3 cell1 3", res.mlog)


if __name__ == "__main__":
    unittest.main()
