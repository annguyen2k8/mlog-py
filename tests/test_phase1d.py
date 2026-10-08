"""Tests for Phase 1D: while, break, continue, and nested loops."""

import unittest
from src.errors import CompileError
from src.compiler import compile_source_to_ir
from src.emitter import Emitter


class TestPhase1D(unittest.TestCase):

    def test_simple_while(self):
        source = (
            "i = 0\n"
            "while i < 10:\n"
            "    i = i + 1"
        )
        ir = compile_source_to_ir(source, "test.py")
        mlog, label_table = Emitter(ir).emit()
        expected = [
            "set i 0",
            "jump 4 greaterThanEq i 10",
            "op add i i 1",
            "jump 1 always 0 0",
        ]
        self.assertEqual(mlog.strip().splitlines(), expected)

    def test_while_with_break(self):
        source = (
            "while i < 10:\n"
            "    if x == 5:\n"
            "        break\n"
            "    i = i + 1"
        )
        ir = compile_source_to_ir(source, "test.py")
        mlog, label_table = Emitter(ir).emit()
        expected = [
            "jump 5 greaterThanEq i 10",
            "jump 3 notEqual x 5",
            "jump 5 always 0 0",
            "op add i i 1",
            "jump 0 always 0 0",
        ]
        self.assertEqual(mlog.strip().splitlines(), expected)

    def test_while_with_continue(self):
        source = (
            "while i < 10:\n"
            "    if x == 5:\n"
            "        continue\n"
            "    i = i + 1"
        )
        ir = compile_source_to_ir(source, "test.py")
        mlog, label_table = Emitter(ir).emit()
        expected = [
            "jump 5 greaterThanEq i 10",
            "jump 3 notEqual x 5",
            "jump 0 always 0 0",
            "op add i i 1",
            "jump 0 always 0 0",
        ]
        self.assertEqual(mlog.strip().splitlines(), expected)

    def test_nested_while_loops(self):
        source = (
            "i = 0\n"
            "while i < 3:\n"
            "    j = 0\n"
            "    while j < 2:\n"
            "        if j == 1:\n"
            "            break\n"
            "        j = j + 1\n"
            "    i = i + 1"
        )
        ir = compile_source_to_ir(source, "test.py")
        mlog, label_table = Emitter(ir).emit()
        lines = mlog.strip().splitlines()
        # Verify instructions:
        # 0: set i 0
        # 1: jump 10 greaterThanEq i 3 (exit outer loop)
        # 2: set j 0
        # 3: jump 9 greaterThanEq j 2 (exit inner loop)
        # 4: jump 6 notEqual j 1
        # 5: jump 9 always 0 0 (break inner loop)
        # 6: op add j j 1
        # 7: jump 3 always 0 0 (inner loop continue/restart)
        # 8: op add i i 1
        # 9: jump 1 always 0 0 (outer loop restart)
        expected = [
            "set i 0",
            "jump 10 greaterThanEq i 3",
            "set j 0",
            "jump 8 greaterThanEq j 2",
            "jump 6 notEqual j 1",
            "jump 8 always 0 0",
            "op add j j 1",
            "jump 3 always 0 0",
            "op add i i 1",
            "jump 1 always 0 0",
        ]
        self.assertEqual(lines, expected)

    def test_break_outside_loop_rejected(self):
        source = "break"
        with self.assertRaises(CompileError) as ctx:
            compile_source_to_ir(source, "test.py")
        self.assertIn("'break' outside of loop", str(ctx.exception))
        self.assertIn("test.py:1:", str(ctx.exception))

    def test_continue_outside_loop_rejected(self):
        source = "continue"
        with self.assertRaises(CompileError) as ctx:
            compile_source_to_ir(source, "test.py")
        self.assertIn("'continue' outside of loop", str(ctx.exception))
        self.assertIn("test.py:1:", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
