"""Comprehensive regression tests for Mindustry built-in variables and sensor properties.

Verifies:
1. Built-in variables (@tick, @time, @unit, @counter, etc.) via at_* identifiers, counter, and expressions.
2. Sensor properties (@enabled, @config, @color, @health, etc.) via SensorProperty enum, string literals, and identifiers.
3. Strict disambiguation between regular string literals starting with '@' and actual built-in variables.
4. Backward compatibility for compiler intrinsics and existing constructs.
5. Rejection of invalid/unknown properties and un-exported builtins.
6. Execution and assembly verification using the real Mindustry Java harness.
"""

import unittest
from src.errors import CompileError
from src.mindustry_validator import is_mindustry_available, run_with_mindustry, validate_with_mindustry
from src.mlog import compile_py
from src.mlog_registry import (
    ControlProperty,
    SensorProperty,
)
from src.validator import MlogValidator


class TestBuiltinVariables(unittest.TestCase):
    """Test full semantic support for Mindustry built-in variables and registers."""

    def check_compile(self, source: str) -> str:
        """Compile source and validate emitted mlog syntax."""
        res = compile_py(source, filename="test.py", validate=True)
        MlogValidator.validate(res.mlog)
        return res.mlog.strip()

    # -----------------------------------------------------------------------
    # 1. Reading Built-in Variables
    # -----------------------------------------------------------------------

    def test_read_builtins_into_variables(self):
        """Reading built-in registers emits correct mlog tokens."""
        source = """
from mlog import Vars
t = Vars.tick
tm = Vars.time
u = Vars.unit
c = Vars.counter
c2 = counter
th = Vars.this
ipt = Vars.ipt
lnk = Vars.links
s = Vars.second
m = Vars.minute
w = Vars.waveNumber
wt = Vars.waveTime
mw = Vars.mapw
mh = Vars.maph
pi = Vars.pi
e = Vars.e
"""
        mlog = self.check_compile(source)
        lines = [line.strip() for line in mlog.splitlines()]
        self.assertIn("set t @tick", lines)
        self.assertIn("set tm @time", lines)
        self.assertIn("set u @unit", lines)
        self.assertIn("set c @counter", lines)
        self.assertIn("set c2 @counter", lines)
        self.assertIn("set th @this", lines)
        self.assertIn("set ipt @ipt", lines)
        self.assertIn("set lnk @links", lines)
        self.assertIn("set s @second", lines)
        self.assertIn("set m @minute", lines)
        self.assertIn("set w @waveNumber", lines)
        self.assertIn("set wt @waveTime", lines)
        self.assertIn("set mw @mapw", lines)
        self.assertIn("set mh @maph", lines)
        self.assertIn("set pi @pi", lines)
        self.assertIn("set e @e", lines)

    # -----------------------------------------------------------------------
    # 2. Writing / Modifying Built-in Registers
    # -----------------------------------------------------------------------

    def test_write_and_modify_counter(self):
        """Setting and augmented assignment to @counter works cleanly."""
        source = """
from mlog import Vars
Vars.counter = 10
counter = 20
set(Vars.counter, 30)
set("@counter", 40)
counter += 2
Vars.counter += 1
"""
        mlog = self.check_compile(source)
        lines = [line.strip() for line in mlog.splitlines()]
        self.assertIn("set @counter 10", lines)
        self.assertIn("set @counter 20", lines)
        self.assertIn("set @counter 30", lines)
        self.assertIn("set @counter 40", lines)
        self.assertIn("op add @counter @counter 2", lines)
        self.assertIn("op add @counter @counter 1", lines)

    def test_augmented_assignment_counter(self):
        """Augmented assignments operate on Vars.counter and counter."""
        source = """
from mlog import Vars
counter += 5
Vars.counter += 2
"""
        mlog = self.check_compile(source)
        lines = [line.strip() for line in mlog.splitlines()]
        self.assertIn("op add @counter @counter 5", lines)
        self.assertIn("op add @counter @counter 2", lines)

    # -----------------------------------------------------------------------
    # 3. Expressions Involving Built-in Variables
    # -----------------------------------------------------------------------

    def test_arithmetic_with_builtins(self):
        """Arithmetic expressions with @tick and @time emit valid op instructions."""
        source = """
from mlog import Vars
next_tick = Vars.tick + 10
scaled_time = Vars.time * 2
elapsed_wave = Vars.waveTime - 5.0
half_counter = counter // 2
"""
        mlog = self.check_compile(source)
        lines = [line.strip() for line in mlog.splitlines()]
        self.assertIn("op add next_tick @tick 10", lines)
        self.assertIn("op mul scaled_time @time 2", lines)
        self.assertIn("op sub elapsed_wave @waveTime 5.0", lines)
        self.assertIn("op idiv half_counter @counter 2", lines)

    def test_conditions_with_builtins(self):
        """Conditionals and branches with @unit, @tick, and @counter compile cleanly."""
        source = """
from mlog import Vars
if Vars.unit == null:
    x = 1
if Vars.tick > 100:
    y = 2
if counter < 50:
    z = 3
"""
        mlog = self.check_compile(source)
        self.assertIn("@unit null", mlog)
        self.assertIn("@tick 100", mlog)
        self.assertIn("@counter 50", mlog)

    def test_builtins_in_intrinsics(self):
        """Passing built-in variables as operands to compiler intrinsics."""
        source = """
from mlog import Vars, print, op, sensor, SensorProperty
print(Vars.tick)
print(Vars.unit)
print(counter)
res = op("add", Vars.tick, 10)
hp = sensor(Vars.unit, SensorProperty.HEALTH)
"""
        mlog = self.check_compile(source)
        lines = [line.strip() for line in mlog.splitlines()]
        self.assertIn("print @tick", lines)
        self.assertIn("print @unit", lines)
        self.assertIn("print @counter", lines)
        self.assertIn("op add res @tick 10", lines)
        self.assertIn("sensor hp @unit @health", lines)

    # -----------------------------------------------------------------------
    # 4. Removal of Legacy at_* Aliases
    # -----------------------------------------------------------------------

    def test_legacy_at_imports_rejected(self):
        """Importing legacy at_* aliases from mlog is rejected."""
        for name in ("at_tick", "at_time", "at_unit", "at_counter", "at_this"):
            source = f"from mlog import {name}\n"
            with self.assertRaises(CompileError) as ctx:
                compile_py(source, filename="bad.py")
            self.assertIn(f"cannot import name '{name}' from 'mlog'", str(ctx.exception))

    def test_at_identifier_compiles_as_normal_variable(self):
        """Identifiers with at_ prefix are treated as regular variables, not @ registers."""
        source = """
at_tick = 5
at_custom = at_tick + 1
"""
        mlog = self.check_compile(source)
        lines = [line.strip() for line in mlog.splitlines()]
        self.assertIn("set at_tick 5", lines)
        self.assertIn("op add at_custom at_tick 1", lines)


class TestSensorProperties(unittest.TestCase):
    """Test full Mindustry support for sensor properties, especially @enabled, @config, @color."""

    def check_compile(self, source: str) -> str:
        res = compile_py(source, filename="test.py", validate=True)
        MlogValidator.validate(res.mlog)
        return res.mlog.strip()

    def test_sensor_enabled_all_syntaxes(self):
        """@enabled is fully supported via SensorProperty enum and string literals."""
        source = """
from mlog import sensor, SensorProperty
res1 = sensor(block1, SensorProperty.ENABLED)
res2 = sensor(block1, "@enabled")
res3 = sensor(block1, "enabled")
sensor(res5, block1, SensorProperty.ENABLED)
sensor(res6, block1, "@enabled")
sensor(res7, block1, "enabled")
"""
        mlog = self.check_compile(source)
        lines = [line.strip() for line in mlog.splitlines()]
        self.assertIn("sensor res1 block1 @enabled", lines)
        self.assertIn("sensor res2 block1 @enabled", lines)
        self.assertIn("sensor res3 block1 @enabled", lines)
        self.assertIn("sensor res5 block1 @enabled", lines)
        self.assertIn("sensor res6 block1 @enabled", lines)
        self.assertIn("sensor res7 block1 @enabled", lines)

    def test_sensor_config_and_color(self):
        """@config and @color are supported as senseable properties."""
        source = """
from mlog import sensor, SensorProperty
cfg1 = sensor(sorter1, SensorProperty.CONFIG)
cfg2 = sensor(sorter1, "@config")
cfg3 = sensor(sorter1, "config")
col1 = sensor(light1, SensorProperty.COLOR)
col2 = sensor(light1, "@color")
col3 = sensor(light1, "color")
"""
        mlog = self.check_compile(source)
        lines = [line.strip() for line in mlog.splitlines()]
        self.assertIn("sensor cfg1 sorter1 @config", lines)
        self.assertIn("sensor cfg2 sorter1 @config", lines)
        self.assertIn("sensor cfg3 sorter1 @config", lines)
        self.assertIn("sensor col1 light1 @color", lines)
        self.assertIn("sensor col2 light1 @color", lines)
        self.assertIn("sensor col3 light1 @color", lines)

    def test_control_and_sensor_enabled_distinction(self):
        """control uses unquoted enabled while sensor uses @enabled."""
        source = """
from mlog import control, sensor, ControlProperty, SensorProperty
control(ControlProperty.ENABLED, conveyor1, 1)
control("@enabled", conveyor1, 1)
control("enabled", conveyor1, 1)
is_on = sensor(conveyor1, SensorProperty.ENABLED)
"""
        mlog = self.check_compile(source)
        lines = [line.strip() for line in mlog.splitlines()]
        self.assertIn("control enabled conveyor1 1 0 0 0", lines)
        self.assertIn("sensor is_on conveyor1 @enabled", lines)

    def test_unknown_sensor_property_rejected(self):
        """Unknown sensor properties are strictly rejected with CompileError."""
        invalid_cases = [
            'sensor(out, block1, "@invalid_prop")',
            'sensor(out, block1, "invalid_prop")',
            'sensor(out, block1, SensorProperty.NOT_A_REAL_PROPERTY)',
        ]
        for code in invalid_cases:
            with self.subTest(code=code):
                with self.assertRaises(CompileError) as ctx:
                    compile_py(code, filename="bad.py")
                self.assertIn("unknown", str(ctx.exception).lower())


class TestStringLiteralDisambiguation(unittest.TestCase):
    """Ensure ordinary Python string literals starting with '@' are not confused with built-in variables."""

    def check_compile(self, source: str) -> str:
        res = compile_py(source, filename="test.py", validate=True)
        MlogValidator.validate(res.mlog)
        return res.mlog.strip()

    def test_regular_strings_starting_with_at_are_quoted(self):
        """Regular strings like '@hello', '@user' are emitted as quoted string literals."""
        source = """
msg = "@hello"
tag = "@channel"
handle = "@user123"
notice = "@custom_text"
"""
        mlog = self.check_compile(source)
        lines = [line.strip() for line in mlog.splitlines()]
        self.assertIn('set msg "@hello"', lines)
        self.assertIn('set tag "@channel"', lines)
        self.assertIn('set handle "@user123"', lines)
        self.assertIn('set notice "@custom_text"', lines)

    def test_print_string_literal_disambiguation(self):
        """print('@text') emits quoted string print '@text', whereas print(Vars.tick) emits print @tick."""
        source = """
from mlog import Vars
print("@hello")
print("@notice")
print("@tick")
print("@unit")
print(Vars.tick)
print(Vars.unit)
print(counter)
"""
        mlog = self.check_compile(source)
        lines = [line.strip() for line in mlog.splitlines()]
        # String literals passed to print must be quoted
        self.assertIn('print "@hello"', lines)
        self.assertIn('print "@notice"', lines)
        self.assertIn('print "@tick"', lines)
        self.assertIn('print "@unit"', lines)
        # Built-in variable identifiers passed to print must be unquoted
        self.assertIn('print @tick', lines)
        self.assertIn('print @unit', lines)
        self.assertIn('print @counter', lines)

    def test_set_intrinsic_string_disambiguation(self):
        """set(x, '@hello') quotes the value, while set('@counter', 10) recognizes @counter destination."""
        source = """
set(x, "@hello")
set(y, "standard_text")
set("@counter", 100)
"""
        mlog = self.check_compile(source)
        lines = [line.strip() for line in mlog.splitlines()]
        self.assertIn('set x "@hello"', lines)
        self.assertIn('set y "standard_text"', lines)
        self.assertIn('set @counter 100', lines)

    def test_comparison_with_at_string_literal(self):
        """Comparing a variable with a string literal '@text' quotes the string."""
        source = """
if msg == "@online":
    flag = 1
"""
        mlog = self.check_compile(source)
        self.assertIn('"@online"', mlog)


class TestMindustryJavaHarnessExecution(unittest.TestCase):
    """Execute built-ins, sensor properties, and string literals on the real Mindustry engine."""

    def setUp(self):
        if not is_mindustry_available():
            self.skipTest("Mindustry Java harness not available in this environment")

    def test_mindustry_runtime_string_literal_preservation(self):
        """Verify that '@hello' evaluates to the string '@hello' in Mindustry runtime, not null."""
        mlog = 'set msg "@hello"\n'
        ok, vars_dict, msg = run_with_mindustry(mlog)
        self.assertTrue(ok, f"Execution failed: {msg}")
        self.assertEqual(vars_dict.get("msg"), "@hello", "msg must hold string '@hello' at runtime")

    def test_mindustry_runtime_builtins_arithmetic(self):
        """Verify that op add x @tick 10 executes and computes correctly at runtime."""
        mlog = 'op add x @tick 10\n'
        ok, vars_dict, msg = run_with_mindustry(mlog)
        self.assertTrue(ok, f"Execution failed: {msg}")
        self.assertIn("x", vars_dict)
        self.assertEqual(vars_dict["x"], 10.0)

    def test_mindustry_harness_assembly_validation(self):
        """Verify that compiled mlog with @enabled, @config, @color passes Mindustry LAssembler."""
        source = """
from mlog import sensor, control, SensorProperty, ControlProperty
is_on = sensor(conveyor1, SensorProperty.ENABLED)
cfg = sensor(sorter1, SensorProperty.CONFIG)
col = sensor(light1, SensorProperty.COLOR)
control(ControlProperty.ENABLED, conveyor1, 1)
"""
        res = compile_py(source, filename="test.py")
        is_valid, msg, count = validate_with_mindustry(res.mlog)
        self.assertTrue(is_valid, f"Mindustry assembly validation failed: {msg}")
        self.assertEqual(count, 4)


if __name__ == "__main__":
    unittest.main()
