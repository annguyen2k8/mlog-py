"""Tests for Phase 1F: Comprehensive test suite for all 19 test categories, validation, and CLI."""

import subprocess
import sys
import unittest
from src.mlog import compile_py
from src.validator import MlogValidator, ValidationError


class TestPhase1F(unittest.TestCase):

    def check_compile_and_validate(self, source: str) -> str:
        """Helper to compile Python code, validate mlog, and return mlog string."""
        res = compile_py(source, filename="test.py", validate=True)
        # Re-validate explicitly with MlogValidator
        MlogValidator.validate(res.mlog)
        return res.mlog.strip()

    # 1. simple assignment
    def test_01_simple_assignment(self):
        source = "x = 42\ny = 3.14\ns = \"mindustry\""
        mlog = self.check_compile_and_validate(source)
        expected = [
            "set x 42",
            "set y 3.14",
            'set s "mindustry"',
        ]
        self.assertEqual(mlog.splitlines(), expected)

    # 2. arithmetic
    def test_02_arithmetic(self):
        source = (
            "a = 10\n"
            "b = 3\n"
            "add_res = a + b\n"
            "sub_res = a - b\n"
            "mul_res = a * b\n"
            "div_res = a / b\n"
            "idiv_res = a // b\n"
            "mod_res = a % b\n"
            "compound = (a + b) * (a - b)"
        )
        mlog = self.check_compile_and_validate(source)
        lines = mlog.splitlines()
        self.assertIn("op add add_res a b", lines)
        self.assertIn("op sub sub_res a b", lines)
        self.assertIn("op mul mul_res a b", lines)
        self.assertIn("op div div_res a b", lines)
        self.assertIn("op idiv idiv_res a b", lines)
        self.assertIn("op mod mod_res a b", lines)
        self.assertIn("op mul compound __tmp0 __tmp1", lines)

    # 3. comparison
    def test_03_comparison(self):
        source = (
            "if a == b:\n    res = 1\n"
            "if a != b:\n    res = 2\n"
            "if a < b:\n    res = 3\n"
            "if a <= b:\n    res = 4\n"
            "if a > b:\n    res = 5\n"
            "if a >= b:\n    res = 6"
        )
        mlog = self.check_compile_and_validate(source)
        lines = mlog.splitlines()
        self.assertTrue(any("notEqual a b" in line for line in lines))
        self.assertTrue(any("equal a b" in line for line in lines))
        self.assertTrue(any("greaterThanEq a b" in line for line in lines))
        self.assertTrue(any("greaterThan a b" in line for line in lines))
        self.assertTrue(any("lessThanEq a b" in line for line in lines))
        self.assertTrue(any("lessThan a b" in line for line in lines))

    # 4. if
    def test_04_if(self):
        source = "if x == 0:\n    y = 10"
        mlog = self.check_compile_and_validate(source)
        expected = [
            "jump 2 notEqual x 0",
            "set y 10",
        ]
        self.assertEqual(mlog.splitlines(), expected)

    # 5. if/else
    def test_05_if_else(self):
        source = "if x == 0:\n    y = 10\nelse:\n    y = 20"
        mlog = self.check_compile_and_validate(source)
        expected = [
            "jump 3 notEqual x 0",
            "set y 10",
            "jump 4 always 0 0",
            "set y 20",
        ]
        self.assertEqual(mlog.splitlines(), expected)

    # 6. elif
    def test_06_elif(self):
        source = (
            "if state == 0:\n"
            "    mode = 10\n"
            "elif state == 1:\n"
            "    mode = 20\n"
            "else:\n"
            "    mode = 30"
        )
        mlog = self.check_compile_and_validate(source)
        expected = [
            "jump 3 notEqual state 0",
            "set mode 10",
            "jump 7 always 0 0",
            "jump 6 notEqual state 1",
            "set mode 20",
            "jump 7 always 0 0",
            "set mode 30",
        ]
        self.assertEqual(mlog.splitlines(), expected)

    # 7. while
    def test_07_while(self):
        source = "i = 0\nwhile i < 5:\n    i = i + 1"
        mlog = self.check_compile_and_validate(source)
        expected = [
            "set i 0",
            "jump 4 greaterThanEq i 5",
            "op add i i 1",
            "jump 1 always 0 0",
        ]
        self.assertEqual(mlog.splitlines(), expected)

    # 8. nested while
    def test_08_nested_while(self):
        source = (
            "x = 0\n"
            "while x < 3:\n"
            "    y = 0\n"
            "    while y < 2:\n"
            "        y = y + 1\n"
            "    x = x + 1"
        )
        mlog = self.check_compile_and_validate(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "set x 0")
        self.assertEqual(lines[1], "jump 8 greaterThanEq x 3")
        self.assertEqual(lines[2], "set y 0")
        self.assertEqual(lines[3], "jump 6 greaterThanEq y 2")
        self.assertEqual(lines[4], "op add y y 1")
        self.assertEqual(lines[5], "jump 3 always 0 0")
        self.assertEqual(lines[6], "op add x x 1")
        self.assertEqual(lines[7], "jump 1 always 0 0")

    # 9. nested if
    def test_09_nested_if(self):
        source = (
            "if a > 0:\n"
            "    if b > 0:\n"
            "        res = 1\n"
            "    else:\n"
            "        res = 2"
        )
        mlog = self.check_compile_and_validate(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "jump 5 lessThanEq a 0")
        self.assertEqual(lines[1], "jump 4 lessThanEq b 0")
        self.assertEqual(lines[2], "set res 1")
        self.assertEqual(lines[3], "jump 5 always 0 0")
        self.assertEqual(lines[4], "set res 2")

    # 10. break
    def test_10_break(self):
        source = (
            "while i < 10:\n"
            "    if i == 5:\n"
            "        break\n"
            "    i = i + 1"
        )
        mlog = self.check_compile_and_validate(source)
        lines = mlog.splitlines()
        # break jumps to line 5 (after the while loop)
        self.assertEqual(lines[2], "jump 5 always 0 0")

    # 11. continue
    def test_11_continue(self):
        source = (
            "while i < 10:\n"
            "    if i == 5:\n"
            "        continue\n"
            "    i = i + 1"
        )
        mlog = self.check_compile_and_validate(source)
        lines = mlog.splitlines()
        # continue jumps to line 0 (the start of while loop condition)
        self.assertEqual(lines[2], "jump 0 always 0 0")

    # 12. multiple labels / blocks
    def test_12_multiple_labels(self):
        source = (
            "if x == 1:\n"
            "    a = 1\n"
            "if y == 2:\n"
            "    b = 2\n"
            "if z == 3:\n"
            "    c = 3"
        )
        mlog = self.check_compile_and_validate(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "jump 2 notEqual x 1")
        self.assertEqual(lines[1], "set a 1")
        self.assertEqual(lines[2], "jump 4 notEqual y 2")
        self.assertEqual(lines[3], "set b 2")
        self.assertEqual(lines[4], "jump 6 notEqual z 3")
        self.assertEqual(lines[5], "set c 3")

    # 13. forward jump
    def test_13_forward_jump(self):
        source = "if cond:\n    x = 10"
        mlog = self.check_compile_and_validate(source)
        lines = mlog.splitlines()
        # Jump forward to skip body
        self.assertEqual(lines[0], "jump 2 equal cond 0")
        self.assertEqual(lines[1], "set x 10")

    # 14. backward jump
    def test_14_backward_jump(self):
        source = "while True:\n    op(\"add\", i, i, 1)"
        mlog = self.check_compile_and_validate(source)
        lines = mlog.splitlines()
        expected = [
            "jump 3 equal true 0",
            "op add i i 1",
            "jump 0 always 0 0",
        ]
        self.assertEqual(lines, expected)

    # 15. @counter
    def test_15_counter(self):
        source = (
            "set(\"@counter\", 0)\n"
            "at_counter = 10\n"
            "counter = 5"
        )
        mlog = self.check_compile_and_validate(source)
        expected = [
            "set @counter 0",
            "set @counter 10",
            "set @counter 5",
        ]
        self.assertEqual(mlog.splitlines(), expected)

    # 16. mlog built-in constants
    def test_16_builtin_constants(self):
        source = (
            "u = at_unit\n"
            "t = at_this\n"
            "hp = sensor(\"block1\", \"@health\")\n"
            "ubind(\"@mega\")"
        )
        mlog = self.check_compile_and_validate(source)
        expected = [
            "set u @unit",
            "set t @this",
            "sensor hp block1 @health",
            "ubind @mega",
        ]
        self.assertEqual(mlog.splitlines(), expected)

    # 17. draw commands
    def test_17_draw_commands(self):
        source = (
            "draw(\"clear\", 0, 0, 0)\n"
            "draw(\"color\", 255, 255, 255, 255)\n"
            "draw(\"line\", 10, 20, 30, 40)\n"
            "drawflush(\"display1\")"
        )
        mlog = self.check_compile_and_validate(source)
        expected = [
            "draw clear 0 0 0 0 0 0",
            "draw color 255 255 255 255 0 0",
            "draw line 10 20 30 40 0 0",
            "drawflush display1",
        ]
        self.assertEqual(mlog.splitlines(), expected)

    # 18. memory read/write
    def test_18_memory_read_write(self):
        source = (
            "write(999, \"cell1\", 0)\n"
            "val = read(\"cell1\", 0)"
        )
        mlog = self.check_compile_and_validate(source)
        expected = [
            "write 999 cell1 0",
            "read val cell1 0",
        ]
        self.assertEqual(mlog.splitlines(), expected)

    # 19. complex nested control flow
    def test_19_complex_nested_control_flow(self):
        source = (
            "total = 0\n"
            "i = 0\n"
            "while i < 10:\n"
            "    if i % 2 == 0:\n"
            "        if i == 6:\n"
            "            break\n"
            "        total = total + i\n"
            "    else:\n"
            "        total = total - 1\n"
            "    i = i + 1\n"
            "print(total)\n"
            "printflush(\"message1\")"
        )
        mlog = self.check_compile_and_validate(source)
        # Verify valid mlog
        MlogValidator.validate(mlog)
        lines = mlog.splitlines()
        self.assertTrue(lines[-2].startswith("print total"))
        self.assertEqual(lines[-1], "printflush message1")

    def test_validator_detects_invalid_opcode(self):
        with self.assertRaises(ValidationError) as ctx:
            MlogValidator.validate("invalid_opcode 1 2 3")
        self.assertIn("Unknown or unsupported mlog opcode", str(ctx.exception))

    def test_validator_detects_invalid_jump_address(self):
        with self.assertRaises(ValidationError) as ctx:
            MlogValidator.validate("jump not_a_number always 0 0")
        self.assertIn("Jump address must be a non-negative integer", str(ctx.exception))

    def test_cli_execution(self):
        res = subprocess.run(
            [sys.executable, "compiler.py", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("Compile a controlled Python subset into Mindustry Logic", res.stdout)


if __name__ == "__main__":
    unittest.main()
