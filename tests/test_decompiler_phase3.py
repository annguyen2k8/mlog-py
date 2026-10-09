"""Phase 3 Unit Tests: Expression & Dataflow Recovery.

Tests Expression IR, Use-Def analysis, single assignment, copy propagation,
binary expressions, nested expression trees with proper precedence parenthesization,
constant propagation, temporary elimination, variable overwrite safety,
multiple-use temporary preservation, expression in if/while conditions,
unknown opcode preservation (Zero Guessing), and end-to-end round-trip integrity.
"""

import ast
import unittest

from src.decompiler import (
    AssignNode,
    BinaryExpr,
    CallExpr,
    ConstantExpr,
    DataflowTransformer,
    ExprStmtNode,
    InstructionNode,
    UnaryExpr,
    VariableExpr,
    decompile,
    decompile_to_structured,
    recover_expressions,
    structure_cfg,
)
from src.mlog import compile_py


class TestDecompilerPhase3(unittest.TestCase):
    """Test suite for Phase 3 Expression & Dataflow Recovery."""

    # -----------------------------------------------------------------------
    # 1. Single Assignment & Direct Operations
    # -----------------------------------------------------------------------

    def test_single_assignment(self):
        """Test simple assignment from constant and variable."""
        mlog = """
set x 10
set y x
"""
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("x = 10", py)
        self.assertIn("y = x", py)

    def test_binary_expression(self):
        """Test direct binary operations mapping to Python operators."""
        mlog = """
op add a x 5
op sub b x 3
op mul c a b
op div d c 2
op idiv e c 4
op mod f c 7
op pow g x 2
op shl h x 1
op shr i x 2
op and j x 255
op or k x 128
op xor l x 15
"""
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("a = x + 5", py)
        self.assertIn("b = x - 3", py)
        self.assertIn("c = a * b", py)
        self.assertIn("d = c / 2", py)
        self.assertIn("e = c // 4", py)
        self.assertIn("f = c % 7", py)
        self.assertIn("g = x ** 2", py)
        self.assertIn("h = x << 1", py)
        self.assertIn("i = x >> 2", py)
        self.assertIn("j = x & 255", py)
        self.assertIn("k = x | 128", py)
        self.assertIn("l = x ^ 15", py)

    def test_unary_expressions(self):
        """Test unary negation and bitwise not."""
        mlog = """
op sub neg 0 x
op not inv x 0
"""
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("neg = -x", py)
        self.assertIn("inv = ~x", py)

    # -----------------------------------------------------------------------
    # 2. Nested Expressions & Parenthesization
    # -----------------------------------------------------------------------

    def test_nested_expression_precedence(self):
        """Test that expressions requiring parentheses are parenthesized correctly."""
        # x = (a + b) * c
        mlog = """
op add __tmp0 a b
op mul x __tmp0 c
"""
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("x = (a + b) * c", py)
        self.assertNotIn("__tmp0", py)

    def test_nested_expression_no_redundant_parens(self):
        """Test that expressions naturally conforming to precedence have no redundant parentheses."""
        # x = a + b * c
        mlog = """
op mul __tmp0 b c
op add x a __tmp0
"""
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("x = a + b * c", py)
        self.assertNotIn("__tmp0", py)

    def test_deeply_nested_expression_chain(self):
        """Test 3 levels of nested operations: res = ((a + b) * c) - d."""
        mlog = """
op add __tmp0 a b
op mul __tmp1 __tmp0 c
op sub res __tmp1 d
"""
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("res = (a + b) * c - d", py)
        self.assertNotIn("__tmp0", py)
        self.assertNotIn("__tmp1", py)

    # -----------------------------------------------------------------------
    # 3. Copy & Constant Propagation
    # -----------------------------------------------------------------------

    def test_copy_propagation(self):
        """Test that temporary copies are propagated and eliminated."""
        mlog = """
set __tmp0 a
op add res __tmp0 5
"""
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("res = a + 5", py)
        self.assertNotIn("__tmp0", py)

    def test_constant_propagation(self):
        """Test constant value propagation through temporary."""
        mlog = """
set __tmp0 100
op mul res __tmp0 factor
"""
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("res = 100 * factor", py)
        self.assertNotIn("__tmp0", py)

    # -----------------------------------------------------------------------
    # 4. Safety Guarantees: Overwrites & Multiple Uses
    # -----------------------------------------------------------------------

    def test_variable_overwrite_prevents_inlining(self):
        """Test that inlining is blocked when a constituent variable is modified between def and use."""
        mlog = """
op add __tmp0 a 1
set a 10
op mul res __tmp0 2
"""
        py = decompile(mlog)
        ast.parse(py)
        # Because 'a' was modified before __tmp0 was used, __tmp0 must NOT be inlined!
        self.assertIn("__tmp0 = a + 1", py)
        self.assertIn("a = 10", py)
        self.assertIn("res = __tmp0 * 2", py)

    def test_multiple_use_temporary_preserved(self):
        """Test that temporaries with multiple uses are not inlined/duplicated."""
        mlog = """
op add __tmp0 a b
op mul x __tmp0 2
op add y __tmp0 3
"""
        py = decompile(mlog)
        ast.parse(py)
        # Multiple uses: do not duplicate computation
        self.assertIn("__tmp0 = a + b", py)
        self.assertIn("x = __tmp0 * 2", py)
        self.assertIn("y = __tmp0 + 3", py)

    # -----------------------------------------------------------------------
    # 5. Expressions in If & While Conditions
    # -----------------------------------------------------------------------

    def test_expression_in_if_condition(self):
        """Test temporary calculation feeding into an if condition."""
        mlog = """
op add __tmp0 x 1
jump 3 lessThanEq __tmp0 5
set y 10
"""
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("if x + 1 > 5:", py)
        self.assertIn("y = 10", py)
        self.assertNotIn("__tmp0", py)

    def test_expression_in_while_condition(self):
        """Test temporary calculation feeding into a while loop condition."""
        mlog = """
set i 0
op add __tmp0 i 1
jump 5 greaterThanEq __tmp0 10
op add i i 1
jump 1 always 0 0
"""
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("while i + 1 < 10:", py)
        self.assertIn("i = i + 1", py)
        self.assertNotIn("__tmp0", py)

    def test_expressions_inside_if_and_while_bodies(self):
        """Test arithmetic chains inside structured blocks."""
        code = """
count = 0
while count < 10:
    val = count * 2
    if val > 5:
        target = (val + 1) * 3
    else:
        target = val - 1
    count = count + 1
"""
        compiled = compile_py(code)
        py = decompile(compiled.mlog)
        ast.parse(py)
        self.assertIn("count = 0", py)
        self.assertIn("while count < 10:", py)
        self.assertIn("val = count * 2", py)
        self.assertIn("if val > 5:", py)
        self.assertIn("target = (val + 1) * 3", py)
        self.assertIn("target = val - 1", py)
        self.assertIn("count = count + 1", py)

    # -----------------------------------------------------------------------
    # 6. Unknown Opcodes & Zero Guessing Principle
    # -----------------------------------------------------------------------

    def test_unknown_opcode_preservation(self):
        """Test that non-arithmetic or un-inferable opcodes are strictly preserved as raw calls."""
        mlog = """
ucontrol move x y 0 0 0
draw clear 0 0 0 0 0 0
sensor hp vault1 @health
packcolor col 1 0 0 1
"""
        py = decompile(mlog)
        # Verify instructions remain valid without making assumptions or inventing APIs
        self.assertIn('ucontrol("move", x, y, 0, 0, 0)', py)
        self.assertIn('draw("clear", 0, 0, 0, 0, 0, 0)', py)
        self.assertIn("col = packcolor(1, 0, 0, 1)", py)

    # -----------------------------------------------------------------------
    # 7. End-to-End Round-Trip Regression Tests (mlog -> Python -> compiler -> mlog)
    # -----------------------------------------------------------------------

    def test_round_trip_arithmetic(self):
        """Test full round trip: Python -> mlog -> decompiled Python -> mlog."""
        original_py = """
x = 10
y = x + 20
z = (x + y) * 2
"""
        mlog_1 = compile_py(original_py).mlog
        decompiled_py = decompile(mlog_1)
        mlog_2 = compile_py(decompiled_py).mlog
        self.assertEqual(mlog_1.strip(), mlog_2.strip())

    def test_round_trip_branching(self):
        """Test full round trip for if-else with arithmetic."""
        original_py = """
a = 15
if a > 10:
    b = a * 2
else:
    b = a + 5
c = b - 1
"""
        mlog_1 = compile_py(original_py).mlog
        decompiled_py = decompile(mlog_1)
        mlog_2 = compile_py(decompiled_py).mlog
        self.assertEqual(mlog_1.strip(), mlog_2.strip())

    def test_round_trip_while_loop(self):
        """Test full round trip for while loop with arithmetic and break."""
        original_py = """
i = 0
total = 0
while i < 10:
    if i == 5:
        break
    total = total + i
    i = i + 1
"""
        mlog_1 = compile_py(original_py).mlog
        decompiled_py = decompile(mlog_1)
        mlog_2 = compile_py(decompiled_py).mlog
        self.assertEqual(mlog_1.strip(), mlog_2.strip())


if __name__ == "__main__":
    unittest.main()
