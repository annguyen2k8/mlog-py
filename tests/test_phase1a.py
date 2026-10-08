"""Tests for Phase 1A: parser, validation, IR, set, and emitter basics."""

import unittest
from src.errors import CompileError
from src.compiler import compile_source_to_ir
from src.emitter import Emitter
from src.ir import IRLabel, IRJump, IRSet


class TestPhase1A(unittest.TestCase):

    def test_assignment_integer(self):
        source = "x = 10"
        ir = compile_source_to_ir(source, "test.py")
        mlog, label_table = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "set x 10")
        self.assertEqual(label_table, {})

    def test_assignment_float(self):
        source = "val = 3.14"
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "set val 3.14")

    def test_assignment_string(self):
        source = 'msg = "hello mindustry"'
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), 'set msg "hello mindustry"')

    def test_assignment_variable(self):
        source = "a = 1\nb = a"
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        expected = "set a 1\nset b a"
        self.assertEqual(mlog.strip(), expected)

    def test_assignment_counter(self):
        source = "at_counter = 5\ncounter = 0"
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        expected = "set @counter 5\nset @counter 0"
        self.assertEqual(mlog.strip(), expected)

    def test_reserved_temp_name_rejected(self):
        source = "__tmp0 = 10"
        with self.assertRaises(CompileError) as ctx:
            compile_source_to_ir(source, "test.py")
        self.assertIn("reserved for compiler temporaries", str(ctx.exception))

    def test_unsupported_python_features_rejected_with_location(self):
        cases = [
            ("def foo(): pass", "unsupported Python feature: function definition"),
            ("class Foo: pass", "unsupported Python feature: class definition"),
            ("x = [1, 2, 3]", "unsupported Python feature: list literal"),
            ("d = {'a': 1}", "unsupported Python feature: dict literal"),
            ("import math", "unsupported Python feature: import statement"),
            ("for i in range(10): pass", "unsupported Python feature: for loop"),
            ("try: pass\nexcept: pass", "unsupported Python feature: try/except statement"),
            ("x += 1", "unsupported Python feature: augmented assignment"),
            ("a = b = 1", "multiple/chained assignment targets are not supported"),
            ("a, b = 1, 2", "assignment target must be a simple variable name"),
        ]
        for src, err_substr in cases:
            with self.subTest(src=src):
                with self.assertRaises(CompileError) as ctx:
                    compile_source_to_ir(src, "test.py")
                self.assertIn("test.py:1:", str(ctx.exception))
                self.assertIn(err_substr, str(ctx.exception))

    def test_emitter_duplicate_label_error(self):
        ir = [
            IRLabel(name="loop"),
            IRSet(to="x", from_="1"),
            IRLabel(name="loop"),
        ]
        with self.assertRaises(CompileError) as ctx:
            Emitter(ir).emit()
        self.assertIn("Duplicate label: 'loop'", str(ctx.exception))

    def test_emitter_undefined_label_error(self):
        ir = [
            IRJump(target="missing_label", cond="always"),
        ]
        with self.assertRaises(CompileError) as ctx:
            Emitter(ir).emit()
        self.assertIn("Undefined jump label: 'missing_label'", str(ctx.exception))

    def test_emitter_two_pass_resolution(self):
        ir = [
            IRSet(to="x", from_="0"),
            IRLabel(name="loop_start"),
            IRSet(to="x", from_="1"),
            IRJump(target="loop_end", cond="always"),
            IRSet(to="x", from_="2"),
            IRLabel(name="loop_end"),
            IRSet(to="x", from_="3"),
        ]
        mlog, label_table = Emitter(ir).emit()
        self.assertEqual(label_table, {"loop_start": 1, "loop_end": 4})
        expected_lines = [
            "set x 0",
            "set x 1",
            "jump 4 always 0 0",
            "set x 2",
            "set x 3",
        ]
        self.assertEqual(mlog.strip().splitlines(), expected_lines)


if __name__ == "__main__":
    unittest.main()
