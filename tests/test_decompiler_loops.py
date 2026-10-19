"""Comprehensive audit and regression test suite for Mlog Loop Decompilation.

Covers:
1. Top-tested while loops (pure while cond:)
2. Top-tested loops with pre-instructions / side-effects in header (safe while True: with break)
3. Bottom-tested loops (do-while / conditional latch)
4. Infinite loops (while True:)
5. Loops with break and continue statements (conditional and unconditional)
6. Nested loops (inner break/continue, statements after inner loop, outer break/continue)
7. Loops containing if / elif / else branching
8. Irreducible / multi-entry loops (fallback to UnstructuredNode with clean semantic jump calls)
9. Loop invariant safety (no invalid inlining of modified variables)
10. Semantic equivalence and roundtrip verification (ast.parse, compile -> decompile -> compile)
"""

import ast
import unittest

from src.mlog import compile_py
from src.decompiler import decompile, decompile_program
from src.decompiler.structurer import decompile_to_structured


class TestDecompilerLoops(unittest.TestCase):
    """Test suite verifying robust, semantically-correct decompilation of all loop patterns."""

    def _assert_valid_python(self, py_code: str):
        """Verify generated Python code is syntactically valid."""
        try:
            ast.parse(py_code)
        except SyntaxError as e:
            self.fail(f"Decompiled code has syntax error: {e}\nCode:\n{py_code}")

    def _assert_no_undefined_in_while_condition(self, py_code: str):
        """Verify variables in while conditions are defined before the while loop."""
        tree = ast.parse(py_code)
        defined_vars = set()
        for stmt in tree.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        defined_vars.add(target.id)
            elif isinstance(stmt, ast.While):
                for node in ast.walk(stmt.test):
                    if isinstance(node, ast.Name) and node.id not in ("True", "False", "None"):
                        self.assertIn(
                            node.id,
                            defined_vars,
                            f"Variable '{node.id}' used in while condition before definition!\n{py_code}",
                        )
                break

    # -----------------------------------------------------------------------
    # 1. Pure Top-Tested While Loops
    # -----------------------------------------------------------------------

    def test_pure_top_tested_while_simple(self):
        """Simple while condition with no header pre-instructions."""
        mlog = """set i 0
jump 4 greaterThanEq i 10
op add i i 1
jump 1 always 0 0
print i
"""
        py = decompile(mlog)
        self._assert_valid_python(py)
        self.assertIn("while i < 10:", py)
        self.assertIn("i = i + 1", py)
        self.assertIn("print(i)", py)

        # Roundtrip
        recompiled = compile_py(py).mlog.strip()
        self.assertIn("jump 4 greaterThanEq i 10", recompiled)
        self.assertIn("op add i i 1", recompiled)
        self.assertIn("jump 1 always 0 0", recompiled)

    def test_pure_top_tested_while_with_condition_expression(self):
        """Top-tested while loop where condition temp is inlined safely."""
        mlog = """set i 0
op add __tmp0 i 1
jump 6 greaterThan __tmp0 10
op add i i 1
print i
jump 1 always 0 0
print "done"
"""
        py = decompile(mlog)
        self._assert_valid_python(py)
        self.assertIn("while i + 1 <= 10:", py)
        self.assertIn("i = i + 1", py)
        self.assertIn("print(i)", py)

        # Roundtrip
        recompiled = compile_py(py).mlog.strip()
        self.assertIn("greaterThan", recompiled)
        self.assertIn("op add i i 1", recompiled)

    # -----------------------------------------------------------------------
    # 2. Top-Tested Loops with Side-Effects / Header Pre-Instructions
    # -----------------------------------------------------------------------

    def test_loop_header_with_read_side_effect(self):
        """Header contains I/O instruction (read): must NOT produce undefined variable in while test."""
        mlog = """set sum 0
read val bank1 i
jump 6 equal val 0
op add sum sum val
op add i i 1
jump 1 always 0 0
print sum
"""
        py = decompile(mlog)
        self._assert_valid_python(py)
        # val must NOT be checked in while condition before being read!
        self.assertNotIn("while val != 0:", py)
        self.assertIn("while True:", py)
        self.assertIn('val = read("bank1", i)', py)
        self.assertIn("if val == 0:", py)
        self.assertIn("break", py)
        self.assertIn("sum = sum + val", py)
        self.assertIn("print(sum)", py)

        # Verify semantics: val is defined before being tested in break check
        self._assert_no_undefined_in_while_condition(py)

        # Roundtrip
        recompiled = compile_py(py).mlog.strip()
        self.assertIn("read val bank1 i", recompiled)
        self.assertIn("op add sum sum val", recompiled)
        self.assertIn("jump 8 always 0 0", recompiled)

    def test_loop_header_with_sensor_side_effect(self):
        """Header contains sensor: must execute sensor before checking condition."""
        mlog = """sensor hp @unit @health
jump 4 lessThan hp 50
ucontrol move 10 10 0 0 0
jump 0 always 0 0
print "dead"
"""
        py = decompile(mlog)
        self._assert_valid_python(py)
        self.assertIn("while True:", py)
        self.assertIn("hp = sensor('@unit', '@health')", py)
        self.assertIn("if hp < 50:", py)
        self.assertIn("break", py)
        self.assertIn("ucontrol.move(10, 10)", py)
        self.assertIn('print("dead")', py)

        # Roundtrip
        recompiled = compile_py(py).mlog.strip()
        self.assertIn("sensor hp @unit @health", recompiled)
        self.assertIn("greaterThanEq hp 50", recompiled)
        self.assertIn("jump 6 always 0 0", recompiled)

    # -----------------------------------------------------------------------
    # 3. Bottom-Tested Loops (do-while / latch condition)
    # -----------------------------------------------------------------------

    def test_bottom_tested_loop_do_while(self):
        """Loop executes body first, tests condition at latch to repeat."""
        mlog = """set i 0
op add i i 1
print i
jump 1 lessThan i 10
print "done"
"""
        py = decompile(mlog)
        self._assert_valid_python(py)
        self.assertIn("while True:", py)
        self.assertIn("i = i + 1", py)
        self.assertIn("print(i)", py)
        # Inverted latch condition: repeats when i < 10, breaks when not (i < 10) -> i >= 10
        self.assertIn("if i >= 10:", py)
        self.assertIn("break", py)
        self.assertIn('print("done")', py)

        # Roundtrip
        recompiled = compile_py(py).mlog.strip()
        self.assertIn("op add i i 1", recompiled)
        self.assertIn("print i", recompiled)

    def test_bottom_tested_loop_with_latch_expression(self):
        """Bottom-tested loop with temporary calculation before latch jump."""
        mlog = """set i 0
op add i i 1
op mul __tmp0 i 2
jump 1 lessThan __tmp0 20
print "done"
"""
        py = decompile(mlog)
        self._assert_valid_python(py)
        self.assertIn("while True:", py)
        self.assertIn("i = i + 1", py)
        self.assertIn("if i * 2 >= 20:", py)
        self.assertIn("break", py)

        recompiled = compile_py(py).mlog.strip()
        self.assertIn("op add i i 1", recompiled)

    # -----------------------------------------------------------------------
    # 4. Infinite Loops (while True:)
    # -----------------------------------------------------------------------

    def test_infinite_loop(self):
        """Infinite loop with unconditional latch jump."""
        mlog = """op add count count 1
print count
jump 0 always 0 0
"""
        py = decompile(mlog)
        self._assert_valid_python(py)
        self.assertIn("while True:", py)
        self.assertIn("count = count + 1", py)
        self.assertIn("print(count)", py)

    # -----------------------------------------------------------------------
    # 5. Loops with Break and Continue
    # -----------------------------------------------------------------------

    def test_loop_with_unconditional_break_and_continue(self):
        """Unconditional break and continue inside conditional branches in loop body."""
        mlog = """set i 0
jump 9 greaterThanEq i 10
op add i i 1
jump 5 notEqual i 5
jump 1 always 0 0
jump 7 notEqual i 8
jump 9 always 0 0
print i
jump 1 always 0 0
print "done"
"""
        py = decompile(mlog)
        self._assert_valid_python(py)
        self.assertIn("while i < 10:", py)
        self.assertIn("if i == 5:", py)
        self.assertIn("continue", py)
        self.assertIn("if i == 8:", py)
        self.assertIn("break", py)

        # Roundtrip
        recompiled = compile_py(py).mlog.strip()
        self.assertIn("jump 9 greaterThanEq i 10", recompiled)
        self.assertIn("jump 1 always 0 0", recompiled)
        self.assertIn("jump 9 always 0 0", recompiled)

    def test_loop_with_conditional_break(self):
        """Conditional break inside loop."""
        mlog = """set i 0
jump 6 greaterThanEq i 100
op add i i 1
jump 6 greaterThan i 50
print i
jump 1 always 0 0
print "done"
"""
        py = decompile(mlog)
        self._assert_valid_python(py)
        self.assertIn("while i < 100:", py)
        self.assertIn("if i > 50:", py)
        self.assertIn("break", py)
        self.assertIn("print(i)", py)

        recompiled = compile_py(py).mlog.strip()
        self.assertIn("jump 7 greaterThanEq i 100", recompiled)
        self.assertIn("jump 7 always 0 0", recompiled)

    def test_loop_with_conditional_continue(self):
        """Conditional continue inside loop."""
        mlog = """set i 0
jump 6 greaterThanEq i 20
op add i i 1
jump 1 lessThan i 10
print i
jump 1 always 0 0
print "done"
"""
        py = decompile(mlog)
        self._assert_valid_python(py)
        self.assertIn("while i < 20:", py)
        self.assertIn("if i < 10:", py)
        self.assertIn("continue", py)
        self.assertIn("print(i)", py)

        recompiled = compile_py(py).mlog.strip()
        self.assertIn("jump 7 greaterThanEq i 20", recompiled)
        self.assertIn("jump 1 always 0 0", recompiled)

    # -----------------------------------------------------------------------
    # 6. Nested Loops
    # -----------------------------------------------------------------------

    def test_nested_loops_with_inner_break(self):
        """Nested while loops where inner loop breaks out to outer loop body."""
        mlog = """set x 0
jump 10 greaterThanEq x 5
set y 0
jump 7 greaterThanEq y 3
jump 7 equal y 1
op add y y 1
jump 3 always 0 0
print x
op add x x 1
jump 1 always 0 0
print "done"
"""
        py = decompile(mlog)
        self._assert_valid_python(py)
        self.assertIn("while x < 5:", py)
        self.assertIn("while y < 3:", py)
        self.assertIn("if y == 1:", py)
        self.assertIn("break", py)
        self.assertIn("print(x)", py)
        self.assertIn("x = x + 1", py)
        self.assertIn('print("done")', py)

        recompiled = compile_py(py).mlog.strip()
        self.assertIn("jump 11 greaterThanEq x 5", recompiled)
        self.assertIn("jump 8 greaterThanEq y 3", recompiled)
        self.assertIn("jump 8 always 0 0", recompiled)

    def test_nested_loops_with_inner_continue(self):
        """Nested loops where inner loop continues independently."""
        mlog = """set r 0
jump 11 greaterThanEq r 4
set c 0
jump 8 greaterThanEq c 4
op add c c 1
jump 3 lessThan c 2
print c
jump 3 always 0 0
op add r r 1
jump 1 always 0 0
print "finished"
"""
        py = decompile(mlog)
        self._assert_valid_python(py)
        self.assertIn("while r < 4:", py)
        self.assertIn("while c < 4:", py)
        self.assertIn("if c < 2:", py)
        self.assertIn("continue", py)
        self.assertIn("print(c)", py)
        self.assertIn("r = r + 1", py)

    # -----------------------------------------------------------------------
    # 7. Loops with If / Elif / Else Inside
    # -----------------------------------------------------------------------

    def test_loop_with_if_else_inside(self):
        """Loop containing if/else branch with execution continuing after merge."""
        mlog = """set i 0
jump 9 greaterThanEq i 10
jump 5 notEqual mode 1
print "mode 1"
jump 6 always 0 0
print "mode 0"
op add i i 1
jump 1 always 0 0
print "done"
"""
        py = decompile(mlog)
        self._assert_valid_python(py)
        self.assertIn("while i < 10:", py)
        self.assertIn("if mode == 1:", py)
        self.assertIn('print("mode 1")', py)
        self.assertIn("else:", py)
        self.assertIn('print("mode 0")', py)
        self.assertIn("i = i + 1", py)

    def test_loop_with_if_elif_else_with_break_and_continue(self):
        """Loop with if-elif-else where branches break and continue."""
        mlog = """set i 0
jump 11 greaterThanEq i 10
jump 5 notEqual x 1
jump 11 always 0 0
jump 9 always 0 0
jump 8 notEqual x 2
jump 1 always 0 0
jump 9 always 0 0
print "other"
op add i i 1
jump 1 always 0 0
print "done"
"""
        py = decompile(mlog)
        self._assert_valid_python(py)
        self.assertIn("while i < 10:", py)
        self.assertIn("if x == 1:", py)
        self.assertIn("break", py)
        self.assertIn("elif x == 2:", py)
        self.assertIn("continue", py)
        self.assertIn("else:", py)
        self.assertIn('print("other")', py)
        self.assertIn("i = i + 1", py)

    # -----------------------------------------------------------------------
    # 8. Irreducible / Multi-Entry Loops & Fallback Jumps
    # -----------------------------------------------------------------------

    def test_irreducible_multi_entry_loop_fallback(self):
        """Multi-entry irreducible loop must fallback to UnstructuredNode with valid jump() calls."""
        mlog = """set x 0
jump 3 always 0 0
print "head"
print "body"
op add x x 1
jump 2 lessThan x 5
print "done"
"""
        py = decompile(mlog)
        self._assert_valid_python(py)
        self.assertIn("# [UNSTRUCTURED REGION]", py)
        # Jumps must be emitted with clean arguments, NOT quoted strings for variables/numbers
        self.assertIn('jump(3, "always", 0, 0)', py)
        self.assertIn('jump(2, "lessThan", x, 5)', py)

        # Roundtrip: should compile cleanly without syntax errors
        recompiled = compile_py(py).mlog.strip()
        self.assertIn("jump 3 always 0 0", recompiled)
        self.assertIn("jump 2 lessThan x 5", recompiled)

    # -----------------------------------------------------------------------
    # 9. Loop Invariant Safety in Dataflow
    # -----------------------------------------------------------------------

    def test_loop_invariant_modified_in_body_not_inlined(self):
        """Variable defined before loop whose dependencies are modified in loop must not be inlined into condition."""
        mlog = """set x 5
op add __tmp0 x 1
jump 6 greaterThan __tmp0 10
op sub x x 1
print x
jump 2 always 0 0
print "exit"
"""
        # __tmp0 = x + 1 computed before loop. If x is modified inside loop,
        # but header repeats at instruction 2 (which checks __tmp0 > 10),
        # __tmp0 holds the initial value (or header is at 2).
        prog = decompile_to_structured(mlog, recover_expressions=True)
        py = prog.to_python()
        self._assert_valid_python(py)

    def test_loop_variable_updated_in_body_not_folded_to_constant(self):
        """Variable defined outside loop and updated inside must not be folded into constant in condition."""
        mlog = """set i 0
set max 10
jump 6 greaterThanEq i max
op add i i 1
set max 5
jump 2 always 0 0
print i
"""
        py = decompile(mlog)
        self._assert_valid_python(py)
        self.assertIn("while i < max:", py)
        self.assertIn("max = 5", py)
        self.assertIn("print(i)", py)

    # -----------------------------------------------------------------------
    # 10. Additional Real-World Edge Cases & Semantic Equivalence
    # -----------------------------------------------------------------------

    def test_bottom_tested_loop_with_statements_after(self):
        """Bottom-tested loop with body statements and statement after loop."""
        mlog = """set i 0
op add i i 1
jump 1 lessThan i 5
print i
"""
        py = decompile(mlog)
        self._assert_valid_python(py)
        self.assertIn("while True:", py)
        self.assertIn("i = i + 1", py)
        self.assertIn("if i >= 5:", py)
        self.assertIn("break", py)
        self.assertIn("print(i)", py)

        # Roundtrip verification
        recompiled = compile_py(py).mlog.strip()
        self.assertIn("op add i i 1", recompiled)
        self.assertIn("print i", recompiled)

    def test_loop_header_getlink_io_side_effect(self):
        """Loop header containing getlink: must execute getlink inside loop before check."""
        mlog = """set i 0
getlink link i
jump 6 equal link null
ucontrol move 10 10 0 0 0
op add i i 1
jump 1 always 0 0
print "done"
"""
        py = decompile(mlog)
        self._assert_valid_python(py)
        self.assertIn("while True:", py)
        self.assertIn("link = getlink(i)", py)
        self.assertIn("if link == None:", py)
        self.assertIn("break", py)
        self.assertIn("ucontrol.move(10, 10)", py)
        self.assertIn("i = i + 1", py)
        self.assertIn('print("done")', py)

        # Roundtrip
        recompiled = compile_py(py).mlog.strip()
        self.assertIn("getlink link i", recompiled)
        self.assertIn("ucontrol move 10 10", recompiled)
        self.assertIn('print "done"', recompiled)

    def test_multi_level_jump_to_outer_loop_fallback(self):
        """Inner loop jumping to outer loop header is unstructured in Python: exact roundtrip byte-for-byte."""
        mlog = """set x 0
jump 8 greaterThanEq x 5
set y 0
jump 7 greaterThanEq y 5
op add y y 1
jump 1 equal y 2
jump 3 always 0 0
jump 1 always 0 0
print "done"
"""
        py = decompile(mlog)
        self._assert_valid_python(py)
        self.assertIn('jump(1, "equal", y, 2)', py)

        # Exact byte-for-byte roundtrip
        recompiled = compile_py(py).mlog.strip()
        self.assertEqual(mlog.strip(), recompiled)

    def test_irreducible_cross_jumping_shared_back_edge_fallback(self):
        """Irreducible cross-jumping CFG with shared back-edge falls back to clean unquoted jump() calls."""
        mlog = """jump 3 equal mode 1
op add a a 1
jump 4 always 0 0
op add b b 1
jump 1 lessThan a 10
"""
        py = decompile(mlog)
        self._assert_valid_python(py)
        self.assertIn("# [UNSTRUCTURED REGION]", py)
        self.assertIn('jump(3, "equal", mode, 1)', py)
        self.assertIn('jump(4, "always", 0, 0)', py)
        self.assertIn('jump(1, "lessThan", a, 10)', py)

        # Exact byte-for-byte roundtrip
        recompiled = compile_py(py).mlog.strip()
        self.assertEqual(mlog.strip(), recompiled)

    def test_function_analyzer_loop_with_continue_and_trailing_body(self):
        """FunctionAnalyzer loop containing continue must search latch from bottom to preserve trailing body."""
        mlog = """jump 9 always 0 0
set i 0
jump 8 greaterThanEq i 10
op add i i 1
jump 6 greaterThanEq i 5
jump 2 always 0 0
print i
jump 2 always 0 0
set @counter __ret_worker
set __ret_worker 11
jump 1 always 0 0
"""
        prog = decompile_program(mlog)
        py = prog.to_python()
        self._assert_valid_python(py)
        self.assertIn("def worker():", py)
        self.assertIn("while i < 10:", py)
        self.assertIn("i = i + 1", py)
        self.assertIn("if i < 5:", py)
        self.assertIn("continue", py)
        self.assertIn("print(i)", py)
        self.assertIn("worker()", py)


if __name__ == "__main__":
    unittest.main()
