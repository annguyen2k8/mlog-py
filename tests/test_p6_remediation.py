"""Regression suite for P6 remediation.

Covers four independently reproduced findings:

- P6-CRIT-01: unconditional jumps must survive structuring at program
  terminators, enclosing branch boundaries, and loop latches.
- P6-CRIT-02: user-function calls used as values must capture
  ``__retval_<fn>`` instead of degrading to the literal ``0``.
- P6-CRIT-03: source-map emission of raw jumps must format operands
  semantically (numbers stay numeric, identifiers stay bare, condition
  tokens stay strings) so the output recompiles faithfully.
- P6-HIGH-01: direct and indirect recursion are rejected at compile time
  until mlog gains a software call stack.
"""

import ast
import os
import re
import unittest

from src.decompiler import decompile, decompile_with_source_map
from src.decompiler.parser import parse_mlog
from src.errors import CompileError
from src.mlog import compile_py

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(REPO_ROOT, "tests", "corpus")


def _lines(text):
    return [line.strip() for line in text.strip().splitlines()]


class TestP6Crit01UnconditionalJumps(unittest.TestCase):
    """P6-CRIT-01: unconditional jumps are never silently dropped."""

    def test_program_terminator_emits_end(self):
        mlog = "set a 1\njump 5 always 0 0\nset a 2\nset a 3\nprint a\n"
        py = decompile(mlog)
        ast.parse(py)
        lines = _lines(py)
        self.assertIn("end()", lines)
        # The terminator must stay ahead of the unreachable tail so the
        # tail can never execute sequentially.
        self.assertLess(lines.index("end()"), lines.index("a = 2"))
        recompiled = _lines(compile_py(py, allow_functions=True, validate=True).mlog)
        self.assertEqual(
            recompiled[:4],
            ["set a 1", "end", "set a 2", "set a 3"],
        )

    def test_jump_to_final_address_stays_a_terminator(self):
        # A jump to the last instruction must not be rewritten as fallthrough
        # when it is the final instruction itself.
        mlog = "set a 1\nprint a\njump 3 always 0 0\n"
        py = decompile(mlog)
        self.assertIn("end()", _lines(py))
        recompiled = _lines(compile_py(py, allow_functions=True, validate=True).mlog)
        self.assertEqual(recompiled, ["set a 1", "print a", "end"])

    def test_branch_boundary_jump_is_preserved_not_consumed(self):
        mlog = (
            "set x 1\n"
            "jump 4 equal x 0\n"
            "jump 7 always 0 0\n"
            "set dead1 99\n"
            "set y 2\n"
            "set z 3\n"
            "set w 4\n"
            "print y\n"
            "print z\n"
        )
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn('jump(7, "always", 0, 0)', py)
        self.assertLess(py.index("jump(7"), py.index("dead1 = 99"))
        recompiled = _lines(compile_py(py, allow_functions=True, validate=True).mlog)
        self.assertEqual(
            recompiled[:4],
            ["set x 1", "jump 4 equal x 0", "jump 7 always 0 0", "set dead1 99"],
        )

    def test_loop_latch_jump_becomes_continue(self):
        path = os.path.join(CORPUS, "control_flow", "nested_while_breaks.mlog")
        with open(path, "r", encoding="utf-8") as handle:
            mlog = handle.read()

        py, source_map = decompile_with_source_map(mlog, filename=path)
        ast.parse(py)

        # A branch that jumps to the unconditional loop latch means "continue",
        # not "skip the rest of the if body". Address 7 is that latch jump.
        self.assertIn("continue", _lines(py))
        mapping_by_address = {}
        for mapping in source_map.mappings:
            for address in mapping.mlog_addresses:
                mapping_by_address.setdefault(address, []).append(mapping.node_type)
        self.assertIn("Continue", mapping_by_address[7])

        # No instruction may disappear from the source map.
        instructions = parse_mlog(mlog)
        mapped = set(mapping_by_address)
        self.assertEqual(set(range(len(instructions))) - mapped, set())

    def test_loop_exit_gap_is_preserved_as_unstructured(self):
        path = os.path.join(CORPUS, "handwritten", "base_manager_120.mlog")
        with open(path, "r", encoding="utf-8") as handle:
            mlog = handle.read()

        py, source_map = decompile_with_source_map(mlog, filename=path)
        ast.parse(py)

        # P7-HIGH-01: the loop exit skips [20, 22) and [33, 36). Those
        # instructions must stay in the output but must never execute on the
        # loop-exit path, so the whole loop region is preserved as raw code and
        # structuring resumes exactly at the recorded exit addresses.
        self.assertIn("Loop exit at address 22", py)
        self.assertIn("Loop exit at address 36", py)
        self.assertIn('ubind("@flare")', py)
        self.assertIn('u_flag = sensor("@unit", "@flag")', py)

        # No instruction may disappear from the source map.
        instructions = parse_mlog(mlog)
        mapped = set()
        for mapping in source_map.mappings:
            mapped.update(mapping.mlog_addresses)
        self.assertEqual(set(range(len(instructions))) - mapped, set())

        # Recompilation preserves the full 120-instruction layout.
        recompiled = compile_py(py, allow_functions=True, validate=True).mlog
        self.assertEqual(len(recompiled.strip().splitlines()), 120)

    def test_structured_loops_keep_their_shape(self):
        path = os.path.join(CORPUS, "control_flow", "nested_while_breaks.mlog")
        with open(path, "r", encoding="utf-8") as handle:
            mlog = handle.read()
        py = decompile(mlog)
        ast.parse(py)
        self.assertNotIn("end()", py)
        self.assertIn("while ", py)
        self.assertIn("break", py)

    def test_jump_at_range_end_is_still_fallthrough(self):
        # Normal if/else bytecode ends the then-body with an unconditional
        # jump to the merge point; that one is a structured fallthrough and
        # must not be emitted as a raw jump.
        mlog = (
            "set x 1\n"
            "jump 4 equal x 0\n"
            "set y 2\n"
            "jump 5 always 0 0\n"
            "set y 3\n"
            "print y\n"
        )
        py = decompile(mlog)
        ast.parse(py)
        self.assertNotIn("jump(", py)
        self.assertIn("if ", py)
        self.assertIn("else:", py)


class TestP6Crit02FunctionReturnValue(unittest.TestCase):
    """P6-CRIT-02: calls used as values receive their __retval result."""

    def _compile(self, source):
        return compile_py(source, allow_functions=True, validate=True).mlog

    def test_call_in_binary_expression_captures_retval(self):
        mlog = self._compile(
            "def inc(x):\n"
            "    return x + 1\n"
            "\n"
            "res = inc(4) + 1\n"
        )
        self.assertRegex(mlog, r"set __tmp\d+ __retval_inc\nop add res __tmp\d+ 1")

    def test_nested_call_captures_each_result(self):
        mlog = self._compile(
            "def inc(x):\n"
            "    return x + 1\n"
            "\n"
            "res = inc(inc(4))\n"
        )
        # The inner call has no target destination and must capture __retval_inc;
        # the outer call writes directly to res.
        captures = re.findall(r"set __tmp\d+ __retval_inc", mlog)
        self.assertEqual(len(captures), 1)
        self.assertRegex(mlog, r"set x __tmp\d+")
        self.assertIn("set res __retval_inc", mlog)

    def test_multiple_calls_in_one_expression(self):
        mlog = self._compile(
            "def add(a, b):\n"
            "    return a + b\n"
            "\n"
            "def twice(x):\n"
            "    return add(x, x)\n"
            "\n"
            "res = twice(3) + add(1, 2)\n"
        )
        self.assertRegex(mlog, r"set __tmp\d+ __retval_twice")
        self.assertRegex(mlog, r"set __tmp\d+ __retval_add")
        self.assertRegex(mlog, r"op add res __tmp\d+ __tmp\d+")

    def test_call_in_return_statement_captures_retval(self):
        mlog = self._compile(
            "def inc(x):\n"
            "    return x + 1\n"
            "\n"
            "def inc_twice(x):\n"
            "    return inc(inc(x))\n"
            "\n"
            "res = inc_twice(4)\n"
        )
        self.assertGreaterEqual(len(re.findall(r"__retval_inc", mlog)), 3)
        self.assertRegex(mlog, r"set __retval_inc_twice __tmp\d+")

    def test_statement_only_call_does_not_allocate_a_capture(self):
        mlog = self._compile(
            "def bump(x):\n"
            "    msg = x + 1\n"
            "    return msg\n"
            "\n"
            "bump(3)\n"
            "res = 7\n"
        )
        self.assertNotRegex(mlog, r"set __tmp\d+ __retval_bump")
        self.assertIn("set res 7", mlog)

    def test_target_dest_call_is_unchanged(self):
        mlog = self._compile(
            "def inc(x):\n"
            "    return x + 1\n"
            "\n"
            "res = inc(4)\n"
        )
        self.assertIn("set res __retval_inc", mlog)
        self.assertNotRegex(mlog, r"set __tmp\d+ __retval_inc")


class TestP6Crit03SourceMapJumpOperands(unittest.TestCase):
    """P6-CRIT-03: source-map jump operands use semantic formatting."""

    def setUp(self):
        self.path = os.path.join(CORPUS, "pathological", "spaghetti_goto.mlog")
        with open(self.path, "r", encoding="utf-8") as handle:
            self.mlog = handle.read()

    def test_unstructured_jump_arguments_are_not_quoted(self):
        py, _ = decompile_with_source_map(self.mlog, filename=self.path)
        self.assertIn('jump(5, "greaterThan", a, 0)', py)
        self.assertIn('jump(6, "always", 0, 0)', py)
        self.assertNotIn("jump('5'", py)
        self.assertNotIn("'greaterThan'", py)

    def test_source_map_matches_plain_decompilation(self):
        plain = decompile(self.mlog, filename=self.path)
        with_map, _ = decompile_with_source_map(self.mlog, filename=self.path)
        self.assertEqual(plain, with_map)

    def test_source_map_jump_output_recompiles_byte_for_byte(self):
        py, _ = decompile_with_source_map(self.mlog, filename=self.path)
        ast.parse(py)
        recompiled = compile_py(py, allow_functions=True, validate=True).mlog
        self.assertEqual(_lines(recompiled), _lines(self.mlog))

    def test_debug_source_map_output_parses(self):
        py, source_map = decompile_with_source_map(self.mlog, filename=self.path, debug=True)
        ast.parse(py)
        self.assertGreater(len(source_map.mappings), 0)
        self.assertIn('jump(5, "greaterThan", a, 0)', py)


class TestP6High01RecursionRejection(unittest.TestCase):
    """P6-HIGH-01: recursion fails fast with a clear cycle diagnostic."""

    def test_direct_recursion_is_rejected(self):
        source = (
            "def fact(n):\n"
            "    if n <= 1:\n"
            "        return 1\n"
            "    return n * fact(n - 1)\n"
            "\n"
            "result = fact(5)\n"
        )
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, allow_functions=True, validate=True)
        message = str(ctx.exception)
        self.assertIn("recursive user function call is not supported", message)
        self.assertIn("fact -> fact", message)
        self.assertIn("no call stack", message)

    def test_indirect_recursion_is_rejected(self):
        source = (
            "def ping(n):\n"
            "    return pong(n - 1)\n"
            "\n"
            "def pong(n):\n"
            "    if n <= 0:\n"
            "        return 0\n"
            "    return ping(n)\n"
            "\n"
            "result = ping(3)\n"
        )
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, allow_functions=True, validate=True)
        self.assertIn("ping -> pong -> ping", str(ctx.exception))

    def test_three_function_cycle_is_rejected(self):
        source = (
            "def a(n):\n"
            "    return b(n)\n"
            "\n"
            "def b(n):\n"
            "    return c(n)\n"
            "\n"
            "def c(n):\n"
            "    return a(n)\n"
            "\n"
            "x = a(1)\n"
        )
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, allow_functions=True, validate=True)
        self.assertIn("a -> b -> c -> a", str(ctx.exception))

    def test_nested_non_recursive_calls_still_compile(self):
        source = (
            "def inner(x):\n"
            "    return x * 2\n"
            "\n"
            "def outer(x):\n"
            "    return inner(x) + 1\n"
            "\n"
            "result = outer(4)\n"
        )
        mlog = compile_py(source, allow_functions=True, validate=True).mlog
        self.assertIn("set __retval_inner", mlog)
        self.assertIn("set __retval_outer", mlog)
        self.assertIn("set result __retval_outer", mlog)

    def test_same_name_calls_to_different_scopes_are_not_cycles(self):
        # Loops and intrinsics must not be mistaken for recursion.
        source = (
            "def count(n):\n"
            "    total = 0\n"
            "    for i in range(n):\n"
            "        total = total + i\n"
            "    return total\n"
            "\n"
            "result = count(4)\n"
        )
        mlog = compile_py(source, allow_functions=True, validate=True).mlog
        self.assertIn("set result __retval_count", mlog)


if __name__ == "__main__":
    unittest.main()
