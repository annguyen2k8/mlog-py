"""Tests for Mindustry Logic Registry, DSL Enums, Property Validation, and Raw Bypass."""

import unittest
from src.errors import CompileError
from src.mlog import compile_py
from src.mlog_registry import (
    Condition,
    ControlProperty,
    DrawType,
    Items,
    Liquids,
    LogicOp,
    LookupType,
    RadarSort,
    RadarTarget,
    SensorProperty,
    Teams,
    UnitControl,
    Units,
)
from src.validator import MlogValidator


class TestRegistryAndEnums(unittest.TestCase):

    def check_compile(self, source: str) -> str:
        """Compile Python source and return cleaned mlog output."""
        res = compile_py(source, filename="test.py", validate=True)
        MlogValidator.validate(res.mlog)
        return res.mlog.strip()

    # -----------------------------------------------------------------------
    # 1. DSL Enums as Arguments & Expressions
    # -----------------------------------------------------------------------

    def test_sensor_dsl_enum(self):
        source = (
            "from mlog import SensorProperty\n"
            "hp = sensor(block1, SensorProperty.HEALTH)\n"
            "items = sensor(block1, SensorProperty.TOTAL_ITEMS)\n"
            "copper = sensor(block1, SensorProperty.COPPER)\n"
            "water = sensor(block1, SensorProperty.WATER)\n"
        )
        mlog = self.check_compile(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "sensor hp block1 @health")
        self.assertEqual(lines[1], "sensor items block1 @totalItems")
        self.assertEqual(lines[2], "sensor copper block1 @copper")
        self.assertEqual(lines[3], "sensor water block1 @water")

    def test_control_dsl_enum(self):
        source = (
            "from mlog import ControlProperty\n"
            "control(ControlProperty.ENABLED, block1, 1)\n"
            "control(ControlProperty.SHOOT, block1, 10, 20, 1)\n"
        )
        mlog = self.check_compile(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "control enabled block1 1 0 0 0")
        self.assertEqual(lines[1], "control shoot block1 10 20 1 0")

    def test_unit_control_dsl_enum(self):
        source = (
            "from mlog import UnitControl\n"
            "ucontrol(UnitControl.MOVE, 50, 100)\n"
            "ucontrol(UnitControl.APPROACH, 50, 100, 5)\n"
            "ucontrol(UnitControl.TARGET, 10, 20, 1)\n"
        )
        mlog = self.check_compile(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "ucontrol move 50 100 0 0 0")
        self.assertEqual(lines[1], "ucontrol approach 50 100 5 0 0")
        self.assertEqual(lines[2], "ucontrol target 10 20 1 0 0")

    def test_draw_dsl_enum(self):
        source = (
            "from mlog import DrawType\n"
            "draw(DrawType.CLEAR, 0, 0, 0)\n"
            "draw(DrawType.LINE, 10, 20, 30, 40)\n"
            "draw(DrawType.RECT, 5, 5, 50, 50)\n"
            "drawflush(display1)\n"
        )
        mlog = self.check_compile(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "draw clear 0 0 0 0 0 0")
        self.assertEqual(lines[1], "draw line 10 20 30 40 0 0")
        self.assertEqual(lines[2], "draw rect 5 5 50 50 0 0")
        self.assertEqual(lines[3], "drawflush display1")

    def test_logic_op_dsl_enum(self):
        source = (
            "from mlog import LogicOp\n"
            "op(LogicOp.ADD, x, a, b)\n"
            "op(LogicOp.IDIV, y, a, b)\n"
            "op(LogicOp.MOD, z, a, b)\n"
        )
        mlog = self.check_compile(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "op add x a b")
        self.assertEqual(lines[1], "op idiv y a b")
        self.assertEqual(lines[2], "op mod z a b")

    def test_condition_dsl_enum(self):
        source = (
            "from mlog import Condition\n"
            "jump(dest, Condition.EQUAL, a, b)\n"
            "jump(dest, Condition.NOT_EQUAL, a, b)\n"
            "jump(dest, Condition.LESS_THAN, a, b)\n"
        )
        # We need a label 'dest' or numeric target
        source_with_label = (
            "from mlog import Condition\n"
            "jump(0, Condition.EQUAL, a, b)\n"
            "jump(0, Condition.NOT_EQUAL, a, b)\n"
            "jump(0, Condition.LESS_THAN, a, b)\n"
        )
        mlog = self.check_compile(source_with_label)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "jump 0 equal a b")
        self.assertEqual(lines[1], "jump 0 notEqual a b")
        self.assertEqual(lines[2], "jump 0 lessThan a b")

    def test_ubind_units_dsl_enum(self):
        source = (
            "from mlog import Units\n"
            "ubind(Units.FLARE)\n"
            "ubind(Units.HORIZON)\n"
            "ubind(Units.MONO)\n"
        )
        mlog = self.check_compile(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "ubind @flare")
        self.assertEqual(lines[1], "ubind @horizon")
        self.assertEqual(lines[2], "ubind @mono")

    def test_radar_dsl_enums(self):
        source = (
            "from mlog import RadarTarget, RadarSort\n"
            "res = radar(RadarTarget.ENEMY, RadarTarget.ANY, RadarTarget.ANY, RadarSort.DISTANCE, turret1, 1)\n"
            "ures = uradar(RadarTarget.ENEMY, RadarTarget.FLYING, RadarTarget.ANY, RadarSort.HEALTH, 1)\n"
        )
        mlog = self.check_compile(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "radar enemy any any distance turret1 1 res")
        self.assertEqual(lines[1], "uradar enemy flying any health 0 1 ures")


    def test_lookup_packcolor_getlink_dsl_enums(self):
        source = (
            "from mlog import LookupType\n"
            "item0 = lookup(LookupType.ITEM, 0)\n"
            "block0 = lookup(LookupType.BLOCK, 1)\n"
            "col = packcolor(1, 0.5, 0.2, 1)\n"
            "link0 = getlink(0)\n"
        )
        mlog = self.check_compile(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "lookup item item0 0")
        self.assertEqual(lines[1], "lookup block block0 1")
        self.assertEqual(lines[2], "packcolor col 1 0.5 0.2 1")
        self.assertEqual(lines[3], "getlink link0 0")

    def test_content_assignment_dsl_enum(self):
        source = (
            "from mlog import Items, Liquids, Teams\n"
            "item = Items.SILICON\n"
            "liquid = Liquids.CRYOFLUID\n"
            "team = Teams.SHARDED\n"
        )
        mlog = self.check_compile(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "set item @silicon")
        self.assertEqual(lines[1], "set liquid @cryofluid")
        self.assertEqual(lines[2], "set team @sharded")

    # -----------------------------------------------------------------------
    # 2. String Tokens and at_ Prefixes
    # -----------------------------------------------------------------------

    def test_sensor_strings_and_at_names(self):
        source = (
            "hp1 = sensor(block1, \"@health\")\n"
            "hp2 = sensor(block1, \"health\")\n"
            "hp3 = sensor(block1, at_health)\n"
            "copper1 = sensor(block1, \"@copper\")\n"
            "copper2 = sensor(block1, at_copper)\n"
        )
        mlog = self.check_compile(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "sensor hp1 block1 @health")
        self.assertEqual(lines[1], "sensor hp2 block1 @health")
        self.assertEqual(lines[2], "sensor hp3 block1 @health")
        self.assertEqual(lines[3], "sensor copper1 block1 @copper")
        self.assertEqual(lines[4], "sensor copper2 block1 @copper")

    # -----------------------------------------------------------------------
    # 3. Typo Rejection (Sensor, Control, UnitControl, Draw, Op, etc.)
    # -----------------------------------------------------------------------

    def test_sensor_typo_rejected(self):
        source = "hp = sensor(block1, \"@healht\")"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        self.assertIn("unknown sensor property '@healht'", str(ctx.exception))
        self.assertIn("test.py:1:", str(ctx.exception))

    def test_sensor_typo_without_at_rejected(self):
        source = "hp = sensor(block1, \"healht\")"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        self.assertIn("unknown sensor property 'healht'", str(ctx.exception))

    def test_control_typo_rejected(self):
        source = "control(\"enabbled\", block1, 1)"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        self.assertIn("unknown control property 'enabbled'", str(ctx.exception))

    def test_unit_control_typo_rejected(self):
        source = "ucontrol(\"movve\", 10, 20)"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        self.assertIn("unknown unit control action 'movve'", str(ctx.exception))

    def test_draw_typo_rejected(self):
        source = "draw(\"linne\", 0, 0, 10, 10)"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        self.assertIn("unknown draw type 'linne'", str(ctx.exception))

    def test_logic_op_typo_rejected(self):
        source = "op(\"ad\", x, a, b)"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        self.assertIn("unknown logic operation 'ad'", str(ctx.exception))

    def test_jump_condition_typo_rejected(self):
        source = "jump(0, \"eqal\", a, b)"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        self.assertIn("unknown jump condition 'eqal'", str(ctx.exception))

    def test_ubind_unit_typo_rejected(self):
        source = "ubind(\"@flaree\")"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        self.assertIn("unknown unit type '@flaree'", str(ctx.exception))

    def test_radar_target_typo_rejected(self):
        source = "res = radar(\"enemmy\", \"any\", \"any\", \"distance\", turret1, 1)"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        self.assertIn("unknown radar target 'enemmy'", str(ctx.exception))

    def test_radar_sort_typo_rejected(self):
        source = "res = radar(\"enemy\", \"any\", \"any\", \"disttance\", turret1, 1)"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        self.assertIn("unknown radar sort mode 'disttance'", str(ctx.exception))

    def test_lookup_type_typo_rejected(self):
        source = "res = lookup(\"iteem\", 0)"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        self.assertIn("unknown lookup type 'iteem'", str(ctx.exception))

    def test_dsl_enum_attribute_typo_rejected(self):
        source = "hp = sensor(block1, SensorProperty.HEALHT)"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        self.assertIn("unknown SensorProperty attribute 'HEALHT'", str(ctx.exception))

    # -----------------------------------------------------------------------
    # 4. Explicit raw() Escape Hatch Bypass
    # -----------------------------------------------------------------------

    def test_raw_bypass_sensor(self):
        source = (
            "from mlog import raw\n"
            "x = sensor(block1, raw(\"@someNewProperty\"))\n"
        )
        mlog = self.check_compile(source)
        self.assertEqual(mlog.strip(), "sensor x block1 @someNewProperty")

    def test_raw_bypass_control(self):
        source = (
            "from mlog import raw\n"
            "control(raw(\"customControlProp\"), block1, 1)\n"
        )
        mlog = self.check_compile(source)
        self.assertEqual(mlog.strip(), "control customControlProp block1 1 0 0 0")

    def test_raw_bypass_ucontrol(self):
        source = (
            "from mlog import raw\n"
            "ucontrol(raw(\"modAction\"), 10, 20)\n"
        )
        mlog = self.check_compile(source)
        self.assertEqual(mlog.strip(), "ucontrol modAction 10 20 0 0 0")

    def test_raw_bypass_draw(self):
        source = (
            "from mlog import raw\n"
            "draw(raw(\"drawCircleSector\"), 10, 20, 30, 45, 90)\n"
        )
        mlog = self.check_compile(source)
        self.assertEqual(mlog.strip(), "draw drawCircleSector 10 20 30 45 90 0")

    def test_raw_bypass_op(self):
        source = (
            "from mlog import raw\n"
            "op(raw(\"atan2\"), res, y, x)\n"
        )
        mlog = self.check_compile(source)
        self.assertEqual(mlog.strip(), "op atan2 res y x")

    def test_raw_bypass_jump(self):
        source = (
            "from mlog import raw\n"
            "jump(0, raw(\"approxEqual\"), a, b)\n"
        )
        res = compile_py(source, filename="test.py", validate=False)
        self.assertEqual(res.mlog.strip(), "jump 0 approxEqual a b")


    def test_raw_bypass_ubind(self):
        source = (
            "from mlog import raw\n"
            "ubind(raw(\"@modded-unit\"))\n"
        )
        mlog = self.check_compile(source)
        self.assertEqual(mlog.strip(), "ubind @modded-unit")

    # -----------------------------------------------------------------------
    # 5. Imports & Non-mlog Rejection
    # -----------------------------------------------------------------------

    def test_non_mlog_import_rejected(self):
        source = "import os\nx = 1"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        self.assertIn("unsupported Python feature: import statement", str(ctx.exception))

    def test_non_mlog_import_from_rejected(self):
        source = "from math import sin\nx = 1"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        self.assertIn("unsupported Python feature: from ... import statement", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
