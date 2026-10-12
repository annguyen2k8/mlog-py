"""Tests for Mindustry Operation Callable Namespace Object (op.<method>).

Verifies:
1. Expression form binary: result = op.add(a, b)
2. Statement form binary: op.add(result, a, b)
3. Expression form unary: result = op.sin(deg)
4. Statement form unary: op.sin(result, deg)
5. Rejection of Python keywords as methods (op.not_, op.and_, op.or_)
6. CamelCase and snake_case aliases (not_equal/notEqual, angle_diff/angleDiff, etc.)
7. Interplay with infix operators and nested expressions
8. Standalone statement execution
9. Legacy function-call syntax compatibility (op("add", ...), op(LogicOp.ADD, ...), op("not", ...), op("and", ...), op("or", ...))
10. Arity and parameter validation errors
11. Runtime Python execution stub
"""

import unittest
from src.mlog import compile_py
from src.errors import CompileError
import mlog


class TestOpNamespace(unittest.TestCase):

    def test_expression_form_binary_arithmetic(self):
        """Test binary arithmetic operations in expression form."""
        code = (
            "from mlog import op\n"
            "res1 = op.add(a, b)\n"
            "res2 = op.sub(a, b)\n"
            "res3 = op.mul(a, b)\n"
            "res4 = op.div(a, b)\n"
            "res5 = op.idiv(a, b)\n"
            "res6 = op.mod(a, b)\n"
            "res7 = op.emod(a, b)\n"
            "res8 = op.pow(a, b)\n"
        )
        res = compile_py(code, fold_constants=False)
        self.assertIn("op add res1 a b", res.mlog)
        self.assertIn("op sub res2 a b", res.mlog)
        self.assertIn("op mul res3 a b", res.mlog)
        self.assertIn("op div res4 a b", res.mlog)
        self.assertIn("op idiv res5 a b", res.mlog)
        self.assertIn("op mod res6 a b", res.mlog)
        self.assertIn("op emod res7 a b", res.mlog)
        self.assertIn("op pow res8 a b", res.mlog)

    def test_statement_form_binary_arithmetic(self):
        """Test binary arithmetic operations in statement form."""
        code = (
            "from mlog import op\n"
            "op.add(res1, a, b)\n"
            "op.sub(res2, a, b)\n"
            "op.mul(res3, a, b)\n"
            "op.div(res4, a, b)\n"
        )
        res = compile_py(code, fold_constants=False)
        self.assertIn("op add res1 a b", res.mlog)
        self.assertIn("op sub res2 a b", res.mlog)
        self.assertIn("op mul res3 a b", res.mlog)
        self.assertIn("op div res4 a b", res.mlog)

    def test_expression_form_unary_math(self):
        """Test unary math operations in expression form."""
        code = (
            "from mlog import op\n"
            "r1 = op.sin(deg)\n"
            "r2 = op.cos(deg)\n"
            "r3 = op.tan(deg)\n"
            "r4 = op.asin(val)\n"
            "r5 = op.acos(val)\n"
            "r6 = op.atan(val)\n"
            "r7 = op.abs(val)\n"
            "r8 = op.sqrt(val)\n"
            "r9 = op.floor(val)\n"
            "r10 = op.ceil(val)\n"
            "r11 = op.round(val)\n"
            "r12 = op.log(val)\n"
            "r13 = op.log10(val)\n"
            "r14 = op.log_10(val)\n"
            "r15 = op.sign(val)\n"
            "r16 = op.rand(val)\n"
        )
        res = compile_py(code, fold_constants=False)
        self.assertIn("op sin r1 deg 0", res.mlog)
        self.assertIn("op cos r2 deg 0", res.mlog)
        self.assertIn("op tan r3 deg 0", res.mlog)
        self.assertIn("op asin r4 val 0", res.mlog)
        self.assertIn("op acos r5 val 0", res.mlog)
        self.assertIn("op atan r6 val 0", res.mlog)
        self.assertIn("op abs r7 val 0", res.mlog)
        self.assertIn("op sqrt r8 val 0", res.mlog)
        self.assertIn("op floor r9 val 0", res.mlog)
        self.assertIn("op ceil r10 val 0", res.mlog)
        self.assertIn("op round r11 val 0", res.mlog)
        self.assertIn("op log r12 val 0", res.mlog)
        self.assertIn("op log10 r13 val 0", res.mlog)
        self.assertIn("op log10 r14 val 0", res.mlog)
        self.assertIn("op sign r15 val 0", res.mlog)
        self.assertIn("op rand r16 val 0", res.mlog)

    def test_statement_form_unary_math(self):
        """Test unary math operations in statement form."""
        code = (
            "from mlog import op\n"
            "op.sin(res1, deg)\n"
            "op.abs(res2, val)\n"
            "op.rand(res3, 100)\n"
            "op.round(res4, val)\n"
        )
        res = compile_py(code, fold_constants=False)
        self.assertIn("op sin res1 deg 0", res.mlog)
        self.assertIn("op abs res2 val 0", res.mlog)
        self.assertIn("op rand res3 100 0", res.mlog)
        self.assertIn("op round res4 val 0", res.mlog)

    def test_bitwise_operations(self):
        """Test bitwise operations (xor, shl, shr, ushr)."""
        code = (
            "from mlog import op\n"
            "r_xor = op.xor(a, b)\n"
            "op.xor(dest_xor, a, b)\n"
            "r_shl = op.shl(a, 2)\n"
            "r_shr = op.shr(a, 2)\n"
            "r_ushr = op.ushr(a, 2)\n"
        )
        res = compile_py(code, fold_constants=False)
        self.assertIn("op xor r_xor a b", res.mlog)
        self.assertIn("op xor dest_xor a b", res.mlog)
        self.assertIn("op shl r_shl a 2", res.mlog)
        self.assertIn("op shr r_shr a 2", res.mlog)
        self.assertIn("op ushr r_ushr a 2", res.mlog)

    def test_rejected_keyword_methods(self):
        """Verify op.not_, op.and_, and op.or_ methods are completely rejected."""
        with self.assertRaises(CompileError) as ctx1:
            compile_py("from mlog import op\nx = op.not_(a)\n")
        self.assertIn("unknown op method", str(ctx1.exception))

        with self.assertRaises(CompileError) as ctx2:
            compile_py("from mlog import op\nx = op.and_(a, b)\n")
        self.assertIn("unknown op method", str(ctx2.exception))

        with self.assertRaises(CompileError) as ctx3:
            compile_py("from mlog import op\nx = op.or_(a, b)\n")
        self.assertIn("unknown op method", str(ctx3.exception))

    def test_comparison_operations_and_aliases(self):
        """Test comparison operations with camelCase and snake_case aliases."""
        code = (
            "from mlog import op\n"
            "r1 = op.equal(a, b)\n"
            "r2 = op.not_equal(a, b)\n"
            "r3 = op.notEqual(a, b)\n"
            "r4 = op.land(a, b)\n"
            "r5 = op.less_than(a, b)\n"
            "r6 = op.lessThan(a, b)\n"
            "r7 = op.less_than_eq(a, b)\n"
            "r8 = op.lessThanEq(a, b)\n"
            "r9 = op.greater_than(a, b)\n"
            "r10 = op.greaterThan(a, b)\n"
            "r11 = op.greater_than_eq(a, b)\n"
            "r12 = op.greaterThanEq(a, b)\n"
            "r13 = op.strict_equal(a, b)\n"
            "r14 = op.strictEqual(a, b)\n"
        )
        res = compile_py(code, fold_constants=False)
        self.assertIn("op equal r1 a b", res.mlog)
        self.assertIn("op notEqual r2 a b", res.mlog)
        self.assertIn("op notEqual r3 a b", res.mlog)
        self.assertIn("op land r4 a b", res.mlog)
        self.assertIn("op lessThan r5 a b", res.mlog)
        self.assertIn("op lessThan r6 a b", res.mlog)
        self.assertIn("op lessThanEq r7 a b", res.mlog)
        self.assertIn("op lessThanEq r8 a b", res.mlog)
        self.assertIn("op greaterThan r9 a b", res.mlog)
        self.assertIn("op greaterThan r10 a b", res.mlog)
        self.assertIn("op greaterThanEq r11 a b", res.mlog)
        self.assertIn("op greaterThanEq r12 a b", res.mlog)
        self.assertIn("op strictEqual r13 a b", res.mlog)
        self.assertIn("op strictEqual r14 a b", res.mlog)

    def test_vector_noise_log_operations(self):
        """Test min, max, angle, angleDiff, len, noise, logn."""
        code = (
            "from mlog import op\n"
            "r1 = op.min(a, b)\n"
            "r2 = op.max(a, b)\n"
            "r3 = op.angle(x, y)\n"
            "r4 = op.angle_diff(a1, a2)\n"
            "r5 = op.angleDiff(a1, a2)\n"
            "r6 = op.len(dx, dy)\n"
            "r7 = op.length(dx, dy)\n"
            "r8 = op.noise(x, y)\n"
            "r9 = op.logn(val, base)\n"
        )
        res = compile_py(code, fold_constants=False)
        self.assertIn("op min r1 a b", res.mlog)
        self.assertIn("op max r2 a b", res.mlog)
        self.assertIn("op angle r3 x y", res.mlog)
        self.assertIn("op angleDiff r4 a1 a2", res.mlog)
        self.assertIn("op angleDiff r5 a1 a2", res.mlog)
        self.assertIn("op len r6 dx dy", res.mlog)
        self.assertIn("op len r7 dx dy", res.mlog)
        self.assertIn("op noise r8 x y", res.mlog)
        self.assertIn("op logn r9 val base", res.mlog)

    def test_interplay_with_infix_operators(self):
        """Test nesting op.<method> within infix expressions."""
        code = (
            "from mlog import op\n"
            "res = op.add(a, b) * 2 + op.sin(deg)\n"
        )
        res = compile_py(code, fold_constants=False)
        self.assertIn("op add", res.mlog)
        self.assertIn("op sin", res.mlog)
        self.assertIn("op mul", res.mlog)

    def test_nested_op_calls(self):
        """Test nested op.<method> calls inside other op.<method> calls."""
        code = (
            "from mlog import op\n"
            "res1 = op.add(op.mul(a, b), op.sub(c, d))\n"
            "res2 = op.sin(op.add(deg, 45))\n"
            "op.add(res3, op.mul(a, b), c)\n"
        )
        res = compile_py(code, fold_constants=False)
        self.assertIn("op mul __tmp0 a b", res.mlog)
        self.assertIn("op sub __tmp1 c d", res.mlog)
        self.assertIn("op add res1 __tmp0 __tmp1", res.mlog)
        self.assertIn("op add __tmp2 deg 45", res.mlog)
        self.assertIn("op sin res2 __tmp2 0", res.mlog)
        self.assertIn("op add res3 __tmp3 c", res.mlog)

    def test_standalone_statements(self):
        """Test op.<method> called as standalone statement without assignment."""
        code = (
            "from mlog import op\n"
            "op.add(a, b)\n"
            "op.sin(deg)\n"
        )
        res = compile_py(code, fold_constants=False)
        self.assertIn("op add __tmp0 a b", res.mlog)
        self.assertIn("op sin __tmp1 deg 0", res.mlog)

    def test_legacy_form_compatibility(self):
        """Test legacy op('add', ...) and op(LogicOp.ADD, ...) syntax including not, and, or."""
        code = (
            "from mlog import op, LogicOp\n"
            "op('add', res1, a, b)\n"
            "res2 = op('add', a, b)\n"
            "res3 = op(LogicOp.ADD, a, b)\n"
            "op('sin', res4, deg)\n"
            "res5 = op('sin', deg)\n"
            "op('not', res_not, flag)\n"
            "res_not2 = op('not', flag)\n"
            "op('and', res_and, a, b)\n"
            "res_and2 = op('and', a, b)\n"
            "op('or', res_or, a, b)\n"
            "res_or2 = op('or', a, b)\n"
            "res_not_enum = op(LogicOp.NOT, flag)\n"
            "res_and_enum = op(LogicOp.AND, a, b)\n"
            "res_or_enum = op(LogicOp.OR, a, b)\n"
        )
        res = compile_py(code, fold_constants=False)
        self.assertIn("op add res1 a b", res.mlog)
        self.assertIn("op add res2 a b", res.mlog)
        self.assertIn("op add res3 a b", res.mlog)
        self.assertIn("op sin res4 deg 0", res.mlog)
        self.assertIn("op sin res5 deg 0", res.mlog)
        self.assertIn("op not res_not flag 0", res.mlog)
        self.assertIn("op not res_not2 flag 0", res.mlog)
        self.assertIn("op and res_and a b", res.mlog)
        self.assertIn("op and res_and2 a b", res.mlog)
        self.assertIn("op or res_or a b", res.mlog)
        self.assertIn("op or res_or2 a b", res.mlog)
        self.assertIn("op not res_not_enum flag 0", res.mlog)
        self.assertIn("op and res_and_enum a b", res.mlog)
        self.assertIn("op or res_or_enum a b", res.mlog)

    def test_unknown_method_error(self):
        """Test rejection of unknown op method."""
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import op\nop.unknown_op(1, 2)\n")
        self.assertIn("unknown op method", str(ctx.exception))

    def test_unary_arity_errors(self):
        """Test unary arity error reporting."""
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import op\nop.sin()\n")
        self.assertIn("requires 1 operand", str(ctx.exception))

        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import op\nop.sin(1, 2, 3)\n")
        self.assertIn("takes at most 2 arguments", str(ctx.exception))

    def test_binary_arity_errors(self):
        """Test binary arity error reporting."""
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import op\nop.add(1)\n")
        self.assertIn("requires 2 operands", str(ctx.exception))

        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import op\nop.add(1, 2, 3, 4)\n")
        self.assertIn("takes at most 3 arguments", str(ctx.exception))

    def test_keyword_arguments_error(self):
        """Test rejection of keyword arguments."""
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import op\nop.add(a=1, b=2)\n")
        self.assertIn("keyword arguments are not supported in op.add()", str(ctx.exception))

    def test_assignment_with_statement_form(self):
        """Test assigning the result of a statement-form op call."""
        code = (
            "from mlog import op\n"
            "x = op.add(target, a, b)\n"
            "y = op.sin(target_unary, deg)\n"
        )
        res = compile_py(code, fold_constants=False)
        self.assertIn("op add target a b", res.mlog)
        self.assertIn("set x target", res.mlog)
        self.assertIn("op sin target_unary deg 0", res.mlog)
        self.assertIn("set y target_unary", res.mlog)

    def test_op_in_condition(self):
        """Test op.<method> calls inside if/while conditions."""
        code = (
            "from mlog import op\n"
            "if op.less_than(a, 10):\n"
            "    print(1)\n"
        )
        res = compile_py(code, fold_constants=False)
        self.assertIn("op lessThan", res.mlog)
        self.assertIn("print 1", res.mlog)

    def test_all_42_namespace_operations_coverage(self):
        """Verify all 42 Mindustry v160.7 operations available via op.<method>, and 3 keyword ops via legacy op()."""
        from src.mlog_registry_data import LOGIC_OPERATIONS
        from src.mlog_registry import UNARY_LOGIC_OPS
        for mlog_op in LOGIC_OPERATIONS:
            if mlog_op in ("not", "and", "or"):
                # Keyword operations are not available as namespace methods; verified via legacy op()
                if mlog_op == "not":
                    code = "from mlog import op\nres = op('not', x)\n"
                    res = compile_py(code, fold_constants=False)
                    self.assertIn("op not res x 0", res.mlog)
                else:
                    code = f"from mlog import op\nres = op('{mlog_op}', x, y)\n"
                    res = compile_py(code, fold_constants=False)
                    self.assertIn(f"op {mlog_op} res x y", res.mlog)
            elif mlog_op in UNARY_LOGIC_OPS:
                code = f"from mlog import op\nres = op.{mlog_op}(x)\n"
                res = compile_py(code, fold_constants=False)
                self.assertIn(f"op {mlog_op} res x 0", res.mlog)
            else:
                code = f"from mlog import op\nres = op.{mlog_op}(x, y)\n"
                res = compile_py(code, fold_constants=False)
                self.assertIn(f"op {mlog_op} res x y", res.mlog)

    def test_runtime_python_execution(self):
        """Verify direct Python runtime execution behaves gracefully and rejects removed keyword methods."""
        self.assertEqual(mlog.op.add(1, 2), 0)
        self.assertEqual(mlog.op.sub(1, 2), 0)
        self.assertEqual(mlog.op.sin(90), 0)
        self.assertEqual(mlog.op("add", 1, 2), 0)
        self.assertEqual(mlog.op("sin", 90), 0)
        self.assertEqual(mlog.op("not", 1), 0)
        self.assertEqual(mlog.op("and", 1, 2), 0)
        self.assertEqual(mlog.op("or", 1, 2), 0)
        # Verify removal of not_, and_, or_ from namespace runtime
        self.assertFalse(hasattr(mlog.op, "not_"))
        self.assertFalse(hasattr(mlog.op, "and_"))
        self.assertFalse(hasattr(mlog.op, "or_"))


if __name__ == "__main__":
    unittest.main()
