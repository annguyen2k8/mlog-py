"""Tests for Phase 1E: Compiler intrinsics and raw mlog instructions."""

import unittest
from src.compiler import compile_source_to_ir
from src.emitter import Emitter


class TestPhase1E(unittest.TestCase):

    def test_op_intrinsic(self):
        source = 'op("add", i, i, 1)'
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "op add i i 1")

    def test_op_intrinsic_expression(self):
        source = 'x = op("mul", a, b)'
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "op mul x a b")

    def test_draw_line(self):
        source = 'draw("line", x, y, x2, y2)'
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "draw line x y x2 y2 0 0")

    def test_draw_clear(self):
        source = 'draw("clear", 255, 0, 0)'
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "draw clear 255 0 0 0 0 0")

    def test_drawflush(self):
        source = 'drawflush("display1")'
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "drawflush display1")

    def test_print_and_printflush(self):
        source = 'print("Hello Logic!")\nprintflush("message1")'
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        expected = 'print "Hello Logic!"\nprintflush message1'
        self.assertEqual(mlog.strip(), expected)

    def test_read_statement(self):
        source = 'read("val", "cell1", 0)'
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "read val cell1 0")

    def test_read_expression(self):
        source = 'val = read("cell1", 0)'
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "read val cell1 0")

    def test_write(self):
        source = 'write(123, "cell1", 0)'
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "write 123 cell1 0")

    def test_sensor_statement(self):
        source = 'sensor("hp", "block1", "@health")'
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "sensor hp block1 @health")

    def test_sensor_expression(self):
        source = 'hp = sensor("block1", "@health")'
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "sensor hp block1 @health")

    def test_control(self):
        source = 'control("enabled", "conveyor1", 1)'
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "control enabled conveyor1 1 0 0 0")

    def test_ubind(self):
        source = 'ubind("@poly")'
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "ubind @poly")

    def test_ucontrol(self):
        source = 'ucontrol("move", x, y)'
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "ucontrol move x y 0 0 0")

    def test_uradar(self):
        source = 'uradar("enemy", "any", "any", "distance", 1, "target")'
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "uradar enemy any any distance 0 1 target")

    def test_wait_stop_end(self):
        source = 'wait(2.5)\nstop()\nend()'
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        expected = "wait 2.5\nstop\nend"
        self.assertEqual(mlog.strip(), expected)

    def test_counter_with_set(self):
        source = 'set("@counter", 10)'
        ir = compile_source_to_ir(source, "test.py")
        mlog, _ = Emitter(ir).emit()
        self.assertEqual(mlog.strip(), "set @counter 10")


if __name__ == "__main__":
    unittest.main()
