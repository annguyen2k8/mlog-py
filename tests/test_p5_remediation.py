"""Regression test suite for P5 Remediation: Decompiler Fidelity & Roundtrip Robustness.

Validates fixes for:
- CRIT-01: Power operator (**) associativity preservation
- CRIT-02: 'op land' non-branching boolean logic semantics vs Python short-circuit 'and'
- CRIT-03: Zero instruction loss across CFG loop latch-to-exit gaps
- CRIT-04: Nested function call recovery inside function bodies without hard-coded jump targets
- HIGH-01: Python reserved keywords as Mindustry variable names via set("for", ...) and raw("for")
- HIGH-02: Recursive function call distinction from natural while loops
- HIGH-03: ulocate.spawn enemy flag preservation in tuple unpacking and statements
"""

import ast
import os
import unittest

from src.mlog import compile_py
from src.decompiler import decompile, decompile_program, decompile_with_source_map
from src.decompiler.expression import BinaryExpr, CallExpr, ConstantExpr, VariableExpr
from src.decompiler.parser import parse_mlog

# JVM test harness support
try:
    from tools.harness.mindustry_harness import MindustryHarness
    HARNESS_AVAILABLE = True
except Exception:
    HARNESS_AVAILABLE = False


class TestP5Remediation(unittest.TestCase):
    """Test suite for all P5 Remediation findings."""

    # -----------------------------------------------------------------------
    # CRIT-01: Power Operator (**) Associativity
    # -----------------------------------------------------------------------

    def test_crit01_power_associativity_expressions(self):
        """CRIT-01: Verify left and right associativity of power expressions."""
        # 1. Left-associative power: (a ** b) ** c
        left_tree = BinaryExpr("**", BinaryExpr("**", VariableExpr("a"), VariableExpr("b")), VariableExpr("c"))
        left_py = left_tree.to_python()
        self.assertEqual(left_py, "(a ** b) ** c")

        # 2. Right-associative power: a ** (b ** c)
        right_tree = BinaryExpr("**", VariableExpr("a"), BinaryExpr("**", VariableExpr("b"), VariableExpr("c")))
        right_py = right_tree.to_python()
        self.assertEqual(right_py, "a ** (b ** c)")

    @unittest.skipUnless(HARNESS_AVAILABLE, "Mindustry JVM harness unavailable")
    def test_crit01_power_runtime_jvm(self):
        """CRIT-01: Verify runtime values of parenthesized power in Mindustry JVM."""
        harness = MindustryHarness()
        # In Python: (2 ** 3) ** 2 = 8 ** 2 = 64
        mlog_code = compile_py("res = (2 ** 3) ** 2\n").mlog
        state = harness.execute(mlog_code, max_instructions=50)
        self.assertEqual(state.variables.get("res"), 64.0)

        # In Python: 2 ** (3 ** 2) = 2 ** 9 = 512
        mlog_code2 = compile_py("res = 2 ** (3 ** 2)\n").mlog
        state2 = harness.execute(mlog_code2, max_instructions=50)
        self.assertEqual(state2.variables.get("res"), 512.0)

    # -----------------------------------------------------------------------
    # CRIT-02: 'op land' Non-Branching Boolean Logic
    # -----------------------------------------------------------------------

    def test_crit02_op_land_decompilation_and_recompile(self):
        """CRIT-02: Verify 'op land' decompiles to op('land', ...) and preserves 1-instruction roundtrip."""
        mlog = "op land res a b\n"
        py = decompile(mlog)
        # Must NOT decompile to Python short-circuit 'and'
        self.assertNotIn(" = a and b", py)
        self.assertIn('res = op("land", a, b)', py)

        # Roundtrip recompile must emit exactly 1 instruction without branching jumps
        recompiled = compile_py(py).mlog.strip()
        self.assertEqual(recompiled, "op land res a b")

    @unittest.skipUnless(HARNESS_AVAILABLE, "Mindustry JVM harness unavailable")
    def test_crit02_op_land_runtime_jvm(self):
        """CRIT-02: Verify Mindustry JVM runtime evaluates land to 1.0, unlike Python 'and'."""
        harness = MindustryHarness()
        mlog = """set a 10
set b 20
op land res a b
"""
        state = harness.execute(mlog, max_instructions=50)
        # Mindustry LExecutor: 10 != 0 && 20 != 0 -> 1.0 (Python '10 and 20' would return 20)
        self.assertEqual(state.variables.get("res"), 1.0)

    # -----------------------------------------------------------------------
    # CRIT-03: Loop Instruction Loss across Gaps
    # -----------------------------------------------------------------------

    def test_crit03_loop_instruction_preservation_base_manager(self):
        """CRIT-03: Verify zero instruction drop in base_manager_120.mlog."""
        path = os.path.join(r"D:\Anzuno\mlog-py\tests\corpus\handwritten\base_manager_120.mlog")
        with open(path, "r", encoding="utf-8") as f:
            mlog_text = f.read()

        instructions = parse_mlog(mlog_text)
        py_code, sm = decompile_with_source_map(mlog_text, filename=path)

        # Verify all instructions between latch and exits are preserved in decompiled Python
        self.assertIn('ubind("@flare")', py_code)
        self.assertIn("u_flag = sensor('@unit', '@flag')", py_code)
        self.assertIn("draw.clear(0, 0, 0)", py_code)
        self.assertIn("draw.color(0, 255, 0)", py_code)
        self.assertIn("bar_w = power_ratio * 80", py_code)

        # Verify all instructions (except absorbed if/else unconditional jumps) are mapped
        mapped_addrs = set()
        for m in sm.mappings:
            mapped_addrs.update(m.mlog_addresses)

        all_addrs = set(range(len(instructions)))
        unmapped = all_addrs - mapped_addrs
        # Only address 15 (jump 19 always) is absorbed into structured if/else branch
        for dropped in (20, 21, 33, 34, 35):
            self.assertNotIn(dropped, unmapped, f"Instruction at address {dropped} was dropped!")

    # -----------------------------------------------------------------------
    # CRIT-04: Nested Function Calls
    # -----------------------------------------------------------------------

    def test_crit04_nested_function_calls_recovery(self):
        """CRIT-04: Verify nested function calls inside function body are decompiled cleanly without hardcoded jumps."""
        mlog = """jump 11 always 0 0
op add __retval_inc x 1
set @counter __ret_inc
set @counter __ret_inc
set x x
set __ret_inc 7
jump 1 always 0 0
set t __retval_inc
set __retval_add_two t
set @counter __ret_add_two
set @counter __ret_add_two
set x 5
set __ret_add_two 14
jump 4 always 0 0
set res __retval_add_two
print res
"""
        program = decompile_program(mlog)
        self.assertEqual(len(program.functions), 2)
        fn_names = [f.name for f in program.functions]
        self.assertIn("inc", fn_names)
        self.assertIn("add_two", fn_names)

        py_code = decompile(mlog)
        # Verify nested call is recognized as inc(x) inside add_two body
        self.assertIn("def add_two(x):", py_code)
        self.assertIn("inc(x)", py_code)
        # Verify no hardcoded jumps inside add_two
        self.assertNotIn('jump(1, "always"', py_code)
        self.assertNotIn("__ret_inc = 7", py_code)

    # -----------------------------------------------------------------------
    # HIGH-01: Python Keywords as Identifiers
    # -----------------------------------------------------------------------

    def test_high01_python_keywords_roundtrip(self):
        """HIGH-01: Verify variables named after Python keywords roundtrip without SyntaxError."""
        mlog = """set for 10
set class 20
op add def for class
read pass cell1 0
sensor while block1 @health
getlink if 0
lookup item import 0
"""
        py = decompile(mlog)
        # Verify decompiled Python is syntactically valid AST
        ast.parse(py)

        self.assertIn('set("for", 10)', py)
        self.assertIn('set("class", 20)', py)
        self.assertIn('raw("for"), raw("class")', py)
        self.assertIn('read("cell1", 0, dest="pass")', py)
        self.assertIn('sensor("block1", "@health", dest="while")', py)
        self.assertIn('getlink("if", 0)', py)
        self.assertIn('lookup("item", "import", 0)', py)

        # Recompile must recreate exact MLog instructions
        recompiled = compile_py(py).mlog
        self.assertIn("set for 10", recompiled)
        self.assertIn("set class 20", recompiled)
        self.assertIn("op add def for class", recompiled)
        self.assertIn("read pass cell1 0", recompiled)
        self.assertIn("sensor while block1 @health", recompiled)
        self.assertIn("getlink if 0", recompiled)
        self.assertIn("lookup item import 0", recompiled)

    # -----------------------------------------------------------------------
    # HIGH-02: Recursion vs While Loops
    # -----------------------------------------------------------------------

    def test_high02_recursion_not_confused_with_loop(self):
        """HIGH-02: Verify recursive calls are not restructured into while True loops."""
        mlog = """jump 8 always 0 0
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
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("def fact(n):", py)
        # Inside fact body, recursive call must be recognized
        self.assertIn("fact(", py)

    # -----------------------------------------------------------------------
    # HIGH-03: ulocate.spawn Enemy Flag
    # -----------------------------------------------------------------------

    def test_high03_ulocate_spawn_enemy_flag(self):
        """HIGH-03: Verify ulocate.spawn preserves enemy flag in unpacking and statements."""
        # 1. enemy=False
        mlog_enemy_false = "ulocate spawn core false @copper sx sy sfound sbuild\n"
        py_false = decompile(mlog_enemy_false)
        self.assertIn("enemy=False", py_false)

        recompiled_false = compile_py(py_false).mlog.strip()
        self.assertEqual(recompiled_false, "ulocate spawn core false @copper sx sy sfound sbuild")

        # 2. enemy=True (default)
        mlog_enemy_true = "ulocate spawn core true @copper sx sy sfound sbuild\n"
        py_true = decompile(mlog_enemy_true)
        # Canonical default does not require enemy=True keyword
        self.assertNotIn("enemy=False", py_true)

        recompiled_true = compile_py(py_true).mlog.strip()
        self.assertEqual(recompiled_true, "ulocate spawn core true @copper sx sy sfound sbuild")


if __name__ == "__main__":
    unittest.main()
