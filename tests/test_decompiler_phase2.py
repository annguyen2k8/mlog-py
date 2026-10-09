"""Phase 2 Unit Tests: Structured Control Flow Recovery.

Tests recovery of if, if/else, elif, while, break, continue, nested if,
nested while, break/continue isolation, empty branches (pass), forward/backward jumps,
and graceful fallback on irreducible/unstructured CFGs.
"""

import ast
import unittest

from src.decompiler import (
    BreakNode,
    ContinueNode,
    IfNode,
    InstructionNode,
    PassNode,
    StructuredProgram,
    UnstructuredNode,
    WhileNode,
    build_cfg,
    decompile_to_structured,
    structure_cfg,
)
from src.mlog import compile_py


class TestDecompilerPhase2(unittest.TestCase):
    """Test suite for Phase 2 structured control flow reconstruction."""

    # -----------------------------------------------------------------------
    # 1. If, If-Else, Elif
    # -----------------------------------------------------------------------

    def test_simple_if(self):
        """Test simple if statement without else."""
        mlog = """
jump 2 notEqual a 1
set x 10
set z 20
"""
        prog = decompile_to_structured(mlog)
        self.assertTrue(prog.is_fully_structured)
        self.assertEqual(len(prog.body), 2)
        if_node = prog.body[0]
        self.assertIsInstance(if_node, IfNode)
        self.assertEqual(if_node.condition_str, "a == 1")
        self.assertEqual(len(if_node.then_body), 1)
        self.assertEqual(len(if_node.else_body), 0)
        self.assertFalse(if_node.is_elif)

        py = prog.to_python()
        ast.parse(py)  # Must be valid Python
        self.assertIn("if a == 1:", py)
        self.assertIn("x = 10", py)
        self.assertIn("z = 20", py)

    def test_if_else(self):
        """Test if-else statement with both branches."""
        mlog = """
jump 3 notEqual a 1
set x 10
jump 4 always 0 0
set x 20
set z 30
"""
        prog = decompile_to_structured(mlog)
        self.assertTrue(prog.is_fully_structured)
        self.assertEqual(len(prog.body), 2)
        if_node = prog.body[0]
        self.assertIsInstance(if_node, IfNode)
        self.assertEqual(if_node.condition_str, "a == 1")
        self.assertEqual(len(if_node.then_body), 1)
        self.assertEqual(len(if_node.else_body), 1)

        py = prog.to_python()
        ast.parse(py)
        self.assertIn("if a == 1:", py)
        self.assertIn("else:", py)
        self.assertIn("x = 10", py)
        self.assertIn("x = 20", py)

    def test_elif_chain(self):
        """Test if / elif / else chain."""
        code = """
if cmd == 1:
    act = 10
elif cmd == 2:
    act = 20
elif cmd == 3:
    act = 30
else:
    act = 0
final = act
"""
        compiled = compile_py(code)
        prog = decompile_to_structured(compiled.mlog)
        self.assertTrue(prog.is_fully_structured)

        py = prog.to_python()
        ast.parse(py)
        self.assertIn("if cmd == 1:", py)
        self.assertIn("elif cmd == 2:", py)
        self.assertIn("elif cmd == 3:", py)
        self.assertIn("else:", py)
        self.assertIn("act = 0", py)
        self.assertIn("final = act", py)

    # -----------------------------------------------------------------------
    # 2. Nested If Statements
    # -----------------------------------------------------------------------

    def test_nested_if_two_levels(self):
        """Test nested if inside another if branch."""
        code = """
if a == 1:
    if b == 2:
        x = 10
    else:
        x = 20
else:
    x = 30
"""
        compiled = compile_py(code)
        prog = decompile_to_structured(compiled.mlog)
        self.assertTrue(prog.is_fully_structured)

        py = prog.to_python()
        ast.parse(py)
        self.assertIn("if a == 1:", py)
        self.assertIn("if b == 2:", py)
        self.assertIn("x = 10", py)
        self.assertIn("x = 20", py)
        self.assertIn("x = 30", py)

    def test_nested_if_three_levels(self):
        """Test deeply nested if statements (3 levels)."""
        code = """
if a == 1:
    if b == 2:
        if c == 3:
            x = 10
        else:
            x = 20
    else:
        x = 30
else:
    x = 40
"""
        compiled = compile_py(code)
        prog = decompile_to_structured(compiled.mlog)
        self.assertTrue(prog.is_fully_structured)

        py = prog.to_python()
        ast.parse(py)
        self.assertIn("if a == 1:", py)
        self.assertIn("if b == 2:", py)
        self.assertIn("if c == 3:", py)
        self.assertIn("x = 10", py)
        self.assertIn("x = 40", py)

    # -----------------------------------------------------------------------
    # 3. While Loops & Nested Loops
    # -----------------------------------------------------------------------

    def test_simple_while_loop(self):
        """Test basic while loop with forward condition and backward jump."""
        mlog = """
set i 0
jump 4 greaterThanEq i 10
op add i i 1
jump 1 always 0 0
set z 5
"""
        prog = decompile_to_structured(mlog)
        self.assertTrue(prog.is_fully_structured)
        self.assertEqual(len(prog.body), 3)
        while_node = prog.body[1]
        self.assertIsInstance(while_node, WhileNode)
        self.assertEqual(while_node.condition_str, "i < 10")
        self.assertEqual(len(while_node.body), 1)

        py = prog.to_python()
        ast.parse(py)
        self.assertIn("while i < 10:", py)
        self.assertIn('i = op("add", i, 1)', py)
        self.assertIn("z = 5", py)

    def test_while_true_infinite_loop(self):
        """Test while True loop."""
        code = """
while True:
    x = 1
    if x == 1:
        break
y = 2
"""
        compiled = compile_py(code)
        prog = decompile_to_structured(compiled.mlog)
        self.assertTrue(prog.is_fully_structured)

        py = prog.to_python()
        ast.parse(py)
        self.assertIn("while True:", py)
        self.assertIn("break", py)
        self.assertIn("y = 2", py)

    def test_nested_while_two_levels(self):
        """Test two nested while loops."""
        code = """
i = 0
while i < 10:
    j = 0
    while j < 5:
        j = j + 1
    i = i + 1
"""
        compiled = compile_py(code)
        prog = decompile_to_structured(compiled.mlog)
        self.assertTrue(prog.is_fully_structured)

        py = prog.to_python()
        ast.parse(py)
        self.assertIn("while i < 10:", py)
        self.assertIn("while j < 5:", py)

    def test_nested_while_three_levels(self):
        """Test three nested while loops."""
        code = """
i = 0
while i < 10:
    j = 0
    while j < 5:
        k = 0
        while k < 3:
            k = k + 1
        j = j + 1
    i = i + 1
"""
        compiled = compile_py(code)
        prog = decompile_to_structured(compiled.mlog)
        self.assertTrue(prog.is_fully_structured)

        py = prog.to_python()
        ast.parse(py)
        self.assertIn("while i < 10:", py)
        self.assertIn("while j < 5:", py)
        self.assertIn("while k < 3:", py)

    # -----------------------------------------------------------------------
    # 4. Break & Continue in Loops
    # -----------------------------------------------------------------------

    def test_break_in_loop(self):
        """Test break statement inside loop."""
        code = """
i = 0
while i < 10:
    if i == 5:
        break
    i = i + 1
"""
        compiled = compile_py(code)
        prog = decompile_to_structured(compiled.mlog)
        self.assertTrue(prog.is_fully_structured)

        py = prog.to_python()
        ast.parse(py)
        self.assertIn("while i < 10:", py)
        self.assertIn("if i == 5:", py)
        self.assertIn("break", py)

    def test_continue_in_loop(self):
        """Test continue statement inside loop."""
        code = """
i = 0
while i < 10:
    if i == 5:
        continue
    i = i + 1
"""
        compiled = compile_py(code)
        prog = decompile_to_structured(compiled.mlog)
        self.assertTrue(prog.is_fully_structured)

        py = prog.to_python()
        ast.parse(py)
        self.assertIn("while i < 10:", py)
        self.assertIn("if i == 5:", py)
        self.assertIn("continue", py)

    def test_if_inside_loop_with_both_break_and_continue(self):
        """Test while loop with multiple if branches having break and continue."""
        code = """
i = 0
while i < 100:
    i = i + 1
    if i == 50:
        continue
    if i == 80:
        break
    x = i * 2
"""
        compiled = compile_py(code)
        prog = decompile_to_structured(compiled.mlog)
        self.assertTrue(prog.is_fully_structured)

        py = prog.to_python()
        ast.parse(py)
        self.assertIn("continue", py)
        self.assertIn("break", py)

    def test_nested_loops_break_isolation(self):
        """Test that break inside inner loop isolates to inner loop exit."""
        code = """
outer = 0
while outer < 3:
    inner = 0
    while inner < 3:
        if inner == 1:
            break
        inner = inner + 1
    outer = outer + 1
"""
        compiled = compile_py(code)
        prog = decompile_to_structured(compiled.mlog)
        self.assertTrue(prog.is_fully_structured)

        py = prog.to_python()
        tree = ast.parse(py)
        # Verify outer loop contains an inner While node, which contains the Break
        outer_while = None
        for stmt in tree.body:
            if isinstance(stmt, ast.While):
                outer_while = stmt
                break
        self.assertIsNotNone(outer_while)
        inner_while = None
        for stmt in outer_while.body:
            if isinstance(stmt, ast.While):
                inner_while = stmt
                break
        self.assertIsNotNone(inner_while)

    def test_nested_loops_continue_isolation(self):
        """Test that continue inside inner loop isolates to inner loop header."""
        code = """
outer = 0
while outer < 3:
    inner = 0
    while inner < 3:
        inner = inner + 1
        if inner == 2:
            continue
    outer = outer + 1
"""
        compiled = compile_py(code)
        prog = decompile_to_structured(compiled.mlog)
        self.assertTrue(prog.is_fully_structured)

        py = prog.to_python()
        ast.parse(py)
        self.assertIn("continue", py)

    # -----------------------------------------------------------------------
    # 5. Composite Control Flow (Loop in If, If in Loop)
    # -----------------------------------------------------------------------

    def test_while_inside_if(self):
        """Test while loop nested inside an if branch."""
        code = """
flag = 1
if flag == 1:
    count = 0
    while count < 5:
        count = count + 1
else:
    count = -1
"""
        compiled = compile_py(code)
        prog = decompile_to_structured(compiled.mlog)
        self.assertTrue(prog.is_fully_structured)

        py = prog.to_python()
        ast.parse(py)
        self.assertIn("if flag == 1:", py)
        self.assertIn("while count < 5:", py)
        self.assertIn("else:", py)

    # -----------------------------------------------------------------------
    # 6. Empty Branches (Pass)
    # -----------------------------------------------------------------------

    def test_empty_branch_if_pass(self):
        """Test that empty if branch generates pass."""
        mlog = """
jump 1 notEqual x 1
set y 2
"""
        prog = decompile_to_structured(mlog)
        self.assertTrue(prog.is_fully_structured)
        if_node = prog.body[0]
        self.assertIsInstance(if_node, IfNode)
        self.assertEqual(len(if_node.then_body), 1)
        self.assertIsInstance(if_node.then_body[0], PassNode)

        py = prog.to_python()
        ast.parse(py)
        self.assertIn("if x == 1:", py)
        self.assertIn("pass", py)

    def test_empty_branches_elif_and_while(self):
        """Test empty pass branches in elif and while."""
        code = """
if x == 1:
    pass
elif x == 2:
    pass
else:
    pass

while x < 5:
    pass
"""
        compiled = compile_py(code)
        prog = decompile_to_structured(compiled.mlog)
        self.assertTrue(prog.is_fully_structured)

        py = prog.to_python()
        ast.parse(py)
        self.assertIn("pass", py)

    # -----------------------------------------------------------------------
    # 7. Unstructured & Irreducible CFGs (Semantic Preservation / Fallback)
    # -----------------------------------------------------------------------

    def test_irreducible_cfg_two_loop_entries(self):
        """Test that a CFG with two entries into a cycle is flagged as irreducible."""
        mlog = """
jump 2 equal a 1
set x 1
jump 3 always 0 0
set x 2
jump 1 equal x 1
"""
        prog = decompile_to_structured(mlog)
        self.assertFalse(prog.is_fully_structured)
        self.assertGreater(len(prog.unstructured_reasons), 0)
        self.assertTrue(any("Irreducible" in r for r in prog.unstructured_reasons))

        py = prog.to_python()
        # Fallback must be emitted without crashing
        self.assertIn("[UNSTRUCTURED REGION]", py)
        self.assertIn("jump(", py)

    def test_cross_loop_jump_fallback(self):
        """Test that jumping across loop boundaries to an outer loop triggers fallback."""
        # Instruction 2 jumps directly to 7 (outer loop exit), bypassing inner loop
        mlog = """
jump 7 greaterThanEq outer 3
jump 5 greaterThanEq inner 3
jump 7 always 0 0
jump 1 always 0 0
op add outer outer 1
jump 0 always 0 0
set end 1
"""
        prog = decompile_to_structured(mlog)
        self.assertFalse(prog.is_fully_structured)
        py = prog.to_python()
        self.assertIn("[UNSTRUCTURED REGION]", py)

    def test_arbitrary_unstructured_forward_jump(self):
        """Test that jumping forward into the middle of an if body triggers fallback."""
        mlog = """
jump 3 always 0 0
jump 4 notEqual a 1
set x 10
set y 20
set z 30
"""
        prog = decompile_to_structured(mlog)
        self.assertFalse(prog.is_fully_structured)
        py = prog.to_python()
        self.assertIn("[UNSTRUCTURED REGION]", py)

    # -----------------------------------------------------------------------
    # 8. Regression: End-to-End Compile -> Decompile Integrity
    # -----------------------------------------------------------------------

    def test_multiple_breaks_and_continues_in_elif_chain(self):
        """Test complex loop with elif chain containing multiple breaks and continues."""
        code = """
while running:
    if a == 1:
        continue
    elif a == 2:
        break
    elif a == 3:
        continue
    elif a == 4:
        break
    else:
        op('add', total, total, 1)
"""
        compiled = compile_py(code)
        prog = decompile_to_structured(compiled.mlog)
        self.assertTrue(prog.is_fully_structured)

        py = prog.to_python()
        ast.parse(py)
        self.assertIn("while running != 0:", py)
        self.assertIn("elif a == 2:", py)
        self.assertIn("elif a == 4:", py)


if __name__ == "__main__":
    unittest.main()
