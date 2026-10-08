"""Tests for Phase 1B: Expression lowering and arithmetic op generation."""

import unittest
from src.compiler import compile_source_to_ir
from src.emitter import Emitter


class TestPhase1B(unittest.TestCase):

    def test_arithmetic_add(self):
        source = "x = a + b"
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "op add x a b")

    def test_arithmetic_sub(self):
        source = "x = a - b"
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "op sub x a b")

    def test_arithmetic_mul(self):
        source = "x = a * b"
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "op mul x a b")

    def test_arithmetic_div(self):
        source = "x = a / b"
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "op div x a b")

    def test_arithmetic_idiv(self):
        source = "x = a // b"
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "op idiv x a b")

    def test_arithmetic_mod(self):
        source = "x = a % b"
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "op mod x a b")

    def test_nested_expression_left_compound(self):
        source = "x = (a + b) * c"
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        expected = "op add __tmp0 a b\nop mul x __tmp0 c"
        self.assertEqual(mlog.strip(), expected)

    def test_nested_expression_right_compound(self):
        source = "x = a * (b + c)"
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        expected = "op add __tmp0 b c\nop mul x a __tmp0"
        self.assertEqual(mlog.strip(), expected)

    def test_nested_expression_both_compound(self):
        source = "x = (a + b) * (c - d)"
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        expected = "op add __tmp0 a b\nop sub __tmp1 c d\nop mul x __tmp0 __tmp1"
        self.assertEqual(mlog.strip(), expected)

    def test_unary_sub(self):
        source = "x = -a"
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "op sub x 0 a")

    def test_unary_invert(self):
        source = "x = ~a"
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "op not x a 0")


if __name__ == "__main__":
    unittest.main()
