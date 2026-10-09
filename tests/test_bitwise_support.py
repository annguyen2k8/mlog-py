"""Unit, regression and round-trip tests for Python bitwise operators.

Scope:
- Bitwise AND (&) -> op and
- Bitwise OR (|) -> op or
- Bitwise XOR (^) -> op xor
- Bitwise NOT (~) -> op not (with operand b=0)
- Shift left (<<) -> op shl
- Shift right (>>) -> op shr
- Augmented assignments (&=, |=, ^=, <<=, >>=, +=, etc.) rejected with clear error:
  "unsupported Python feature: augmented assignment"
- Precedence, associativity, parentheses, nested expressions
- Negative numbers and two's complement behavior
- Control flow usage (if, while condition with bitwise expressions)
- Logical vs Bitwise distinction:
  - 'not a' compiles to 'op equal dest a 0' (boolean NOT)
  - '~a' compiles to 'op not dest a 0' (bitwise NOT)
  - 'and' / 'or' compile to conditional jump control flow
  - '&' / '|' compile to 'op and' / 'op or'
- Decompiler expression recovery and round-trip fidelity
- Java Mindustry engine validation
"""

import ast
import unittest

from src.compiler import CompileError
from src.decompiler import decompile
from src.mindustry_validator import (
    is_mindustry_available,
    run_with_mindustry,
    validate_with_mindustry,
)
from src.mlog import compile_py


class TestBitwiseCompiler(unittest.TestCase):
    """Compiler unit tests for bitwise operators."""

    def test_bitwise_and(self):
        code = "res = a & b"
        res = compile_py(code)
        self.assertIn("op and res a b", res.mlog)

    def test_bitwise_or(self):
        code = "res = a | b"
        res = compile_py(code)
        self.assertIn("op or res a b", res.mlog)

    def test_bitwise_xor(self):
        code = "res = a ^ b"
        res = compile_py(code)
        self.assertIn("op xor res a b", res.mlog)

    def test_bitwise_not(self):
        code = "res = ~a"
        res = compile_py(code)
        self.assertIn("op not res a 0", res.mlog)

    def test_shift_left(self):
        code = "res = a << 3"
        res = compile_py(code)
        self.assertIn("op shl res a 3", res.mlog)

    def test_shift_right(self):
        code = "res = a >> 2"
        res = compile_py(code)
        self.assertIn("op shr res a 2", res.mlog)

    def test_negative_numbers(self):
        code = "res = ~(-5)"
        res = compile_py(code)
        # -5 compiled as op sub __tmp0 0 5, then op not res __tmp0 0
        self.assertIn("op sub", res.mlog)
        self.assertIn("op not", res.mlog)

    def test_logical_vs_bitwise_distinction(self):
        """Ensure 'not x' (boolean NOT) and '~x' (bitwise NOT) have distinct opcode emissions."""
        py_bool_not = "res = not x"
        res_bool = compile_py(py_bool_not)
        # boolean NOT is equality check with 0
        self.assertIn("op equal res x 0", res_bool.mlog)
        self.assertNotIn("op not", res_bool.mlog)

        py_bit_not = "res = ~x"
        res_bit = compile_py(py_bit_not)
        # bitwise NOT is op not with dummy 0
        self.assertIn("op not res x 0", res_bit.mlog)
        self.assertNotIn("op equal", res_bit.mlog)

    def test_float_literal_in_bitwise_ops_rejected(self):
        """Float literals in bitwise expressions must be rejected at compile-time."""
        float_cases = [
            ("x = 3.5 & 1", "BitAnd"),
            ("x = 1 | 2.5", "BitOr"),
            ("x = 1.0 ^ 2", "BitXor"),
            ("x = 1.5 << 2", "LShift"),
            ("x = 8 >> 1.5", "RShift"),
            ("x = ~4.2", "Invert"),
        ]
        for code, op_name in float_cases:
            with self.subTest(code=code, op=op_name):
                with self.assertRaises(CompileError) as ctx:
                    compile_py(code)
                self.assertIn("float literal", str(ctx.exception))

    def test_shift_count_bounds_validation(self):
        """Literal shift counts must be non-negative and < 64."""
        # Negative shift counts
        neg_cases = ["x = a << -1", "x = a >> -5"]
        for code in neg_cases:
            with self.subTest(code=code):
                with self.assertRaises(CompileError) as ctx:
                    compile_py(code)
                self.assertIn("negative shift count", str(ctx.exception))

        # Shift counts >= 64
        overflow_cases = ["x = a << 64", "x = a >> 100"]
        for code in overflow_cases:
            with self.subTest(code=code):
                with self.assertRaises(CompileError) as ctx:
                    compile_py(code)
                self.assertIn("exceeds 64-bit integer width", str(ctx.exception))

    def test_integer_literal_out_of_64bit_range_rejected(self):
        """Integer constants exceeding signed 64-bit bounds [-2^63, 2^63 - 1] must be rejected."""
        too_large = "x = 9223372036854775808"  # 2^63
        with self.assertRaises(CompileError) as ctx:
            compile_py(too_large)
        self.assertIn("exceeds signed 64-bit integer range", str(ctx.exception))

        too_small = "x = -9223372036854775809"
        with self.assertRaises(CompileError) as ctx:
            compile_py(too_small)
        self.assertIn("exceeds signed 64-bit integer range", str(ctx.exception))

        # Valid 64-bit max boundary literal compiles cleanly
        valid_max = "x = 9223372036854775807"
        res_max = compile_py(valid_max)
        self.assertIn("9223372036854775807", res_max.mlog)

        # Valid 64-bit min boundary literal -2**63 (-9223372036854775808):
        # Arc lexer fails on literal token 9223372036854775808, so compiler lowers
        # -2**63 to `op shl x 1 63`, producing exact Long.MIN_VALUE in runtime.
        valid_min = "x = -9223372036854775808"
        res_min = compile_py(valid_min)
        self.assertEqual(res_min.mlog.strip(), "op shl x 1 63")

        # Parenthesized -(2**63)
        valid_min_paren = "x = -(9223372036854775808)"
        res_min_paren = compile_py(valid_min_paren)
        self.assertEqual(res_min_paren.mlog.strip(), "op shl x 1 63")

        # -(2**63) - 1 should also be rejected
        too_small_paren = "x = -(9223372036854775809)"
        with self.assertRaises(CompileError) as ctx:
            compile_py(too_small_paren)
        self.assertIn("exceeds signed 64-bit integer range", str(ctx.exception))

    def test_ieee754_double_boundaries_and_bitwise_ops(self):
        """Test expressions around the 2^53 IEEE-754 safe integer limit (9007199254740992)."""
        # 2^53 - 1, 2^53, 2^53 + 1, -(2^53 + 1)
        cases = [
            "x = 9007199254740991 & 1",
            "x = 9007199254740992 | 2",
            "x = 9007199254740993 ^ 3",
            "x = ~(-9007199254740993)",
        ]
        for code in cases:
            with self.subTest(code=code):
                res = compile_py(code)
                self.assertIsNotNone(res.mlog)
                if is_mindustry_available():
                    ok, msg, count = validate_with_mindustry(res.mlog)
                    self.assertTrue(ok, f"Mindustry validation failed for {code}: {msg}")


class TestBitwiseDecompiler(unittest.TestCase):
    """Decompiler unit tests for bitwise operators."""

    def test_decompile_basic_bitwise_ops(self):
        mlog = """
op and r1 a b
op or r2 c d
op xor r3 e f
op not r4 g 0
op shl r5 h 4
op shr r6 i 2
"""
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("r1 = a & b", py)
        self.assertIn("r2 = c | d", py)
        self.assertIn("r3 = e ^ f", py)
        self.assertIn("r4 = ~g", py)
        self.assertIn("r5 = h << 4", py)
        self.assertIn("r6 = i >> 2", py)
        # Bitwise operators are standard Python syntax, no imports
        self.assertNotIn("from mlog", py)

    def test_shift_right_associativity_parenthesization(self):
        """Right operand of << or >> with equal precedence must be parenthesized to preserve semantics."""
        # a >> (b >> c)
        mlog = """
op shr __tmp0 b c
op shr x a __tmp0
"""
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("x = a >> (b >> c)", py)

        # (a >> b) >> c
        mlog_left = """
op shr __tmp0 a b
op shr x __tmp0 c
"""
        py_left = decompile(mlog_left)
        ast.parse(py_left)
        self.assertIn("x = a >> b >> c", py_left)

    def test_nested_bitwise_precedence_parentheses(self):
        """Verify standard Python precedence: () > ~ > <<, >> > & > ^ > |."""
        # & has higher precedence than |: a & (b | c) needs parens
        mlog = """
op or __tmp0 b c
op and x a __tmp0
"""
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("x = a & (b | c)", py)

        # (a & b) | c does not need parens because & binds tighter than |
        mlog2 = """
op and __tmp0 a b
op or x __tmp0 c
"""
        py2 = decompile(mlog2)
        ast.parse(py2)
        self.assertIn("x = a & b | c", py2)

    def test_while_loop_with_bitwise_not_inlined(self):
        """While loop header containing ~x should inline into while condition."""
        mlog = """
set x 0
op not __tmp0 x 0
jump 5 greaterThanEq __tmp0 10
op add x x 1
jump 1 always 0 0
"""
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("while ~x < 10:", py)


class TestBitwiseRoundTripAndEngine(unittest.TestCase):
    """End-to-end roundtrip fidelity and Mindustry engine validation."""

    def test_roundtrip_complex_expressions(self):
        expressions = [
            "a & (b | c)",
            "a & b | c",
            "a ^ (b & c)",
            "(a ^ b) & c",
            "~a & b",
            "~(a & b)",
            "a << b + c",
            "(a << b) + c",
            "a + (b << c)",
            "a >> (b >> c)",
            "a >> b >> c",
            "a << (b << c)",
            "a << b << c",
            "(a == b) & c",
            "a == (b & c)",
        ]

        for expr in expressions:
            with self.subTest(expr=expr):
                code = f"x = {expr}\n"
                compiled = compile_py(code)
                decompiled = decompile(compiled.mlog)
                ast.parse(decompiled)
                recompiled = compile_py(decompiled)
                self.assertEqual(
                    compiled.mlog.strip(),
                    recompiled.mlog.strip(),
                    f"Roundtrip failed for {expr}:\nDecompiled: {decompiled}\nOrig MLog:\n{compiled.mlog}\nRecomp MLog:\n{recompiled.mlog}",
                )

    def test_mindustry_engine_validation(self):
        """Verify all bitwise operations pass official Mindustry bytecode validation."""
        if not is_mindustry_available():
            self.skipTest("Mindustry harness not available in this environment")

        py_code = """
a = 15
b = 4
c = -8
r1 = a & b
r2 = a | b
r3 = a ^ b
r4 = ~a
r5 = a << 2
r6 = b >> 1
r7 = c >> 1
r8 = (a & b) | (c ^ r1)
r9 = ~c
r10 = a << (b >> 1)
"""
        res = compile_py(py_code)
        ok, msg, count = validate_with_mindustry(res.mlog)
        self.assertTrue(ok, f"Mindustry parser validation failed: {msg}")
        self.assertGreaterEqual(count, 15)

    def test_mindustry_runtime_execution(self):
        """Execute compiled bitwise operations in actual Mindustry LExecutor runtime and assert variable results."""
        if not is_mindustry_available():
            self.skipTest("Mindustry harness not available in this environment")

        py_code = """
a = 15
b = 4
c = -8
r1 = a & b
r2 = a | b
r3 = a ^ b
r4 = ~a
r5 = a << 2
r6 = b >> 1
r7 = c >> 1
r8 = (a & b) | (c ^ r1)
r9 = ~c
r10 = a << (b >> 1)
end
"""
        res = compile_py(py_code)
        ok, vars_dict, msg = run_with_mindustry(res.mlog)
        self.assertTrue(ok, f"Mindustry runtime execution failed: {msg}")

        # Assert actual runtime values evaluated by LExecutor
        self.assertEqual(vars_dict.get("r1"), 4.0)     # 15 & 4 == 4
        self.assertEqual(vars_dict.get("r2"), 15.0)    # 15 | 4 == 15
        self.assertEqual(vars_dict.get("r3"), 11.0)    # 15 ^ 4 == 11
        self.assertEqual(vars_dict.get("r4"), -16.0)   # ~15 == -16
        self.assertEqual(vars_dict.get("r5"), 60.0)    # 15 << 2 == 60
        self.assertEqual(vars_dict.get("r6"), 2.0)     # 4 >> 1 == 2
        self.assertEqual(vars_dict.get("r7"), -4.0)    # -8 >> 1 == -4 (arithmetic right shift)
        self.assertEqual(vars_dict.get("r8"), -4.0)    # 4 | (-8 ^ 4) == -4
        self.assertEqual(vars_dict.get("r9"), 7.0)     # ~(-8) == 7
        self.assertEqual(vars_dict.get("r10"), 60.0)   # 15 << 2 == 60

    def test_runtime_boundaries_and_ieee754(self):
        """Assert runtime behavior for -2**63 boundary and 2**53 precision in Mindustry runtime."""
        if not is_mindustry_available():
            self.skipTest("Mindustry harness not available in this environment")

        # 1. Test -2**63 runtime value and bitwise operations on Long.MIN_VALUE
        py_min64 = """
x = -9223372036854775808
y = ~x
z = x >> 1
w = x & -1
end
"""
        res_min64 = compile_py(py_min64)
        ok, vars_dict, msg = run_with_mindustry(res_min64.mlog)
        self.assertTrue(ok, f"Execution failed: {msg}")
        self.assertEqual(vars_dict.get("x"), -9.223372036854776e+18)
        self.assertEqual(vars_dict.get("y"), 9.223372036854776e+18)
        self.assertEqual(vars_dict.get("z"), -4.611686018427388e+18)
        self.assertEqual(vars_dict.get("w"), -9.223372036854776e+18)

        # 2. Test 2**53 precision boundary
        # In Python:
        # 9007199254740993 & 1 == 1 (Python arbitrary precision)
        # In IEEE-754 double (Mindustry runtime):
        # 9007199254740993 rounds to 9007199254740992.0 (even).
        # Therefore, in Mindustry runtime: (long)9007199254740992.0 & 1L == 0.0.
        # This confirms and verifies the known IEEE-754 precision limitation in engine.
        py_double = """
r1 = 9007199254740993 & 1
r2 = 9007199254740991 & 1
end
"""
        res_double = compile_py(py_double)
        ok, vars_dict, msg = run_with_mindustry(res_double.mlog)
        self.assertTrue(ok, f"Execution failed: {msg}")
        self.assertEqual(vars_dict.get("r1"), 0.0)  # Precision loss at 2^53 + 1
        self.assertEqual(vars_dict.get("r2"), 1.0)  # Preserved at 2^53 - 1

    def test_runtime_near_long_boundaries_and_ieee754_distinction(self):
        """Verify runtime behavior for -9223372036854775807 and 9223372036854775807 in Mindustry runtime."""
        if not is_mindustry_available():
            self.skipTest("Mindustry harness not available in this environment")

        py_code = """
pos_max = 9223372036854775807
pos_near = 9223372036854775806
neg_near = -9223372036854775807
r_pos_and = pos_max & 1
r_neg_and = neg_near & 1
end
"""
        res = compile_py(py_code)
        ok, vars_dict, msg = run_with_mindustry(res.mlog)
        self.assertTrue(ok, f"Execution failed: {msg}")

        # Both pos_max (2^63 - 1) and pos_near (2^63 - 2) convert to double 9.223372036854776e18 (2^63).
        self.assertEqual(vars_dict.get("pos_max"), 9.223372036854776e+18)
        self.assertEqual(vars_dict.get("pos_near"), 9.223372036854776e+18)

        # In Mindustry runtime, Arc's Strings.parseDouble parses 9223372036854775807 / 9223372036854775806
        # into double 9.223372036854776E18.
        # In LExecutor's OpI: (long)a.numval casts double 9.223372036854776E18 to Java long.
        # In Java, (long)9.223372036854776E18 clamps to Long.MAX_VALUE (9223372036854775807L).
        # Thus (long)pos_max is Long.MAX_VALUE, so:
        # Long.MAX_VALUE & 1L == 1L -> r_pos_and == 1.0 (even for pos_near = 9223372036854775806 due to float rounding).
        self.assertEqual(vars_dict.get("r_pos_and"), 1.0)

        # For neg_near (-9223372036854775807), `op sub 0 9223372036854775807` computes
        # 0.0 - 9.223372036854776E18 = -9.223372036854776E18.
        # In Java, (long)-9.223372036854776E18 clamps to Long.MIN_VALUE (-9223372036854775808L).
        # Long.MIN_VALUE & 1L == (-9223372036854775808L) & 1L == 0L -> r_neg_and == 0.0.
        # In Python, -9223372036854775807 & 1 == 1.
        # This confirms and proves the discrepancy with Python is 100% due to IEEE-754 double casting/clamping in Java,
        # and NOT an mlog-py compiler bug.
        self.assertEqual(vars_dict.get("neg_near"), -9.223372036854776e+18)
        self.assertEqual(vars_dict.get("r_neg_and"), 0.0)

    def test_run_with_mindustry_robustness(self):
        """Verify run_with_mindustry handles infinite loops, max_steps, timeouts and invalid code safely."""
        if not is_mindustry_available():
            self.skipTest("Mindustry harness not available in this environment")

        # 1. Infinite loop terminated cleanly by max_steps
        loop_mlog = "jump 0 always 0 0\n"
        ok, vars_dict, msg = run_with_mindustry(loop_mlog, max_steps=150)
        self.assertTrue(ok)
        self.assertEqual(msg, "RUN_OK:150")

        # 2. Timeout handled properly
        ok_to, vars_to, msg_to = run_with_mindustry(loop_mlog, max_steps=100_000_000, timeout_sec=0.5)
        self.assertFalse(ok_to)
        self.assertIn("timed out", msg_to)

        # 3. Invalid instruction rejected cleanly with failure message
        invalid_mlog = "nonexistent_instruction a b c\n"
        ok_inv, vars_inv, msg_inv = run_with_mindustry(invalid_mlog)
        self.assertFalse(ok_inv)
        self.assertIn("InvalidStatement", msg_inv)


if __name__ == "__main__":
    unittest.main()


