"""Tests for Phase 1C: if, if/else, elif, comparisons, and short-circuit boolean conditions."""

import unittest
from src.compiler import compile_source_to_ir
from src.emitter import Emitter


class TestPhase1C(unittest.TestCase):

    def test_simple_if(self):
        source = "if x == 0:\n    x = 1"
        ir = compile_source_to_ir(source, "test.py")
        mlog, label_table = Emitter(ir).emit()
        expected = [
            "jump 2 notEqual x 0",
            "set x 1",
        ]
        self.assertEqual(mlog.strip().splitlines(), expected)

    def test_if_else(self):
        source = "if x == 0:\n    x = 1\nelse:\n    x = 2"
        ir = compile_source_to_ir(source, "test.py")
        mlog, label_table = Emitter(ir).emit()
        expected = [
            "jump 3 notEqual x 0",
            "set x 1",
            "jump 4 always 0 0",
            "set x 2",
        ]
        self.assertEqual(mlog.strip().splitlines(), expected)

    def test_if_elif_else(self):
        source = (
            "if x == 0:\n"
            "    x = 1\n"
            "elif x == 1:\n"
            "    x = 2\n"
            "else:\n"
            "    x = 3"
        )
        ir = compile_source_to_ir(source, "test.py")
        mlog, label_table = Emitter(ir).emit()
        expected = [
            "jump 3 notEqual x 0",
            "set x 1",
            "jump 7 always 0 0",
            "jump 6 notEqual x 1",
            "set x 2",
            "jump 7 always 0 0",
            "set x 3",
        ]
        self.assertEqual(mlog.strip().splitlines(), expected)

    def test_comparison_operators(self):
        cases = [
            ("if x != 5: y = 1", "jump 2 equal x 5"),
            ("if x < 5: y = 1", "jump 2 greaterThanEq x 5"),
            ("if x <= 5: y = 1", "jump 2 greaterThan x 5"),
            ("if x > 5: y = 1", "jump 2 lessThanEq x 5"),
            ("if x >= 5: y = 1", "jump 2 lessThan x 5"),
        ]
        for src, expected_jump in cases:
            with self.subTest(src=src):
                ir = compile_source_to_ir(src, "test.py")
                mlog, _ = Emitter(ir).emit()
                lines = mlog.strip().splitlines()
                self.assertEqual(lines[0], expected_jump)
                self.assertEqual(lines[1], "set y 1")

    def test_short_circuit_and(self):
        source = "if a == 1 and b == 2:\n    x = 1"
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        expected = [
            "jump 3 notEqual a 1",
            "jump 3 notEqual b 2",
            "set x 1",
        ]
        self.assertEqual(mlog.strip().splitlines(), expected)

    def test_short_circuit_or(self):
        source = "if a == 1 or b == 2:\n    x = 1"
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        expected = [
            "jump 2 equal a 1",
            "jump 3 notEqual b 2",
            "set x 1",
        ]
        self.assertEqual(mlog.strip().splitlines(), expected)

    def test_boolean_not(self):
        source = "if not (x == 0):\n    x = 1"
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        expected = [
            "jump 2 equal x 0",
            "set x 1",
        ]
        self.assertEqual(mlog.strip().splitlines(), expected)

    def test_nested_if(self):
        source = (
            "if a == 1:\n"
            "    if b == 2:\n"
            "        x = 10\n"
            "    else:\n"
            "        x = 20\n"
            "else:\n"
            "    x = 30"
        )
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        expected = [
            "jump 6 notEqual a 1",
            "jump 4 notEqual b 2",
            "set x 10",
            "jump 5 always 0 0",
            "set x 20",
            "jump 7 always 0 0",
            "set x 30",
        ]
        self.assertEqual(mlog.strip().splitlines(), expected)

    def test_truthiness_expression(self):
        source = "if flag:\n    x = 1"
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        expected = [
            "jump 2 equal flag 0",
            "set x 1",
        ]
        self.assertEqual(mlog.strip().splitlines(), expected)


if __name__ == "__main__":
    unittest.main()
