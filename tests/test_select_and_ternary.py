"""Comprehensive tests for Mindustry select opcode, intrinsic select(), and Python ternary (ast.IfExp).

Tests verify:
1. Pure Python ternary lowering to Mindustry 'select' opcode (select dest op comp0 comp1 a b)
2. Complex / side-effect / division ternary lowering to jump control flow with strict short-circuiting
3. Pure and impure nested ternary handling
4. Intrinsic select() with 3, 4, 5, and 6 argument forms
5. Standalone statement validation and error handling
6. MlogValidator syntax verification
7. Round-trip decompiler recovery between Python ternary and Mlog select
8. Compile-time constant folding for IfExp
"""

import shutil
import subprocess
import unittest

from src.compiler import CompileError
from src.decompiler import decompile
from src.mindustry_validator import get_classpath, is_mindustry_available, run_with_mindustry
from src.mlog import compile_py
from src.metadata import _rt_select
from src.validator import MlogValidator, ValidationError


class TestPureTernaryCompilation(unittest.TestCase):
    """Test pure ternary expressions that lower directly to Mindustry select opcode."""

    def test_pure_simple_name_ternary(self):
        """x = a if c else b lowers to select x notEqual c 0 a b."""
        source = "x = a if c else b\n"
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], "select x notEqual c 0 a b")

    def test_pure_constants_ternary(self):
        """x = 1 if c else 2 lowers to select x notEqual c 0 1 2."""
        source = "x = 1 if c else 2\n"
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], "select x notEqual c 0 1 2")

    def test_pure_not_condition_ternary(self):
        """x = a if not c else b lowers to select x equal c 0 a b."""
        source = "x = a if not c else b\n"
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], "select x equal c 0 a b")

    def test_pure_comparison_conditions(self):
        """Test all comparison operators lowering directly into select opcode."""
        cases = [
            ("x = 1 if a < 10 else 2", "select x lessThan a 10 1 2"),
            ("x = 1 if a <= 10 else 2", "select x lessThanEq a 10 1 2"),
            ("x = 1 if a > 10 else 2", "select x greaterThan a 10 1 2"),
            ("x = 1 if a >= 10 else 2", "select x greaterThanEq a 10 1 2"),
            ("x = 1 if a == 10 else 2", "select x equal a 10 1 2"),
            ("x = 1 if a != 10 else 2", "select x notEqual a 10 1 2"),
            ("x = 1 if a is None else 2", "select x strictEqual a null 1 2"),
        ]
        for src, expected in cases:
            with self.subTest(src=src):
                res = compile_py(src)
                lines = res.mlog.strip().splitlines()
                self.assertEqual(lines[0], expected)

    def test_pure_ternary_nested_in_arithmetic(self):
        """Ternary expression nested in arithmetic expression allocates temporary and uses select."""
        source = "res = (1 if c else 2) + 5\n"
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(lines[0], "select __tmp0 notEqual c 0 1 2")
        self.assertEqual(lines[1], "op add res __tmp0 5")

    def test_pure_nested_ternary(self):
        """Pure nested ternary expressions chain select opcodes without jumps."""
        source = "x = 1 if c1 else (2 if c2 else 3)\n"
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], "select __tmp0 notEqual c2 0 2 3")
        self.assertEqual(lines[1], "select x notEqual c1 0 1 __tmp0")

    def test_pure_is_not_ternary(self):
        """x = 1 if a is not None else 2 lowers to select x strictEqual a null 2 1 with inverted branches."""
        source = "x = 1 if a is not None else 2\n"
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], "select x strictEqual a null 2 1")

    def test_pure_nested_in_body(self):
        """Nested ternary in body branch compiles pure select instructions."""
        source = "x = (1 if c1 else 2) if c0 else 3\n"
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], "select __tmp0 notEqual c1 0 1 2")
        self.assertEqual(lines[1], "select x notEqual c0 0 __tmp0 3")

    def test_pure_nested_in_test(self):
        """Nested ternary in condition compiles pure select instructions."""
        source = "x = 1 if (2 if c1 else 3) else 4\n"
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], "select __tmp0 notEqual c1 0 2 3")
        self.assertEqual(lines[1], "select x notEqual __tmp0 0 1 4")

    def test_evaluation_order_test_before_body(self):
        """Test expression instructions are emitted before body and else instructions."""
        source = "x = (c + d) if (a + b) > 10 else 2\n"
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        # op add for condition (a + b) should appear before op add for body (c + d)
        self.assertEqual(lines[0], "op add __tmp0 a b")
        self.assertEqual(lines[1], "op add __tmp1 c d")
        self.assertEqual(lines[2], "select x greaterThan __tmp0 10 __tmp1 2")


class TestImpureTernaryShortCircuit(unittest.TestCase):
    """Test ternary expressions requiring short-circuiting that must lower to jumps."""

    def test_call_in_body_uses_jump(self):
        """Function call in body branch must not execute when condition is falsy."""
        source = "from mlog import print\nx = print(1) if c else 0\n"
        res = compile_py(source)
        self.assertIn("jump ", res.mlog)
        self.assertNotIn("select ", res.mlog)

    def test_call_in_else_uses_jump(self):
        """Function call in else branch must not execute when condition is truthy."""
        source = "from mlog import print\nx = 0 if c else print(2)\n"
        res = compile_py(source)
        self.assertIn("jump ", res.mlog)
        self.assertNotIn("select ", res.mlog)

    def test_division_by_variable_uses_jump(self):
        """Guarded division (100 / x if x != 0 else 0) must use jump to prevent zero division."""
        source = "res = 100 / x if x != 0 else 0\n"
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        # Must have conditional jump protecting division
        self.assertTrue(any("jump " in l for l in lines))
        self.assertNotIn("select ", res.mlog)

    def test_array_subscript_uses_jump(self):
        """Guarded array indexing must use jumps to avoid out-of-bounds access."""
        source = (
            "from mlog import Array\n"
            "arr = Array('cell1', 10)\n"
            "val = arr[i] if i < 10 else 0\n"
        )
        res = compile_py(source)
        self.assertTrue(any("jump " in l for l in res.mlog.splitlines()))
        self.assertNotIn("select ", res.mlog)

    def test_call_in_condition_with_side_effect_branch(self):
        """Ternary where branches have side effects uses jump control flow."""
        source = (
            "from mlog import wait\n"
            "x = wait(1) if c else wait(2)\n"
        )
        res = compile_py(source)
        self.assertIn("jump ", res.mlog)
        self.assertNotIn("select ", res.mlog)

    def test_nested_ternary_with_side_effect(self):
        """Nested ternary where inner branch has side effect falls back to jumps."""
        source = (
            "from mlog import print\n"
            "x = 1 if c1 else (print('foo') if c2 else 3)\n"
        )
        res = compile_py(source)
        self.assertIn("jump ", res.mlog)
        self.assertNotIn("select ", res.mlog)

    def test_compound_and_condition_uses_jump(self):
        """Ternary with compound 'and' condition lowers to short-circuit jumps."""
        source = "x = 1 if (a > 0 and b > 0) else 2\n"
        res = compile_py(source)
        self.assertIn("jump ", res.mlog)
        self.assertNotIn("select ", res.mlog)

    def test_compound_or_condition_uses_jump(self):
        """Ternary with compound 'or' condition lowers to short-circuit jumps."""
        source = "x = 1 if (a > 0 or b > 0) else 2\n"
        res = compile_py(source)
        self.assertIn("jump ", res.mlog)
        self.assertNotIn("select ", res.mlog)

    def test_division_by_constant_zero_uses_jump(self):
        """Ternary with division by literal zero lowers to jumps."""
        source = "x = (10 / 0) if c else 0\n"
        res = compile_py(source)
        self.assertIn("jump ", res.mlog)
        self.assertNotIn("select ", res.mlog)

    def test_modulo_by_variable_uses_jump(self):
        """Ternary with variable modulo lowers to jumps."""
        source = "x = (a % b) if b != 0 else 0\n"
        res = compile_py(source)
        self.assertIn("jump ", res.mlog)
        self.assertNotIn("select ", res.mlog)


class TestIntrinsicSelect(unittest.TestCase):
    """Test compiler intrinsic select() function call variations."""

    def test_select_3_args_expression(self):
        """x = select(c, a, b) -> select x notEqual c 0 a b."""
        source = "from mlog import select\nx = select(c, a, b)\n"
        res = compile_py(source)
        self.assertEqual(res.mlog.strip(), "select x notEqual c 0 a b")

    def test_select_4_args_statement(self):
        """select(x, c, a, b) -> select x notEqual c 0 a b."""
        source = "from mlog import select\nselect(x, c, a, b)\n"
        res = compile_py(source)
        self.assertEqual(res.mlog.strip(), "select x notEqual c 0 a b")

    def test_select_5_args_expression(self):
        """x = select('lessThan', a, b, 1, 2) -> select x lessThan a b 1 2."""
        source = "from mlog import select\nx = select('lessThan', a, b, 1, 2)\n"
        res = compile_py(source)
        self.assertEqual(res.mlog.strip(), "select x lessThan a b 1 2")

    def test_select_6_args_statement(self):
        """select(x, 'greaterThanEq', a, b, 1, 2) -> select x greaterThanEq a b 1 2."""
        source = "from mlog import select\nselect(x, 'greaterThanEq', a, b, 1, 2)\n"
        res = compile_py(source)
        self.assertEqual(res.mlog.strip(), "select x greaterThanEq a b 1 2")

    def test_select_standalone_statement_without_dest_rejected(self):
        """Standalone select(c, a, b) without dest raises CompileError."""
        source = "from mlog import select\nselect(c, a, b)\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source)
        self.assertIn("invalid arguments for select", str(ctx.exception))

    def test_select_invalid_condition_op_rejected(self):
        """select with invalid condition operator raises CompileError."""
        source = "from mlog import select\nx = select('invalidOp', a, b, 1, 2)\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source)
        self.assertIn("unknown jump condition", str(ctx.exception))

    def test_select_runtime_evaluation(self):
        """_rt_select executes correctly in Python runtime."""
        self.assertEqual(_rt_select(True, 10, 20), 10)
        self.assertEqual(_rt_select(False, 10, 20), 20)
        self.assertEqual(_rt_select("res", True, 10, 20), 10)
        self.assertEqual(_rt_select("lessThan", 5, 10, "yes", "no"), "yes")
        self.assertEqual(_rt_select("lessThan", 15, 10, "yes", "no"), "no")
        self.assertEqual(_rt_select("res", "equal", 5, 5, 1, 0), 1)


class TestMlogValidatorSelect(unittest.TestCase):
    """Test MlogValidator opcode and argument validation for select."""

    def test_valid_select_passes_validator(self):
        mlog = "select result lessThan a 10 1 2\n"
        MlogValidator.validate(mlog)

    def test_invalid_condition_fails_validator(self):
        mlog = "select result badCond a 10 1 2\n"
        with self.assertRaises(ValidationError) as ctx:
            MlogValidator.validate(mlog)
        self.assertIn("Invalid select condition", str(ctx.exception))

    def test_wrong_arg_count_fails_validator(self):
        mlog = "select result lessThan a 10 1\n"
        with self.assertRaises(ValidationError) as ctx:
            MlogValidator.validate(mlog)
        self.assertIn("expects 6 arguments, got 5", str(ctx.exception))


class TestTernaryRoundTripDecompiler(unittest.TestCase):
    """Test round-trip decompilation and recompilation between select and ternary."""

    def test_comparison_ternary_roundtrip(self):
        """x = 1 if a < 10 else 2 decompiles and recompiles cleanly."""
        source = "x = 1 if a < 10 else 2\n"
        res = compile_py(source)
        self.assertEqual(res.mlog.strip(), "select x lessThan a 10 1 2")

        py = decompile(res.mlog)
        self.assertIn("x = 1 if a < 10 else 2", py)

        recompiled = compile_py(py)
        self.assertEqual(recompiled.mlog.strip(), "select x lessThan a 10 1 2")

    def test_truthiness_ternary_roundtrip(self):
        """x = y if c else z decompiles and recompiles cleanly."""
        source = "x = y if c else z\n"
        res = compile_py(source)
        self.assertEqual(res.mlog.strip(), "select x notEqual c 0 y z")

        py = decompile(res.mlog)
        self.assertIn("x = y if c else z", py)

        recompiled = compile_py(py)
        self.assertEqual(recompiled.mlog.strip(), "select x notEqual c 0 y z")

    def test_not_ternary_roundtrip(self):
        """x = y if not c else z decompiles and recompiles cleanly."""
        source = "x = y if not c else z\n"
        res = compile_py(source)
        self.assertEqual(res.mlog.strip(), "select x equal c 0 y z")

        py = decompile(res.mlog)
        self.assertIn("x = y if not c else z", py)

        recompiled = compile_py(py)
        self.assertEqual(recompiled.mlog.strip(), "select x equal c 0 y z")

    def test_all_condition_ops_roundtrip(self):
        """Verify all 8 ConditionOps roundtrip between MLog select and Python ternary."""
        ops = [
            ("equal", "==", "x = 1 if a == 10 else 2", "select x equal a 10 1 2"),
            ("notEqual", "!=", "x = 1 if a != 10 else 2", "select x notEqual a 10 1 2"),
            ("lessThan", "<", "x = 1 if a < 10 else 2", "select x lessThan a 10 1 2"),
            ("lessThanEq", "<=", "x = 1 if a <= 10 else 2", "select x lessThanEq a 10 1 2"),
            ("greaterThan", ">", "x = 1 if a > 10 else 2", "select x greaterThan a 10 1 2"),
            ("greaterThanEq", ">=", "x = 1 if a >= 10 else 2", "select x greaterThanEq a 10 1 2"),
            ("strictEqual", "is", "x = 1 if a is None else 2", "select x strictEqual a null 1 2"),
        ]
        for op, py_sym, py_src, expected_mlog in ops:
            with self.subTest(op=op):
                res = compile_py(py_src)
                self.assertEqual(res.mlog.strip(), expected_mlog)
                py = decompile(res.mlog)
                self.assertIn(py_sym, py)
                recompiled = compile_py(py)
                self.assertEqual(recompiled.mlog.strip(), expected_mlog)

    def test_always_condition_decompilation(self):
        """select dest always 0 0 1 2 decompiles to valid Python boolean literal True."""
        mlog = "select dest always 0 0 1 2\n"
        py = decompile(mlog)
        self.assertIn("dest = 1 if True else 2", py)
        self.assertNotIn("'True'", py)

    def test_nested_body_ternary_parentheses_roundtrip(self):
        """(1 if c1 else 2) if c0 else 3 must retain parentheses in body when decompiled."""
        source = "x = (1 if c1 else 2) if c0 else 3\n"
        res = compile_py(source)
        py = decompile(res.mlog)
        # Verify parentheses around body
        self.assertIn("(1 if c1 else 2)", py)
        recompiled = compile_py(py)
        self.assertEqual(res.mlog.strip(), recompiled.mlog.strip())

    def test_raw_select_decompiler(self):
        """Raw select instruction decompiles to Python ternary."""
        mlog = "select dest greaterThan x 0 100 200\n"
        py = decompile(mlog)
        self.assertIn("dest = 100 if x > 0 else 200", py)
        recompiled = compile_py(py)
        self.assertEqual(recompiled.mlog.strip(), "select dest greaterThan x 0 100 200")


class TestConstantFoldingIfExp(unittest.TestCase):
    """Test compile-time constant folding of constant ternary expressions."""

    def test_constant_true_ternary_folds(self):
        """x = 10 if True else 20 folds directly to set x 10."""
        source = "x = 10 if True else 20\n"
        res = compile_py(source)
        self.assertEqual(res.mlog.strip(), "set x 10")

    def test_constant_false_ternary_folds(self):
        """x = 10 if False else 20 folds directly to set x 20."""
        source = "x = 10 if False else 20\n"
        res = compile_py(source)
        self.assertEqual(res.mlog.strip(), "set x 20")

    def test_constant_none_ternary_folds(self):
        """x = 10 if None else 20 folds directly to set x 20."""
        source = "x = 10 if None else 20\n"
        res = compile_py(source)
        self.assertEqual(res.mlog.strip(), "set x 20")

    def test_constant_is_none_folds(self):
        """x = 10 if None is None else 20 folds directly to set x 10."""
        source = "x = 10 if None is None else 20\n"
        res = compile_py(source)
        self.assertEqual(res.mlog.strip(), "set x 10")

    def test_constant_is_not_none_folds(self):
        """x = 10 if 1 is not None else 20 folds directly to set x 10."""
        source = "x = 10 if 1 is not None else 20\n"
        res = compile_py(source)
        self.assertEqual(res.mlog.strip(), "set x 10")

    def test_constant_comparison_ternary_folds(self):
        """x = 10 if 5 > 3 else 20 folds directly to set x 10."""
        source = "x = 10 if 5 > 3 else 20\n"
        res = compile_py(source)
        self.assertEqual(res.mlog.strip(), "set x 10")


class TestRuntimeShortCircuitAndMindustrySemantics(unittest.TestCase):
    """Test runtime short-circuiting and verify ConditionOp semantics matching Mindustry v160.7."""

    def test_runtime_short_circuit_with_side_effects(self):
        """Verify branching ternary uses jump so unused branch is never reached."""
        compiled = compile_py("from mlog import print\nx = print(1) if cond else print(2)")
        lines = compiled.mlog.strip().splitlines()
        # Find jump to else target line index
        jump_to_else = [l for l in lines if l.startswith("jump ") and "equal cond 0" in l][0]
        else_target_idx = int(jump_to_else.split()[1])

        print1_idx = lines.index("print 1")
        print2_idx = lines.index("print 2")
        # print 1 is in then branch (before else target line)
        self.assertLess(print1_idx, else_target_idx)
        # print 2 is at the else target line (target of jump when cond == 0)
        self.assertEqual(print2_idx, else_target_idx)

    def test_mindustry_strict_equal_semantics(self):
        """Verify ConditionOp strictEqual, equal, and notEqual match Mindustry JVM engine."""
        from src.metadata import _eval_condition_op

        # 0 is not None: under strictEqual, 0 === null is False
        self.assertFalse(_eval_condition_op("strictEqual", 0, None))
        self.assertFalse(_eval_condition_op("strictEqual", 0, "null"))
        # null === null is True
        self.assertTrue(_eval_condition_op("strictEqual", None, None))
        self.assertTrue(_eval_condition_op("strictEqual", "null", None))
        # 5 === 5.0 is True in Mindustry (both are numeric double values)
        self.assertTrue(_eval_condition_op("strictEqual", 5, 5.0))
        # Unquoted numeric string token '5' parses as double in Mindustry LAssembler
        self.assertTrue(_eval_condition_op("strictEqual", 5, "5"))
        # Quoted string '"5"' is explicitly an object: '5' === 5 is False
        self.assertFalse(_eval_condition_op("strictEqual", 5, '"5"'))

        # Mindustry bug check: notEqual(0, null) evaluates to False in JVM because null.num() == 0.0
        self.assertFalse(_eval_condition_op("notEqual", 0, None))
        self.assertTrue(_eval_condition_op("equal", 0, None))

        # In Python ternary '1 if a is not None else 2', strictEqual was inverted with swapped branches:
        # select x strictEqual a null 2 1
        # When a == 0: strictEqual(0, null) -> False -> chooses 1 (body, correct!)
        res_when_zero = _rt_select("strictEqual", 0, None, 2, 1)
        self.assertEqual(res_when_zero, 1)

        # When a == None: strictEqual(None, null) -> True -> chooses 2 (orelse, correct!)
        res_when_none = _rt_select("strictEqual", None, None, 2, 1)
        self.assertEqual(res_when_none, 2)

    def test_is_and_is_not_roundtrip_never_becomes_equal(self):
        """Verify 'is' and 'is not' across None, numbers, bool, and objects never decompile into '=='."""
        cases = [
            ("x = 1 if a is None else 2", "select x strictEqual a null 1 2", "is"),
            ("x = 1 if a is b else 2", "select x strictEqual a b 1 2", "is"),
            ("x = 1 if a is 0 else 2", "select x strictEqual a 0 1 2", "is"),
            ("x = 1 if a is True else 2", "select x strictEqual a true 1 2", "is"),
        ]
        for py_src, expected_mlog, expected_op in cases:
            with self.subTest(py_src=py_src):
                res = compile_py(py_src)
                self.assertEqual(res.mlog.strip(), expected_mlog)
                py = decompile(res.mlog)
                self.assertIn(f" {expected_op} ", py)
                self.assertNotIn(" == ", py)
                recompiled = compile_py(py)
                self.assertEqual(recompiled.mlog.strip(), expected_mlog)

    def test_eval_condition_op_all_8_ops_and_types(self):
        """Exhaustively verify all 8 ConditionOps across numbers, objects, booleans, and epsilon boundary."""
        from src.metadata import _eval_condition_op

        # 1. always
        self.assertTrue(_eval_condition_op("always", 1, 2))
        self.assertTrue(_eval_condition_op("always", None, "abc"))

        # 2. equal
        # Exact numbers
        self.assertTrue(_eval_condition_op("equal", 5.0, 5.0))
        # Epsilon boundary check: epsilon = 1e-6 (0.000001)
        self.assertTrue(_eval_condition_op("equal", 1.0, 1.0000005))   # diff 5e-7 < 1e-6 -> True
        self.assertFalse(_eval_condition_op("equal", 1.0, 1.000005))    # diff 5e-6 >= 1e-6 -> False
        # Objects
        self.assertTrue(_eval_condition_op("equal", '"item"', '"item"'))
        self.assertFalse(_eval_condition_op("equal", '"item1"', '"item2"'))
        # Object vs number (Mindustry num() fallback)
        self.assertTrue(_eval_condition_op("equal", 0, None))
        self.assertFalse(_eval_condition_op("equal", 10, None))
        # Booleans
        self.assertTrue(_eval_condition_op("equal", True, 1))
        self.assertTrue(_eval_condition_op("equal", False, 0))

        # 3. notEqual
        self.assertFalse(_eval_condition_op("notEqual", 5.0, 5.0))
        self.assertFalse(_eval_condition_op("notEqual", 1.0, 1.0000005))
        self.assertTrue(_eval_condition_op("notEqual", 1.0, 1.000005))
        self.assertFalse(_eval_condition_op("notEqual", '"item"', '"item"'))
        self.assertTrue(_eval_condition_op("notEqual", '"item1"', '"item2"'))
        self.assertFalse(_eval_condition_op("notEqual", 0, None))  # Mindustry bug check

        # 4. lessThan
        self.assertTrue(_eval_condition_op("lessThan", 4.9999, 5.0))
        self.assertFalse(_eval_condition_op("lessThan", 5.0, 5.0))
        self.assertTrue(_eval_condition_op("lessThan", None, 1.0))   # None.num() = 0 < 1.0

        # 5. lessThanEq
        self.assertTrue(_eval_condition_op("lessThanEq", 5.0, 5.0))
        self.assertFalse(_eval_condition_op("lessThanEq", 5.0001, 5.0))

        # 6. greaterThan
        self.assertTrue(_eval_condition_op("greaterThan", 5.0001, 5.0))
        self.assertFalse(_eval_condition_op("greaterThan", 5.0, 5.0))

        # 7. greaterThanEq
        self.assertTrue(_eval_condition_op("greaterThanEq", 5.0, 5.0))
        self.assertFalse(_eval_condition_op("greaterThanEq", 4.9999, 5.0))

        # 8. strictEqual: NO epsilon tolerance, exact equality only
        self.assertTrue(_eval_condition_op("strictEqual", 1.0, 1.0))
        self.assertFalse(_eval_condition_op("strictEqual", 1.0, 1.0000005))
        self.assertTrue(_eval_condition_op("strictEqual", '"foo"', '"foo"'))
        self.assertFalse(_eval_condition_op("strictEqual", '"foo"', '"bar"'))

    def test_instruction_trace_short_circuit_verification(self):
        """Simulate step-by-step instruction execution to prove non-evaluated branches are never executed."""
        def run_mlog(code_str: str, init_vars: dict) -> Tuple[dict, List[int], List[str]]:
            """Minimal MLOG interpreter for trace verification."""
            res = compile_py(code_str)
            lines = [l.strip() for l in res.mlog.strip().splitlines() if l.strip()]
            vars_state = dict(init_vars)
            trace_pc = []
            executed_lines = []
            pc = 0
            max_steps = 100
            steps = 0
            while 0 <= pc < len(lines) and steps < max_steps:
                steps += 1
                trace_pc.append(pc)
                line = lines[pc]
                executed_lines.append(line)
                tokens = line.split()
                op = tokens[0]

                if op == "jump":
                    target = int(tokens[1])
                    cond = tokens[2]
                    comp0 = tokens[3]
                    comp1 = tokens[4]
                    v0 = vars_state.get(comp0, comp0)
                    v1 = vars_state.get(comp1, comp1)
                    from src.metadata import _eval_condition_op
                    if _eval_condition_op(cond, v0, v1):
                        pc = target
                        continue
                elif op == "set":
                    dest = tokens[1]
                    src = tokens[2]
                    vars_state[dest] = vars_state.get(src, src)
                elif op == "op":
                    sub_op = tokens[1]
                    dest = tokens[2]
                    v0 = float(vars_state.get(tokens[3], tokens[3]))
                    v1 = float(vars_state.get(tokens[4], tokens[4]))
                    if sub_op == "div":
                        if v1 == 0:
                            raise ZeroDivisionError("division by zero in MLOG VM")
                        vars_state[dest] = v0 / v1
                elif op == "print":
                    vars_state["_printed"] = vars_state.get("_printed", []) + [tokens[1]]
                elif op == "read":
                    dest = tokens[1]
                    cell = tokens[2]
                    idx = int(vars_state.get(tokens[3], tokens[3]))
                    if idx >= 10:
                        raise IndexError(f"out of bounds read: {idx} >= 10")
                    vars_state[dest] = f"mem[{idx}]"

                pc += 1
            return vars_state, trace_pc, executed_lines

        # 1. Side effect short-circuiting:
        code_side = "from mlog import print\nx = print('THEN') if cond else print('ELSE')\n"
        # When cond = 1:
        st, _, exec_lines = run_mlog(code_side, {"cond": 1})
        self.assertEqual(st.get("_printed"), ['"THEN"'])
        self.assertFalse(any('print "ELSE"' in l for l in exec_lines))
        # When cond = 0:
        st, _, exec_lines = run_mlog(code_side, {"cond": 0})
        self.assertEqual(st.get("_printed"), ['"ELSE"'])
        self.assertFalse(any('print "THEN"' in l for l in exec_lines))

        # 2. Division by zero short-circuiting:
        code_div = "res = 100 / x if x != 0 else 0\n"
        # When x = 0: should NEVER raise ZeroDivisionError
        st, _, exec_lines = run_mlog(code_div, {"x": 0})
        self.assertEqual(st.get("res"), "0")
        self.assertFalse(any("op div" in l for l in exec_lines))
        # When x = 5: should execute div
        st, _, exec_lines = run_mlog(code_div, {"x": 5})
        self.assertEqual(st.get("res"), 20.0)
        self.assertTrue(any("op div" in l for l in exec_lines))

        # 3. Array access out-of-bounds short-circuiting:
        code_arr = "from mlog import Array\narr = Array('cell1', 10)\nval = arr[i] if i < 10 else 0\n"
        # When i = 15: should NEVER raise IndexError
        st, _, exec_lines = run_mlog(code_arr, {"i": 15})
        self.assertEqual(st.get("val"), "0")
        self.assertFalse(any("read" in l for l in exec_lines))
        # When i = 2: executes read
        st, _, exec_lines = run_mlog(code_arr, {"i": 2})
        self.assertEqual(st.get("val"), "mem[2]")
        self.assertTrue(any("read" in l for l in exec_lines))

        # 4. Nested impure ternary short-circuiting:
        code_nested = "from mlog import print\nx = (print('A') if c1 else print('B')) if c0 else print('C')\n"
        # c0 = 0 -> only C printed, never A or B
        st, _, exec_lines = run_mlog(code_nested, {"c0": 0, "c1": 1})
        self.assertEqual(st.get("_printed"), ['"C"'])
        self.assertFalse(any('print "A"' in l or 'print "B"' in l for l in exec_lines))
        # c0 = 1, c1 = 1 -> only A printed
        st, _, exec_lines = run_mlog(code_nested, {"c0": 1, "c1": 1})
        self.assertEqual(st.get("_printed"), ['"A"'])
        self.assertFalse(any('print "B"' in l or 'print "C"' in l for l in exec_lines))
        # c0 = 1, c1 = 0 -> only B printed
        st, _, exec_lines = run_mlog(code_nested, {"c0": 1, "c1": 0})
        self.assertEqual(st.get("_printed"), ['"B"'])
        self.assertFalse(any('print "A"' in l or 'print "C"' in l for l in exec_lines))


class TestIsNotComprehensiveSemantics(unittest.TestCase):
    """Exhaustive regression tests for 'is not' across all expression contexts and Mindustry JVM runtime.

    Verifies:
    1. Assignment lowering uses strictEqual followed by inversion via equal 0 (avoiding Mindustry notEqual bug).
    2. Pure ternary lowering inverts operands in select opcode (select dest strictEqual a b else then).
    3. If/while control flow jumps on strictEqual to false label without notEqual.
    4. Compound boolean conditions (or / and) properly invert strictEqual via skip jumps.
    5. Full compiler-decompiler round-trip preservation.
    6. Runtime verification in Mindustry v160.7 JVM execution for '0 is not None', 'None is not 0',
       equal numbers, distinct numbers, and 'None is not None'.
    """

    def _run_jvm(self, source: str) -> dict:
        """Helper to run compiled mlog in real Mindustry JVM engine and return variable map."""
        if not is_mindustry_available():
            self.skipTest("Mindustry Java runtime not available in this environment")
        res = compile_py(source)
        run_res = run_with_mindustry(res.mlog)
        self.assertTrue(run_res.success, f"Mindustry JVM failed: {run_res.message}")
        vars_map = {}
        for k, v in run_res.vars.items():
            vars_map[k] = str(v)
        return vars_map

    def test_is_not_assignment_lowering(self):
        """res = a is not b lowers to op strictEqual __tmp a b followed by op equal res __tmp 0."""
        source = "res = a is not b\n"
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], "op strictEqual __tmp0 a b")
        self.assertEqual(lines[1], "op equal res __tmp0 0")

    def test_is_not_pure_ternary_lowering(self):
        """res = 10 if a is not b else 20 lowers to select res strictEqual a b 20 10."""
        source = "res = 10 if a is not b else 20\n"
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], "select res strictEqual a b 20 10")

    def test_is_not_if_statement_lowering(self):
        """if a is not b: res = 10 else: res = 20 jumps on strictEqual to else label."""
        source = "if a is not b:\n    res = 10\nelse:\n    res = 20\n"
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(lines[0], "jump 3 strictEqual a b")
        self.assertEqual(lines[1], "set res 10")
        self.assertEqual(lines[2], "jump 4 always 0 0")
        self.assertEqual(lines[3], "set res 20")

    def test_is_not_compound_or_lowering(self):
        """if (a is not b) or flag: res = 10 else: res = 20 uses strictEqual skip jump."""
        source = "if (a is not b) or flag:\n    res = 10\nelse:\n    res = 20\n"
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        # Verify strictEqual is used to branch, never notEqual
        self.assertTrue(any("strictEqual a b" in l for l in lines))
        self.assertFalse(any("notEqual a b" in l for l in lines))

    def test_is_not_assignment_roundtrip(self):
        """res = a is not b round-trips cleanly from Python -> MLog -> Python -> MLog."""
        source = "res = a is not b\n"
        res = compile_py(source)
        py = decompile(res.mlog)
        self.assertIn("res = a is not b", py)
        recompiled = compile_py(py).mlog.strip()
        self.assertEqual(recompiled, res.mlog.strip())

    def test_is_not_jvm_zero_is_not_none(self):
        """Mindustry JVM runtime verifies 0 is not None evaluates to True across all constructs."""
        # 1. Assignment
        v_assign = self._run_jvm("a = 0\nb = None\nres = a is not b\n")
        self.assertEqual(v_assign.get("res"), "1.0", "0 is not None assignment failed")

        # 2. Ternary
        v_tern = self._run_jvm("a = 0\nb = None\nres = 10 if a is not b else 20\n")
        self.assertEqual(v_tern.get("res"), "10.0", "0 is not None ternary failed")

        # 3. If Statement
        v_if = self._run_jvm("a = 0\nb = None\nif a is not b:\n    res = 10\nelse:\n    res = 20\n")
        self.assertEqual(v_if.get("res"), "10.0", "0 is not None if statement failed")

    def test_is_not_jvm_none_is_not_zero(self):
        """Mindustry JVM runtime verifies None is not 0 evaluates to True across all constructs."""
        # 1. Assignment
        v_assign = self._run_jvm("a = None\nb = 0\nres = a is not b\n")
        self.assertEqual(v_assign.get("res"), "1.0", "None is not 0 assignment failed")

        # 2. Ternary
        v_tern = self._run_jvm("a = None\nb = 0\nres = 10 if a is not b else 20\n")
        self.assertEqual(v_tern.get("res"), "10.0", "None is not 0 ternary failed")

        # 3. If Statement
        v_if = self._run_jvm("a = None\nb = 0\nif a is not b:\n    res = 10\nelse:\n    res = 20\n")
        self.assertEqual(v_if.get("res"), "10.0", "None is not 0 if statement failed")

    def test_is_not_jvm_numbers_equal_and_different(self):
        """Mindustry JVM runtime verifies exact number equality and inequality."""
        # Identical numbers: 5 is not 5 -> False (0.0)
        v_eq = self._run_jvm("a = 5\nb = 5\nres_assign = a is not b\nres_tern = 10 if a is not b else 20\n")
        self.assertEqual(v_eq.get("res_assign"), "0.0")
        self.assertEqual(v_eq.get("res_tern"), "20.0")

        # Different numbers: 5 is not 10 -> True (1.0)
        v_diff = self._run_jvm("a = 5\nb = 10\nres_assign = a is not b\nres_tern = 10 if a is not b else 20\n")
        self.assertEqual(v_diff.get("res_assign"), "1.0")
        self.assertEqual(v_diff.get("res_tern"), "10.0")

        # Identical None: None is not None -> False (0.0)
        v_none = self._run_jvm("a = None\nb = None\nres_assign = a is not b\nres_tern = 10 if a is not b else 20\n")
        self.assertEqual(v_none.get("res_assign"), "0.0")
        self.assertEqual(v_none.get("res_tern"), "20.0")

    def test_is_not_jvm_not_expression(self):
        """Mindustry JVM runtime verifies 'not (a is not b)' boolean inversion."""
        # 0 is not None is True -> not True is False -> res = 20
        v1 = self._run_jvm("a = 0\nb = None\nif not (a is not b):\n    res = 10\nelse:\n    res = 20\n")
        self.assertEqual(v1.get("res"), "20.0")

        # None is not None is False -> not False is True -> res = 10
        v2 = self._run_jvm("a = None\nb = None\nif not (a is not b):\n    res = 10\nelse:\n    res = 20\n")
        self.assertEqual(v2.get("res"), "10.0")

    def test_is_not_jvm_while_loop(self):
        """Mindustry JVM runtime verifies while loop termination with 'is not'."""
        src = """
i = 0
total = 0
x = 0
while i < 5 and x is not None:
    total += i
    i += 1
    if i == 3:
        x = None
"""
        v = self._run_jvm(src)
        self.assertEqual(v.get("i"), "3.0")
        self.assertEqual(v.get("total"), "3.0")
        self.assertEqual(v.get("x"), "null")

    def test_is_not_jvm_nested_and_or(self):
        """Mindustry JVM runtime verifies nested and/or expressions with 'is not'."""
        template = """
a = {a}
b = {b}
c = {c}
d = {d}
if (a is not b and c > 0) or d == 1:
    res = 10
else:
    res = 20
"""
        # True and True or False -> True (10.0)
        self.assertEqual(self._run_jvm(template.format(a="0", b="None", c="5", d="0")).get("res"), "10.0")
        # True and False or False -> False (20.0)
        self.assertEqual(self._run_jvm(template.format(a="0", b="None", c="0", d="0")).get("res"), "20.0")
        # True and False or True -> True (10.0)
        self.assertEqual(self._run_jvm(template.format(a="0", b="None", c="0", d="1")).get("res"), "10.0")
        # False and True or False -> False (20.0)
        self.assertEqual(self._run_jvm(template.format(a="None", b="None", c="5", d="0")).get("res"), "20.0")

    def test_is_not_jvm_elif_branch_chain(self):
        """Mindustry JVM runtime verifies elif branching chain with 'is' and 'is not'."""
        src = """
a = 0
b = None
if a is b:
    res = 1
elif a is not None:
    res = 2
else:
    res = 3
"""
        v = self._run_jvm(src)
        self.assertEqual(v.get("res"), "2.0")


if __name__ == "__main__":
    unittest.main()
