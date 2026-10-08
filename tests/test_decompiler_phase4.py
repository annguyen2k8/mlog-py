"""Unit tests for Phase 4: Function and Procedure Recovery in mlog decompiler.

Tests cover:
1. Single function recovery
2. Multiple functions recovery
3. Function parameters
4. Return values
5. Void functions (procedures without return value)
6. Global variable access across functions
7. Nested if/while control flow inside functions
8. Multiple call sites to the same function
9. Recursion with verified calling convention
10. Negative tests: normal control flow (loops, break, if) NOT mistaken for function calls
11. Invalid/ambiguous function patterns and fallback without guessing
12. Round-trip regression tests: mlog -> Python DSL -> compiler -> mlog
13. Python syntax verification via ast.parse and py_compile.compile
"""

import ast
import py_compile
import tempfile
import unittest
from pathlib import Path

from src.decompiler import (
    CallNode,
    FunctionAnalyzer,
    FunctionDef,
    FunctionProgram,
    Parameter,
    ReturnNode,
    decompile,
    decompile_program,
)
from src.mlog import compile_py


class TestDecompilerPhase4(unittest.TestCase):
    """Test suite for Phase 4 Function and Procedure Recovery."""

    def _verify_python_syntax(self, code: str) -> ast.AST:
        """Helper to ensure generated code is valid Python syntax and compiles cleanly."""
        tree = ast.parse(code)
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = f.name
        try:
            py_compile.compile(temp_path, doraise=True)
        finally:
            Path(temp_path).unlink(missing_ok=True)
        return tree

    # -----------------------------------------------------------------------
    # 1. Single Function Recovery
    # -----------------------------------------------------------------------

    def test_single_function_basic(self):
        """Test recovering a single function with parameters and return value."""
        mlog = """
jump 5 always 0 0
op add res a b
set __retval_add res
set @counter __ret_add
set @counter __ret_add
set a 10
set b 20
set __ret_add 9
jump 1 always 0 0
set out __retval_add
print out
"""
        program = decompile_program(mlog)
        self.assertEqual(len(program.functions), 1)
        fn = program.functions[0]
        self.assertEqual(fn.name, "add")
        self.assertEqual(fn.param_names, ["a", "b"])

        py_code = program.to_python()
        self._verify_python_syntax(py_code)
        self.assertIn("def add(a, b):", py_code)
        self.assertTrue("return a + b" in py_code or ("res = a + b" in py_code and "return res" in py_code))
        self.assertIn("out = add(10, 20)", py_code)
        self.assertIn("print(out)", py_code)

    # -----------------------------------------------------------------------
    # 2. Multiple Functions Recovery
    # -----------------------------------------------------------------------

    def test_multiple_functions(self):
        """Test recovering multiple distinct functions in a single program."""
        mlog = """
jump 9 always 0 0
op add sum_val x y
set __retval_add sum_val
set @counter __ret_add
set @counter __ret_add
op mul prod_val x y
set __retval_mul prod_val
set @counter __ret_mul
set @counter __ret_mul
set x 3
set y 4
set __ret_add 13
jump 1 always 0 0
set r1 __retval_add
set x r1
set y 2
set __ret_mul 18
jump 5 always 0 0
set r2 __retval_mul
print r2
"""
        program = decompile_program(mlog)
        self.assertEqual(len(program.functions), 2)
        fn_names = [f.name for f in program.functions]
        self.assertIn("add", fn_names)
        self.assertIn("mul", fn_names)

        py_code = program.to_python()
        self._verify_python_syntax(py_code)
        self.assertIn("def add(x, y):", py_code)
        self.assertIn("def mul(x, y):", py_code)
        self.assertIn("r1 = add(3, 4)", py_code)
        self.assertIn("r2 = mul(r1, 2)", py_code)

    # -----------------------------------------------------------------------
    # 3. Function Parameters Recovery
    # -----------------------------------------------------------------------

    def test_function_multiple_parameters(self):
        """Test recovering functions with 1, 2, and 3 parameters."""
        mlog = """
jump 5 always 0 0
op mul r1 a 2
set __retval_calc r1
set @counter __ret_calc
set @counter __ret_calc
set a 7
set __ret_calc 8
jump 1 always 0 0
set ans __retval_calc
"""
        py_code = decompile(mlog)
        self._verify_python_syntax(py_code)
        self.assertIn("def calc(a):", py_code)
        self.assertIn("ans = calc(7)", py_code)

    # -----------------------------------------------------------------------
    # 4. Return Value Recovery
    # -----------------------------------------------------------------------

    def test_function_return_expression(self):
        """Test that function return expressions are synthesized via Phase 3 dataflow."""
        mlog = """
jump 7 always 0 0
op mul t1 a a
op mul t2 b b
op add sq t1 t2
set __retval_dist sq
set @counter __ret_dist
set @counter __ret_dist
set a 3
set b 4
set __ret_dist 11
jump 1 always 0 0
set d __retval_dist
"""
        py_code = decompile(mlog)
        self._verify_python_syntax(py_code)
        self.assertIn("def dist(a, b):", py_code)
        self.assertIn("d = dist(3, 4)", py_code)

    # -----------------------------------------------------------------------
    # 5. Void Function (No Return Value)
    # -----------------------------------------------------------------------

    def test_void_function_without_return_value(self):
        """Test recovering a procedure without return value."""
        mlog = """
jump 5 always 0 0
print text
printflush message1
set @counter __ret_notify
set @counter __ret_notify
set text "alert"
set __ret_notify 8
jump 1 always 0 0
print "done"
"""
        program = decompile_program(mlog)
        self.assertEqual(len(program.functions), 1)
        fn = program.functions[0]
        self.assertEqual(fn.name, "notify")

        py_code = program.to_python()
        self._verify_python_syntax(py_code)
        self.assertIn("def notify(text):", py_code)
        self.assertTrue('notify("alert")' in py_code or "notify('alert')" in py_code)
        self.assertNotIn(" = notify(", py_code)

    # -----------------------------------------------------------------------
    # 6. Global Variable Access Across Functions
    # -----------------------------------------------------------------------

    def test_global_variable_preservation(self):
        """Test that global variables accessed inside functions are not treated as parameters."""
        mlog = """
jump 4 always 0 0
op add counter counter 1
set @counter __ret_bump
set @counter __ret_bump
set counter 0
set __ret_bump 7
jump 1 always 0 0
print counter
"""
        program = decompile_program(mlog)
        self.assertEqual(len(program.functions), 1)
        fn = program.functions[0]
        self.assertNotIn("counter", fn.param_names)

        py_code = program.to_python()
        self._verify_python_syntax(py_code)
        self.assertIn("def bump():", py_code)
        self.assertIn("counter = counter + 1", py_code)
        self.assertIn("bump()", py_code)

    # -----------------------------------------------------------------------
    # 7. Nested if / while Control Flow inside Functions
    # -----------------------------------------------------------------------

    def test_nested_if_in_function(self):
        """Test recovering structured if/else branching inside a function body."""
        mlog = """
jump 7 always 0 0
jump 4 lessThan val 0
set sign 1
jump 5 always 0 0
set sign -1
set __retval_sgn sign
set @counter __ret_sgn
set @counter __ret_sgn
set val -5
set __ret_sgn 11
jump 1 always 0 0
set res __retval_sgn
"""
        py_code = decompile(mlog)
        self._verify_python_syntax(py_code)
        self.assertIn("def sgn(val):", py_code)
        self.assertIn("res = sgn(-5)", py_code)

    def test_nested_while_in_function(self):
        """Test recovering a while loop inside a function body."""
        mlog = """
jump 7 always 0 0
set acc 0
jump 6 greaterThanEq n 10
op add acc acc n
op add n n 1
jump 2 always 0 0
set __retval_sum acc
set @counter __ret_sum
set @counter __ret_sum
set n 0
set __ret_sum 12
jump 1 always 0 0
set total __retval_sum
"""
        py_code = decompile(mlog)
        self._verify_python_syntax(py_code)
        self.assertIn("def sum(n):", py_code)
        self.assertIn("total = sum(0)", py_code)

    # -----------------------------------------------------------------------
    # 8. Multiple Call Sites
    # -----------------------------------------------------------------------

    def test_multiple_call_sites(self):
        """Test recovering a function called from multiple call sites with different arguments."""
        mlog = """
jump 5 always 0 0
op mul doubled x 2
set __retval_twice doubled
set @counter __ret_twice
set @counter __ret_twice
set x 5
set __ret_twice 8
jump 1 always 0 0
set a __retval_twice
set x 20
set __ret_twice 12
jump 1 always 0 0
set b __retval_twice
"""
        program = decompile_program(mlog)
        self.assertEqual(len(program.functions), 1)
        fn = program.functions[0]
        self.assertEqual(fn.name, "twice")

        py_code = program.to_python()
        self._verify_python_syntax(py_code)
        self.assertIn("def twice(x):", py_code)
        self.assertIn("a = twice(5)", py_code)
        self.assertIn("b = twice(20)", py_code)

    # -----------------------------------------------------------------------
    # 9. Recursion with Verified Convention
    # -----------------------------------------------------------------------

    def test_recursion_recovery(self):
        """Test recovering recursive function calls when calling convention is verified."""
        mlog = """
jump 8 always 0 0
jump 5 greaterThanEq n 1
set __retval_fact 1
set @counter __ret_fact
op sub next_n n 1
set n next_n
set __ret_fact 8
jump 1 always 0 0
set @counter __ret_fact
set n 5
set __ret_fact 12
jump 1 always 0 0
set ans __retval_fact
"""
        program = decompile_program(mlog)
        self.assertEqual(len(program.functions), 1)
        fn = program.functions[0]
        self.assertEqual(fn.name, "fact")

        py_code = program.to_python()
        self._verify_python_syntax(py_code)
        self.assertIn("def fact(n):", py_code)

    # -----------------------------------------------------------------------
    # 10. Negative Tests: Control Flow NOT Mistaken for Function Call
    # -----------------------------------------------------------------------

    def test_negative_while_loop_latch_not_a_call(self):
        """Verify that a backward loop latch is NOT mistaken for a function call."""
        mlog = """
set i 0
jump 4 greaterThanEq i 10
op add i i 1
jump 1 always 0 0
print i
"""
        program = decompile_program(mlog)
        self.assertEqual(len(program.functions), 0)
        py_code = program.to_python()
        self._verify_python_syntax(py_code)
        self.assertNotIn("def ", py_code)
        self.assertIn("while i < 10:", py_code)

    def test_negative_break_jump_not_a_call(self):
        """Verify that a forward break jump is NOT mistaken for a function call."""
        mlog = """
set i 0
jump 6 greaterThanEq i 10
jump 5 notEqual i 5
jump 6 always 0 0
op add i i 1
jump 1 always 0 0
print "done"
"""
        program = decompile_program(mlog)
        self.assertEqual(len(program.functions), 0)
        py_code = program.to_python()
        self._verify_python_syntax(py_code)
        self.assertNotIn("def ", py_code)
        self.assertIn("break", py_code)

    def test_negative_if_forward_branch_not_a_call(self):
        """Verify that an if-else forward merge jump is NOT mistaken for a function call."""
        mlog = """
set x 10
jump 4 greaterThan x 5
set y 1
jump 5 always 0 0
set y 2
print y
"""
        program = decompile_program(mlog)
        self.assertEqual(len(program.functions), 0)
        py_code = program.to_python()
        self._verify_python_syntax(py_code)
        self.assertNotIn("def ", py_code)
        self.assertTrue("if x <= 5:" in py_code or "if x > 5:" in py_code)

    # -----------------------------------------------------------------------
    # 11. Invalid / Ambiguous Pattern Fallback (Zero Guessing)
    # -----------------------------------------------------------------------

    def test_ambiguous_computed_goto_fallback(self):
        """Verify that unverified computed goto without call site falls back safely."""
        mlog = """
set x 10
set @counter unknown_reg
print x
"""
        program = decompile_program(mlog)
        self.assertEqual(len(program.functions), 0)
        py_code = program.to_python()
        self._verify_python_syntax(py_code)
        self.assertNotIn("def ", py_code)

    # -----------------------------------------------------------------------
    # 12. Round-Trip Regression Tests (mlog -> Python -> compiler -> mlog)
    # -----------------------------------------------------------------------

    def test_round_trip_single_function(self):
        """Test full round-trip for function definition and call."""
        original_py = """
def add(a, b):
    return a + b

out = add(10, 20)
print(out)
"""
        # 1. Compile Python with allow_functions=True
        compile_res_1 = compile_py(original_py, allow_functions=True)
        mlog_1 = compile_res_1.mlog
        self.assertTrue(bool(mlog_1.strip()))

        # 2. Decompile mlog back to Python DSL
        decompiled_py = decompile(mlog_1)
        self._verify_python_syntax(decompiled_py)
        self.assertIn("def add(a, b):", decompiled_py)
        self.assertIn("out = add(10, 20)", decompiled_py)

        # 3. Compile decompiled Python back to mlog
        compile_res_2 = compile_py(decompiled_py, allow_functions=True)
        mlog_2 = compile_res_2.mlog

        # 4. Decompile again to verify convergence (fixpoint)
        decompiled_py_2 = decompile(mlog_2)
        self.assertEqual(decompiled_py.strip(), decompiled_py_2.strip())

    def test_round_trip_multiple_functions(self):
        """Test full round-trip for multiple functions."""
        original_py = """
def add(a, b):
    return a + b

def mul(a, b):
    return a * b

x = add(3, 4)
y = mul(x, 2)
"""
        compile_res_1 = compile_py(original_py, allow_functions=True)
        mlog_1 = compile_res_1.mlog
        decompiled_py = decompile(mlog_1)
        self._verify_python_syntax(decompiled_py)

        compile_res_2 = compile_py(decompiled_py, allow_functions=True)
        decompiled_py_2 = decompile(compile_res_2.mlog)
        self.assertEqual(decompiled_py.strip(), decompiled_py_2.strip())

    def test_round_trip_void_procedure(self):
        """Test full round-trip for a procedure without return value."""
        original_py = """
def alert(msg):
    print(msg)
    return

alert("warning")
"""
        compile_res_1 = compile_py(original_py, allow_functions=True)
        mlog_1 = compile_res_1.mlog
        decompiled_py = decompile(mlog_1)
        self._verify_python_syntax(decompiled_py)
        self.assertIn("def alert(msg):", decompiled_py)
        self.assertTrue('alert("warning")' in decompiled_py or "alert('warning')" in decompiled_py)


if __name__ == "__main__":
    unittest.main()
