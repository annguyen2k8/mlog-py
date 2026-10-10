"""Unit, regression, and Java harness verification tests for Augmented Assignment.

Covers:
- Scalar variables with all 12 supported operators:
  +=, -=, *=, /=, //=, %=, **=, &=, |=, ^=, <<=, >>=
- Array element augmented assignments (int, float, bool dtypes)
- Single-evaluation guarantee for index expressions and base offsets (no duplicate reads or evaluations)
- Compile-time bounds, type validations, and error reporting for unsupported operators (e.g. @=)
- Python runtime Array emulation verification
- Mindustry Java harness bytecode assembly and runtime LExecutor execution
"""

import unittest

from src.compiler import CompileError
from src.metadata import Array, SensorProperty
from src.mindustry_validator import (
    is_mindustry_available,
    run_with_mindustry,
    validate_with_mindustry,
)
from src.mlog import compile_py
from src.validator import MlogValidator


class TestAugAssignScalar(unittest.TestCase):
    """Unit tests for augmented assignments on simple scalar variables."""

    def test_all_twelve_operators(self):
        """All 12 supported Python operators compile to canonical MLog op instructions."""
        cases = [
            ("x += 5", "op add x x 5"),
            ("x -= 3", "op sub x x 3"),
            ("x *= 4", "op mul x x 4"),
            ("x /= 2", "op div x x 2"),
            ("x //= 2", "op idiv x x 2"),
            ("x %= 3", "op mod x x 3"),
            ("x **= 2", "op pow x x 2"),
            ("x &= 7", "op and x x 7"),
            ("x |= 8", "op or x x 8"),
            ("x ^= 1", "op xor x x 1"),
            ("x <<= 2", "op shl x x 2"),
            ("x >>= 1", "op shr x x 1"),
        ]
        for stmt, expected_op in cases:
            with self.subTest(stmt=stmt):
                code = f"x = 10\n{stmt}"
                res = compile_py(code)
                self.assertIn(expected_op, res.mlog)
                MlogValidator.validate(res.mlog)

    def test_complex_rhs_expression(self):
        """RHS expressions are evaluated before applying the augmented assignment."""
        code = """
x = 10
y = 3
x += y * 2 + 1
"""
        res = compile_py(code)
        lines = [line.strip() for line in res.mlog.splitlines() if line.strip()]
        self.assertIn("op mul __tmp0 y 2", lines)
        self.assertIn("op add __tmp1 __tmp0 1", lines)
        self.assertIn("op add x x __tmp1", lines)
        MlogValidator.validate(res.mlog)

    def test_rhs_referencing_target(self):
        """Target variable referenced in RHS evaluates correctly without collision."""
        code = """
x = 5
x += x
"""
        res = compile_py(code)
        self.assertIn("op add x x x", res.mlog)
        MlogValidator.validate(res.mlog)

    def test_builtin_registers_augmented_assignment(self):
        """Special registers like counter/@counter and @unit support augmented assignment."""
        code = """
counter += 2
at_unit += 1
"""
        res = compile_py(code)
        self.assertIn("op add @counter @counter 2", res.mlog)
        self.assertIn("op add @unit @unit 1", res.mlog)
        MlogValidator.validate(res.mlog)

    def test_function_scope_augmented_assignment(self):
        """Augmented assignments operate correctly inside procedure bodies."""
        code = """
def step(val):
    val += 10
    val *= 2
    return val

r = step(5)
"""
        res = compile_py(code, allow_functions=True)
        self.assertIn("op add val val 10", res.mlog)
        self.assertIn("op mul val val 2", res.mlog)
        MlogValidator.validate(res.mlog)

    def test_loop_counter_augmented_assignment(self):
        """Augmented assignments work in while loops and for loop bodies."""
        code = """
total = 0
i = 0
while i < 10:
    total += i
    i += 1
"""
        res = compile_py(code)
        self.assertIn("op add total total i", res.mlog)
        self.assertIn("op add i i 1", res.mlog)
        MlogValidator.validate(res.mlog)


class TestAugAssignArray(unittest.TestCase):
    """Unit tests for array element augmented assignments (arr[i] op= val)."""

    def test_int_array_all_operators_literal_index(self):
        """All 12 operators on integer array compile read -> op -> write at static address."""
        operators = [
            ("+=", "op add"),
            ("-=", "op sub"),
            ("*=", "op mul"),
            ("/=", "op div"),
            ("//=", "op idiv"),
            ("%=", "op mod"),
            ("**=", "op pow"),
            ("&=", "op and"),
            ("|=", "op or"),
            ("^=", "op xor"),
            ("<<=", "op shl"),
            (">>=", "op shr"),
        ]
        for op_sym, mlog_op in operators:
            with self.subTest(op=op_sym):
                code = f"""
from mlog import Array
a = Array("cell1", size=10)
a[0] {op_sym} 2
"""
                res = compile_py(code)
                lines = [l.strip() for l in res.mlog.splitlines() if l.strip()]
                # Pattern: read tmp0 cell1 0, op ... tmp1 tmp0 2, write tmp1 cell1 0
                self.assertIn("read __tmp0 cell1 0", lines)
                self.assertIn(f"{mlog_op} __tmp1 __tmp0 2", lines)
                self.assertIn("write __tmp1 cell1 0", lines)
                MlogValidator.validate(res.mlog)

    def test_array_single_evaluation_dynamic_index(self):
        """Dynamic index is read and evaluated exactly once; address is reused for read & write."""
        code = """
from mlog import Array
a = Array("cell1", size=10)
a[i] += 5
"""
        res = compile_py(code)
        lines = [l.strip() for l in res.mlog.splitlines() if l.strip()]
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], "read __tmp0 cell1 i")
        self.assertEqual(lines[1], "op add __tmp1 __tmp0 5")
        self.assertEqual(lines[2], "write __tmp1 cell1 i")
        MlogValidator.validate(res.mlog)

    def test_array_single_evaluation_with_base_offset(self):
        """Array with non-zero base offset evaluates offset addition exactly once."""
        code = """
from mlog import Array
first = Array("cell1", size=10)
second = Array("cell1", size=10)
second[i] += 7
"""
        res = compile_py(code)
        lines = [l.strip() for l in res.mlog.splitlines() if l.strip()]
        # second array has base_offset = 10
        self.assertIn("op add __tmp0 i 10", lines)
        self.assertIn("read __tmp1 cell1 __tmp0", lines)
        self.assertIn("op add __tmp2 __tmp1 7", lines)
        self.assertIn("write __tmp2 cell1 __tmp0", lines)
        # Verify offset addition is only emitted once
        offset_adds = [l for l in lines if l.startswith("op add") and "10" in l]
        self.assertEqual(len(offset_adds), 1)
        MlogValidator.validate(res.mlog)

    def test_array_single_evaluation_complex_index_expression(self):
        """Complex subscript index expression is computed once into temporary address."""
        code = """
from mlog import Array
a = Array("cell1", size=20)
a[x + y * 2] += 42
"""
        res = compile_py(code)
        lines = [l.strip() for l in res.mlog.splitlines() if l.strip()]
        # Multiplication and addition of index expression
        self.assertIn("op mul __tmp0 y 2", lines)
        self.assertIn("op add __tmp1 x __tmp0", lines)
        # read and write use the exact same address __tmp1
        self.assertIn("read __tmp2 cell1 __tmp1", lines)
        self.assertIn("op add __tmp3 __tmp2 42", lines)
        self.assertIn("write __tmp3 cell1 __tmp1", lines)
        # Verify index calculation ops are not duplicated
        mul_count = [l for l in lines if "op mul" in l]
        self.assertEqual(len(mul_count), 1)
        MlogValidator.validate(res.mlog)

    def test_array_augmented_assignment_with_array_rhs(self):
        """Array element on RHS reads from array and adds to target element."""
        code = """
from mlog import Array
a = Array("cell1", size=10)
a[i] += a[j]
"""
        res = compile_py(code)
        lines = [l.strip() for l in res.mlog.splitlines() if l.strip()]
        self.assertIn("read __tmp0 cell1 i", lines)
        self.assertIn("read __tmp1 cell1 j", lines)
        self.assertIn("op add __tmp2 __tmp0 __tmp1", lines)
        self.assertIn("write __tmp2 cell1 i", lines)
        MlogValidator.validate(res.mlog)

    def test_float_array_augmented_assignment(self):
        """Float array supports floating point arithmetic augmented assignments."""
        code = """
from mlog import Array
data = Array("cell1", size=10, dtype=float)
data[0] += 3.14159
data[1] -= 0.5
data[2] *= 2.5
data[3] /= 1.25
data[4] //= 2
data[5] %= 1.5
data[6] **= 2
data[i] += 42
"""
        res = compile_py(code)
        self.assertIn("read __tmp0 cell1 0", res.mlog)
        self.assertIn("op add __tmp1 __tmp0 3.14159", res.mlog)
        self.assertIn("write __tmp1 cell1 0", res.mlog)
        self.assertIn("op sub __tmp3 __tmp2 0.5", res.mlog)
        self.assertIn("op mul __tmp5 __tmp4 2.5", res.mlog)
        self.assertIn("op div __tmp7 __tmp6 1.25", res.mlog)
        self.assertIn("op add __tmp15 __tmp14 42", res.mlog)
        MlogValidator.validate(res.mlog)

    def test_float_array_with_intrinsic_call_rhs(self):
        """Float array augmented assignment with sensor() call on RHS."""
        code = """
from mlog import Array, sensor, SensorProperty
readings = Array("cell1", size=5, dtype=float)
readings[0] += sensor("reactor1", SensorProperty.HEAT)
"""
        res = compile_py(code)
        lines = [l.strip() for l in res.mlog.splitlines() if l.strip()]
        self.assertIn("read __tmp0 cell1 0", lines)
        self.assertIn("sensor __tmp1 reactor1 @heat", lines)
        self.assertIn("op add __tmp2 __tmp0 __tmp1", lines)
        self.assertIn("write __tmp2 cell1 0", lines)
        MlogValidator.validate(res.mlog)

    def test_bool_array_augmented_assignment(self):
        """Bool array supports &=, |=, ^= operations with boolean literals."""
        code = """
from mlog import Array
flags = Array("cell1", size=5, dtype=bool)
flags[0] &= True
flags[1] |= False
flags[2] ^= True
"""
        res = compile_py(code)
        self.assertIn("read __tmp0 cell1 0", res.mlog)
        self.assertIn("op and __tmp1 __tmp0 true", res.mlog)
        self.assertIn("write __tmp1 cell1 0", res.mlog)
        self.assertIn("op or __tmp3 __tmp2 false", res.mlog)
        self.assertIn("op xor __tmp5 __tmp4 true", res.mlog)
        MlogValidator.validate(res.mlog)

    def test_bool_array_dynamic_normalization(self):
        """Bool array normalizes dynamic non-boolean RHS expressions to 0 or 1 before bitwise op."""
        code = """
from mlog import Array
flags = Array("cell1", size=5, dtype=bool)
flags[i] &= raw_status
"""
        res = compile_py(code)
        lines = [l.strip() for l in res.mlog.splitlines() if l.strip()]
        self.assertIn("read __tmp0 cell1 i", lines)
        self.assertIn("op notEqual __tmp1 raw_status 0", lines)
        self.assertIn("op and __tmp2 __tmp0 __tmp1", lines)
        self.assertIn("write __tmp2 cell1 i", lines)
        MlogValidator.validate(res.mlog)


class TestAugAssignErrors(unittest.TestCase):
    """Compile-time error reporting and validation tests for augmented assignments."""

    def test_unsupported_operator_matrix_multiplication(self):
        """Operator @= (ast.MatMult) is rejected with clear error message."""
        code = "x @= 5"
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("unsupported augmented assignment operator: '@='", str(ctx.exception))

    def test_unsupported_target_attribute(self):
        """Attribute targets on non-variables are rejected."""
        code = """
from mlog import SensorProperty
SensorProperty.HEAT += 1
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("augmented assignment target must be a simple variable name or array index", str(ctx.exception))

    def test_reassign_array_variable_rejected(self):
        """Performing augmented assignment directly on an Array variable itself is rejected."""
        code = """
from mlog import Array
arr = Array("cell1", size=10)
arr += 5
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("cannot perform augmented assignment on Array variable 'arr'", str(ctx.exception))

    def test_non_array_subscript_rejected(self):
        """Subscript augmented assignment on non-array variable is rejected."""
        code = """
x = 10
x[0] += 5
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("'x' is not an Array", str(ctx.exception))

    def test_array_subscript_float_index_rejected(self):
        """Float literal index in augmented assignment is rejected."""
        code = """
from mlog import Array
arr = Array("cell1", size=10)
arr[1.5] += 5
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("array index must be an integer, got float literal", str(ctx.exception))

    def test_array_subscript_str_index_rejected(self):
        """String literal index in augmented assignment is rejected."""
        code = """
from mlog import Array
arr = Array("cell1", size=10)
arr["index"] += 5
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("array index must be an integer, got string literal", str(ctx.exception))

    def test_array_subscript_bool_index_rejected(self):
        """Boolean literal index in augmented assignment is rejected."""
        code = """
from mlog import Array
arr = Array("cell1", size=10)
arr[True] += 5
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("array index must be an integer, got boolean literal", str(ctx.exception))

    def test_array_subscript_out_of_bounds_rejected(self):
        """Literal index outside valid bounds is rejected at compile time."""
        code_upper = """
from mlog import Array
arr = Array("cell1", size=10)
arr[10] += 1
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code_upper)
        self.assertIn("array index out of bounds: index 10 is outside valid range [0, 10)", str(ctx.exception))

        code_neg = """
from mlog import Array
arr = Array("cell1", size=10)
arr[-1] += 1
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code_neg)
        self.assertIn("array index out of bounds: index -1 is outside valid range [0, 10)", str(ctx.exception))

    def test_int_array_rejects_float_literal(self):
        """Int array rejects float literal operand in augmented assignment."""
        code = """
from mlog import Array
arr = Array("cell1", size=10)
arr[0] += 3.14
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("Array only stores integers; float literal is not supported", str(ctx.exception))

    def test_int_array_rejects_str_and_bool_literals(self):
        """Int array rejects string and boolean literals in augmented assignment."""
        for val in ('"text"', "True", "False"):
            code = f"""
from mlog import Array
arr = Array("cell1", size=10)
arr[0] += {val}
"""
            with self.assertRaises(CompileError) as ctx:
                compile_py(code)
            self.assertIn("Array only stores integers", str(ctx.exception))

    def test_float_array_rejects_bitwise_operators(self):
        """Float array rejects bitwise augmented assignment operators."""
        for op_sym in ("&=", "|=", "^=", "<<=", ">>="):
            code = f"""
from mlog import Array
arr = Array("cell1", size=10, dtype=float)
arr[0] {op_sym} 1
"""
            with self.assertRaises(CompileError) as ctx:
                compile_py(code)
            self.assertIn("unsupported operand type for bitwise operator", str(ctx.exception))

    def test_float_array_rejects_str_and_bool_literals(self):
        """Float array rejects string and boolean literals in augmented assignment."""
        for val in ('"msg"', "True", "False"):
            code = f"""
from mlog import Array
arr = Array("cell1", size=10, dtype=float)
arr[0] += {val}
"""
            with self.assertRaises(CompileError) as ctx:
                compile_py(code)
            self.assertIn("Array of type 'float' only stores numbers", str(ctx.exception))

    def test_bool_array_rejects_arithmetic_operators(self):
        """Bool array rejects arithmetic augmented assignment operators."""
        for op_sym in ("+=", "-=", "*=", "/=", "//=", "%=", "**="):
            code = f"""
from mlog import Array
arr = Array("cell1", size=10, dtype=bool)
arr[0] {op_sym} True
"""
            with self.assertRaises(CompileError) as ctx:
                compile_py(code)
            self.assertIn("only '&=', '|=', '^=' are supported", str(ctx.exception))

    def test_bool_array_rejects_non_bool_literals(self):
        """Bool array rejects integer, float, and string literals in bitwise aug-assign."""
        for val, err in [
            ("1", "integer literal is not supported"),
            ("1.0", "float literal is not supported"),
            ('"true"', "string literal is not supported"),
        ]:
            code = f"""
from mlog import Array
arr = Array("cell1", size=10, dtype=bool)
arr[0] &= {val}
"""
            with self.assertRaises(CompileError) as ctx:
                compile_py(code)
            self.assertIn(err, str(ctx.exception))

    def test_bitwise_scalar_float_literal_rejected(self):
        """Bitwise augmented assignment on scalar variable with float literal is rejected."""
        for op_sym in ("&=", "|=", "^="):
            code = f"x = 10\nx {op_sym} 1.5"
            with self.assertRaises(CompileError) as ctx:
                compile_py(code)
            self.assertIn("float literal", str(ctx.exception))

    def test_shift_scalar_out_of_bounds_rejected(self):
        """Negative shift or shift >= 64 is rejected at compile time."""
        for val, err in [("-1", "negative shift count"), ("64", "exceeds 64-bit")]:
            code = f"x = 10\nx <<= {val}"
            with self.assertRaises(CompileError) as ctx:
                compile_py(code)
            self.assertIn(err, str(ctx.exception))

            code_shr = f"x = 10\nx >>= {val}"
            with self.assertRaises(CompileError) as ctx:
                compile_py(code_shr)
            self.assertIn(err, str(ctx.exception))

    def test_array_rhs_directly_rejected(self):
        """Using an Array object directly on RHS of augmented assignment is rejected."""
        code = """
from mlog import Array
a = Array("cell1", size=10)
x = 0
x += a
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("cannot use Array 'a' directly in an expression", str(ctx.exception))


class TestRuntimeArrayEmulation(unittest.TestCase):
    """Verify runtime behavior of the Array emulation class with augmented assignments."""

    def test_runtime_int_array_aug_assign(self):
        arr = Array("cell1", size=5, dtype=int)
        arr[0] += 10
        self.assertEqual(arr[0], 10)
        arr[0] -= 3
        self.assertEqual(arr[0], 7)
        arr[0] *= 2
        self.assertEqual(arr[0], 14)
        arr[0] //= 3
        self.assertEqual(arr[0], 4)
        arr[0] %= 3
        self.assertEqual(arr[0], 1)
        arr[0] **= 4
        self.assertEqual(arr[0], 1)
        arr[0] &= 1
        self.assertEqual(arr[0], 1)
        arr[0] |= 2
        self.assertEqual(arr[0], 3)
        arr[0] ^= 1
        self.assertEqual(arr[0], 2)
        arr[0] <<= 2
        self.assertEqual(arr[0], 8)
        arr[0] >>= 1
        self.assertEqual(arr[0], 4)

    def test_runtime_float_array_aug_assign(self):
        arr = Array("cell1", size=5, dtype=float)
        arr[0] += 3.5
        self.assertEqual(arr[0], 3.5)
        arr[0] -= 0.5
        self.assertEqual(arr[0], 3.0)
        arr[0] *= 2.0
        self.assertEqual(arr[0], 6.0)
        arr[0] /= 4.0
        self.assertEqual(arr[0], 1.5)

    def test_runtime_bool_array_aug_assign(self):
        arr = Array("cell1", size=5, dtype=bool)
        self.assertIs(arr[0], False)
        arr[0] |= True
        self.assertIs(arr[0], True)
        arr[0] &= False
        self.assertIs(arr[0], False)
        arr[0] ^= True
        self.assertIs(arr[0], True)
        arr[0] ^= True
        self.assertIs(arr[0], False)

        with self.assertRaises(TypeError):
            arr[0] += True

        with self.assertRaises(TypeError):
            arr[0] += 1


class TestAugAssignJavaHarness(unittest.TestCase):
    """Mindustry engine bytecode assembly and execution validation via Java harness."""

    def test_mindustry_assembly_validation_all_operators(self):
        """Compiled bytecode for all 12 operators passes Mindustry LAssembler."""
        if not is_mindustry_available():
            self.skipTest("Mindustry Java harness not available")

        code = """
from mlog import Array
cell_mem = Array("cell1", size=10)

x = 100
x += 10
x -= 5
x *= 2
x /= 5
x //= 3
x %= 4
x **= 2
x &= 15
x |= 8
x ^= 3
x <<= 2
x >>= 1

cell_mem[0] = 50
cell_mem[0] += x
cell_mem[i] += 1
end
"""
        res = compile_py(code)
        ok, msg, count = validate_with_mindustry(res.mlog)
        self.assertTrue(ok, f"Mindustry assembly error: {msg}")
        self.assertGreater(count, 0)

    def test_mindustry_runtime_execution_scalar_math(self):
        """Execute scalar augmented assignments in Mindustry runtime and verify final variable values."""
        if not is_mindustry_available():
            self.skipTest("Mindustry Java harness not available")

        code = """
a = 10
a += 5       # 15
b = 20
b -= 8       # 12
c = 4
c *= 3       # 12
d = 15
d //= 4      # 3
e = 17
e %= 5       # 2
f = 2
f **= 4      # 16
g = 15
g &= 6       # 6
h = 8
h |= 3       # 11
k = 9
k ^= 5       # 12
m = 3
m <<= 2      # 12
n = 16
n >>= 2      # 4
end
"""
        res = compile_py(code)
        ok, vars_dict, msg = run_with_mindustry(res.mlog)
        self.assertTrue(ok, f"Mindustry runtime execution failed: {msg}")

        self.assertEqual(vars_dict.get("a"), 15.0)
        self.assertEqual(vars_dict.get("b"), 12.0)
        self.assertEqual(vars_dict.get("c"), 12.0)
        self.assertEqual(vars_dict.get("d"), 3.0)
        self.assertEqual(vars_dict.get("e"), 2.0)
        self.assertEqual(vars_dict.get("f"), 16.0)
        self.assertEqual(vars_dict.get("g"), 6.0)
        self.assertEqual(vars_dict.get("h"), 11.0)
        self.assertEqual(vars_dict.get("k"), 12.0)
        self.assertEqual(vars_dict.get("m"), 12.0)
        self.assertEqual(vars_dict.get("n"), 4.0)

    def test_mindustry_runtime_execution_accumulator_loop(self):
        """Execute loop accumulation using += in Mindustry runtime."""
        if not is_mindustry_available():
            self.skipTest("Mindustry Java harness not available")

        code = """
total = 0
for i in range(1, 6):
    total += i
end
"""
        res = compile_py(code)
        ok, vars_dict, msg = run_with_mindustry(res.mlog)
        self.assertTrue(ok, f"Mindustry runtime execution failed: {msg}")
        self.assertEqual(vars_dict.get("total"), 15.0)

    def test_mindustry_runtime_execution_audited_edge_cases(self):
        """Audit edge cases: //=, **=, bool ^=, @counter jump in real Mindustry runtime."""
        if not is_mindustry_available():
            self.skipTest("Mindustry Java harness not available")

        code = """
# 1. Floor division //= with negative and positive values
pos_div = 15
pos_div //= 4
neg_div = -15
neg_div //= 4

# 2. Power **= with fractional exponent
pow_val = 4
pow_val **= 0.5

# 3. Boolean toggle ^=
flag = 0
flag ^= 1
flag_t1 = flag
flag ^= 1
flag_t2 = flag

# 4. Program counter jump skipping instruction
counter += 1
skipped = 999
executed = 1
end
"""
        res = compile_py(code)
        ok, vars_dict, msg = run_with_mindustry(res.mlog)
        self.assertTrue(ok, f"Mindustry runtime execution failed: {msg}")

        self.assertEqual(vars_dict.get("pos_div"), 3.0)
        self.assertEqual(vars_dict.get("neg_div"), -4.0)
        self.assertEqual(vars_dict.get("pow_val"), 2.0)
        self.assertEqual(vars_dict.get("flag_t1"), 1.0)
        self.assertEqual(vars_dict.get("flag_t2"), 0.0)
        self.assertEqual(vars_dict.get("skipped"), "null")
        self.assertEqual(vars_dict.get("executed"), 1.0)


if __name__ == "__main__":
    unittest.main()
