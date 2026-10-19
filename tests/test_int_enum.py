"""Tests for user-defined IntEnum named constants in Python DSL for Mindustry Logic."""

import unittest

from src.compiler import CompileError
from src.mlog import compile_py
from src.mindustry_validator import is_mindustry_available, run_with_mindustry


class TestIntEnumCompilation(unittest.TestCase):
    """Test valid declaration, substitution, expressions, and zero-runtime emission."""

    def test_basic_int_enum_substitution(self):
        code = """
from enum import IntEnum

class State(IntEnum):
    IDLE = 0
    MINING = 1
    ATTACKING = 2

state = State.MINING
if state == State.MINING:
    print("Mining")
"""
        res = compile_py(code)
        mlog = res.mlog
        lines = [l.strip() for l in mlog.strip().splitlines()]

        # Verify no runtime enum objects emitted
        self.assertNotIn("class", mlog)
        self.assertNotIn("State", mlog)
        self.assertNotIn("MINING", mlog)

        # Verify exact compile-time substitution: State.MINING -> 1
        self.assertIn("set state 1", lines)
        self.assertIn("jump 3 notEqual state 1", lines)
        self.assertIn('print "Mining"', lines)

    def test_bitwise_flags_and_expressions(self):
        code = """
from enum import IntEnum

class Flags(IntEnum):
    READ = 1 << 0
    WRITE = 1 << 1
    EXEC = 1 << 2
    ALL = READ | WRITE | EXEC

mask = Flags.ALL
is_readable = mask & Flags.READ
"""
        res = compile_py(code)
        mlog = res.mlog

        # Flags.ALL = 1 | 2 | 4 = 7
        self.assertIn("set mask 7", mlog)
        # mask & Flags.READ -> mask & 1
        self.assertIn("op and is_readable mask 1", mlog)

    def test_negative_integers_and_arithmetic_in_members(self):
        code = """
from enum import IntEnum

class Mode(IntEnum):
    RESET = -1
    DEFAULT = 0
    BOOST = DEFAULT + 10

val = Mode.RESET
boost_val = Mode.BOOST
"""
        res = compile_py(code)
        self.assertIn("set val -1", res.mlog)
        self.assertIn("set boost_val 10", res.mlog)

    def test_multiple_enums_in_same_file(self):
        code = """
from enum import IntEnum

class State(IntEnum):
    OFF = 0
    ON = 1

class Priority(IntEnum):
    LOW = 100
    HIGH = 200

s = State.ON
p = Priority.HIGH
"""
        res = compile_py(code)
        self.assertIn("set s 1", res.mlog)
        self.assertIn("set p 200", res.mlog)

    def test_int_enum_with_dsl_enums_interop(self):
        code = """
from enum import IntEnum
from mlog import Items, Units, SensorProperty

class Priority(IntEnum):
    COPPER_PRIO = 1
    LEAD_PRIO = 2

item = Items.COPPER
unit = Units.FLARE
prop = SensorProperty.HEALTH
prio = Priority.COPPER_PRIO
"""
        res = compile_py(code)
        mlog = res.mlog

        # DSL enums must preserve their @token mappings
        self.assertIn("set item @copper", mlog)
        self.assertIn("set unit @flare", mlog)
        self.assertIn("set prop @health", mlog)
        # User IntEnum maps to literal integer
        self.assertIn("set prio 1", mlog)

    def test_int_enum_in_intrinsic_calls(self):
        code = """
from enum import IntEnum
from mlog import draw, ucontrol

class TargetType(IntEnum):
    ENEMY = 1
    ALLY = 0

ucontrol.flag(TargetType.ENEMY)
draw.clear(TargetType.ALLY, TargetType.ENEMY, TargetType.ALLY)
"""
        res = compile_py(code)
        mlog = res.mlog
        self.assertIn("ucontrol flag 1 0 0 0 0", mlog)
        self.assertIn("draw clear 0 1 0", mlog)

    def test_runtime_execution_in_mindustry(self):
        if not is_mindustry_available():
            self.skipTest("Mindustry Java runtime not available in this environment")

        code = """
from enum import IntEnum

class Counter(IntEnum):
    START = 5
    STEP = 2

c = Counter.START
c += Counter.STEP
print(c)
"""
        res = compile_py(code)
        run_res = run_with_mindustry(res.mlog)
        self.assertTrue(run_res.success, f"Mindustry execution failed: {run_res.message}")
        self.assertEqual(run_res.vars.get("c"), 7.0)
        self.assertEqual(run_res.text_buffer.strip(), "7")


class TestIntEnumValidationErrors(unittest.TestCase):
    """Test rejection of unsupported features, duplicates, invalid values, and syntax errors."""

    def test_reject_unsupported_base_enum(self):
        code = """
from enum import Enum

class State(Enum):
    IDLE = 0
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("only 'IntEnum' is supported in MVP", str(ctx.exception))

    def test_reject_unsupported_base_flag(self):
        code = """
from enum import Flag

class State(Flag):
    IDLE = 1
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        # Should be rejected at import or class base
        msg = str(ctx.exception)
        self.assertTrue(
            "only 'IntEnum' is supported in MVP" in msg or "cannot import name 'Flag'" in msg,
            f"Unexpected error: {msg}",
        )

    def test_reject_unsupported_import_from_enum(self):
        code = """
from enum import StrEnum

class State(StrEnum):
    IDLE = "idle"
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("only 'IntEnum' is supported in MVP", str(ctx.exception))

    def test_reject_class_without_base(self):
        code = """
class State:
    IDLE = 0
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("must inherit from 'IntEnum'", str(ctx.exception))

    def test_reject_multiple_inheritance(self):
        code = """
from enum import IntEnum

class Other(IntEnum):
    A = 0

class State(IntEnum, Other):
    IDLE = 0
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("multiple inheritance is not supported", str(ctx.exception))

    def test_reject_duplicate_enum_name(self):
        code = """
from enum import IntEnum

class State(IntEnum):
    IDLE = 0

class State(IntEnum):
    RUN = 1
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("duplicate definition of enum 'State'", str(ctx.exception))

    def test_reject_duplicate_member_in_enum(self):
        code = """
from enum import IntEnum

class State(IntEnum):
    IDLE = 0
    IDLE = 1
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("duplicate member 'IDLE'", str(ctx.exception))

    def test_reject_nonexistent_member(self):
        code = """
from enum import IntEnum

class State(IntEnum):
    IDLE = 0

x = State.MINING
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("enum 'State' has no member 'MINING'", str(ctx.exception))

    def test_reject_string_member_value(self):
        code = """
from enum import IntEnum

class State(IntEnum):
    IDLE = "idle"
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("must be an integer", str(ctx.exception))

    def test_reject_float_member_value(self):
        code = """
from enum import IntEnum

class State(IntEnum):
    IDLE = 1.5
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("must be an integer", str(ctx.exception))

    def test_reject_bool_member_value(self):
        code = """
from enum import IntEnum

class State(IntEnum):
    IDLE = True
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("must be an integer, got bool", str(ctx.exception))

    def test_reject_dynamic_member_value(self):
        code = """
from enum import IntEnum

x = 10
class State(IntEnum):
    IDLE = x + 1
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("unknown identifier 'x'", str(ctx.exception))

        code_call = """
from enum import IntEnum

class State(IntEnum):
    IDLE = len([1, 2])
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code_call)
        self.assertIn("must be a static integer expression", str(ctx.exception))

    def test_reject_methods_in_enum(self):
        code = """
from enum import IntEnum

class State(IntEnum):
    IDLE = 0
    def do_work(self):
        pass
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("methods are not supported in IntEnum", str(ctx.exception))

    def test_reject_assigning_to_enum_member(self):
        code = """
from enum import IntEnum

class State(IntEnum):
    IDLE = 0

State.IDLE = 5
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("cannot assign to enum member 'State.IDLE'", str(ctx.exception))

    def test_reject_aug_assigning_to_enum_member(self):
        code = """
from enum import IntEnum

class State(IntEnum):
    IDLE = 0

State.IDLE += 1
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("cannot assign to enum member 'State.IDLE'", str(ctx.exception))

    def test_reject_standalone_enum_value(self):
        code = """
from enum import IntEnum

class State(IntEnum):
    IDLE = 0

x = State
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("enum 'State' cannot be used as a standalone value", str(ctx.exception))

    def test_reject_enum_defined_in_loop(self):
        code = """
from enum import IntEnum

for i in range(10):
    class State(IntEnum):
        IDLE = 0
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("IntEnum class definitions are only allowed at module level", str(ctx.exception))

    def test_reject_dsl_name_collision(self):
        code = """
from enum import IntEnum

class Items(IntEnum):
    COPPER = 1
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("conflicts with built-in Mindustry DSL name", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
