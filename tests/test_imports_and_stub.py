"""Tests for Python DSL official import API, IDE typing stubs, and SSOT metadata synchronization."""

import inspect
import os
import unittest
from enum import Enum

from src.errors import CompileError
from src.metadata import (
    ALL_REGISTRY_ENUMS,
    ALLOWED_INTRINSICS,
    INTRINSICS,
    MLOG_EXPORTS,
    generate_pyi,
)
from src.mlog import compile_py
from src.validator import MlogValidator
import mlog


class TestImportsAndIdeStub(unittest.TestCase):
    """Test suite for compiler import support, IDE stubs, and SSOT metadata."""

    def check_compile(self, source: str) -> str:
        """Helper to compile source code and validate emitted mlog."""
        res = compile_py(source, filename="test_import.py", validate=True)
        MlogValidator.validate(res.mlog)
        return res.mlog.strip()

    # -----------------------------------------------------------------------
    # 1. Official from mlog import ... Compilation Tests
    # -----------------------------------------------------------------------

    def test_official_import_statement(self):
        """Verify the exact official import statement from user requirements."""
        source = (
            "from mlog import jump, set, op, sensor, control, ucontrol, draw, read, write, wait, stop, end\n"
            "set(x, 10)\n"
            "wait(1.0)\n"
            "stop()\n"
        )
        mlog_out = self.check_compile(source)
        lines = mlog_out.splitlines()
        self.assertEqual(lines[0], "set x 10")
        self.assertEqual(lines[1], "wait 1.0")
        self.assertEqual(lines[2], "stop")

    def test_full_dsl_intrinsics_usage_with_import(self):
        """Verify compiling code that uses all major imported intrinsics."""
        source = (
            "from mlog import jump, set, op, sensor, control, ucontrol, draw, read, write, wait, stop, end\n"
            "from mlog import SensorProperty, ControlProperty, UnitControl, DrawType, LogicOp, Condition\n"
            "set(counter_val, 0)\n"
            "hp = sensor(core1, SensorProperty.HEALTH)\n"
            "control(ControlProperty.ENABLED, reactor1, 1)\n"
            "ucontrol(UnitControl.MOVE, 100, 200)\n"
            "draw(DrawType.CLEAR, 0, 0, 0)\n"
            "val = read(cell1, 0)\n"
            "write(val, cell1, 1)\n"
            "res = op(LogicOp.ADD, hp, 50)\n"
            "jump(0, Condition.GREATER_THAN, res, 100)\n"
            "wait(0.5)\n"
            "end()\n"
        )
        mlog_out = self.check_compile(source)
        lines = mlog_out.splitlines()
        self.assertIn("set counter_val 0", lines)
        self.assertIn("sensor hp core1 @health", lines)
        self.assertIn("control enabled reactor1 1 0 0 0", lines)
        self.assertIn("ucontrol move 100 200 0 0 0", lines)
        self.assertIn("draw clear 0 0 0 0 0 0", lines)
        self.assertIn("read val cell1 0", lines)
        self.assertIn("write val cell1 1", lines)
        self.assertIn("op add res hp 50", lines)
        self.assertIn("jump 0 greaterThan res 100", lines)
        self.assertIn("wait 0.5", lines)
        self.assertIn("end", lines)

    def test_import_all_existing_registries_and_enums(self):
        """Verify importing all 13 official registry Enums from mlog."""
        source = (
            "from mlog import (\n"
            "    SensorProperty, ControlProperty, UnitControl, DrawType,\n"
            "    LogicOp, Condition, RadarTarget, RadarSort, Items,\n"
            "    Liquids, Units, Teams, LookupType\n"
            ")\n"
            "from mlog import ubind, sensor, lookup\n"
            "ubind(Units.FLARE)\n"
            "hp = sensor(core1, SensorProperty.HEALTH)\n"
            "item_name = lookup(LookupType.ITEM, 0)\n"
        )
        mlog_out = self.check_compile(source)
        lines = mlog_out.splitlines()
        self.assertEqual(lines[0], "ubind @flare")
        self.assertEqual(lines[1], "sensor hp core1 @health")
        self.assertEqual(lines[2], "lookup item item_name 0")

    def test_import_star(self):
        """Verify from mlog import * works seamlessly."""
        source = (
            "from mlog import *\n"
            "ubind(Units.MONO)\n"
            "wait(0.2)\n"
            "stop()\n"
        )
        mlog_out = self.check_compile(source)
        lines = mlog_out.splitlines()
        self.assertEqual(lines[0], "ubind @mono")
        self.assertEqual(lines[1], "wait 0.2")
        self.assertEqual(lines[2], "stop")

    def test_import_from_src_mlog(self):
        """Verify from src.mlog import ... is also fully accepted."""
        source = (
            "from src.mlog import jump, set, op, sensor, SensorProperty\n"
            "set(a, 5)\n"
            "h = sensor(core1, SensorProperty.HEALTH)\n"
        )
        mlog_out = self.check_compile(source)
        lines = mlog_out.splitlines()
        self.assertEqual(lines[0], "set a 5")
        self.assertEqual(lines[1], "sensor h core1 @health")

    # -----------------------------------------------------------------------
    # 2. Validation & Security: Unsupported Imports Rejected
    # -----------------------------------------------------------------------

    def test_invalid_symbol_imported_from_mlog(self):
        """Verify that importing an un-exported symbol from mlog raises CompileError."""
        source = "from mlog import nonexistent_feature\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="bad_import.py")
        self.assertIn("cannot import name 'nonexistent_feature' from 'mlog'", str(ctx.exception))

    def test_invalid_module_import_rejected(self):
        """Verify standard library / external module imports are strictly rejected."""
        bad_imports = [
            "import os\n",
            "import sys\n",
            "from math import sin\n",
            "from subprocess import Popen\n",
        ]
        for src in bad_imports:
            with self.subTest(src=src):
                with self.assertRaises(CompileError):
                    compile_py(src, filename="bad.py")

    def test_aliased_import_rejected(self):
        """Verify import aliasing ('as') is rejected to prevent symbol confusion."""
        source = "from mlog import sensor as my_sensor\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="aliased.py")
        self.assertIn("import aliasing", str(ctx.exception))

    # -----------------------------------------------------------------------
    # 3. Single Source of Truth & IDE Stub Synchronization
    # -----------------------------------------------------------------------

    def test_single_source_of_truth_stub_in_sync(self):
        """Verify that mlog.pyi on disk is 100% synchronized with generate_pyi()."""
        expected_pyi = generate_pyi()

        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        mlog_pyi_path = os.path.join(root_dir, "mlog.pyi")
        src_mlog_pyi_path = os.path.join(root_dir, "src", "mlog.pyi")

        self.assertTrue(os.path.exists(mlog_pyi_path), "mlog.pyi must exist in project root")
        self.assertTrue(os.path.exists(src_mlog_pyi_path), "src/mlog.pyi must exist in src/")

        with open(mlog_pyi_path, "r", encoding="utf-8") as f:
            actual_pyi = f.read()
        self.assertEqual(
            expected_pyi,
            actual_pyi,
            "mlog.pyi is out of sync with src/metadata.py SSOT! Run generate_pyi() to update.",
        )

        with open(src_mlog_pyi_path, "r", encoding="utf-8") as f:
            actual_src_pyi = f.read()
        self.assertEqual(
            expected_pyi,
            actual_src_pyi,
            "src/mlog.pyi is out of sync with src/metadata.py SSOT! Run generate_pyi() to update.",
        )

    def test_ide_stub_parses_without_syntax_errors(self):
        """Verify that the generated .pyi stub compiles as valid Python syntax."""
        stub = generate_pyi()
        try:
            compile(stub, "<mlog.pyi>", "exec")
        except SyntaxError as e:
            self.fail(f"mlog.pyi contains syntax error: {e}")

    # -----------------------------------------------------------------------
    # 4. Runtime Module Verification
    # -----------------------------------------------------------------------

    def test_all_intrinsics_exported_at_runtime(self):
        """Verify every intrinsic defined in INTRINSICS is exported on the mlog module."""
        for name in ALLOWED_INTRINSICS:
            self.assertTrue(
                hasattr(mlog, name),
                f"mlog module is missing runtime export for intrinsic '{name}'",
            )
            fn = getattr(mlog, name)
            self.assertTrue(
                callable(fn),
                f"mlog.{name} must be a callable runtime function",
            )

    def test_all_registry_enums_exported_at_runtime(self):
        """Verify all 13 registry enums are exported on mlog."""
        for enum_name, expected_cls in ALL_REGISTRY_ENUMS.items():
            self.assertTrue(
                hasattr(mlog, enum_name),
                f"mlog module missing Enum export '{enum_name}'",
            )
            val = getattr(mlog, enum_name)
            self.assertIs(
                val,
                expected_cls,
                f"mlog.{enum_name} must match registry enum class",
            )
            self.assertTrue(issubclass(val, Enum))

    def test_runtime_intrinsics_callability(self):
        """Verify intrinsics can be safely called in standard Python without crashing."""
        self.assertIsNone(mlog.jump(10))
        self.assertEqual(mlog.set("x", 42), 42)
        self.assertEqual(mlog.op("add", 1, 2), 0)
        self.assertEqual(mlog.sensor("core1", "@health"), 0)
        self.assertIsNone(mlog.control("enabled", "reactor1", 1))
        self.assertIsNone(mlog.ucontrol("move", 10, 20))
        self.assertIsNone(mlog.draw("clear", 0, 0, 0))
        self.assertIsNone(mlog.drawflush("display1"))
        self.assertIsNone(mlog.print("hello"))
        self.assertIsNone(mlog.printflush("message1"))
        self.assertEqual(mlog.read("cell1", 0), 0)
        self.assertIsNone(mlog.write(10, "cell1", 0))
        self.assertIsNone(mlog.wait(0.5))
        self.assertIsNone(mlog.stop())
        self.assertIsNone(mlog.end())
        self.assertIsNone(mlog.ubind("@flare"))
        self.assertEqual(mlog.raw("@customProp"), "@customProp")

    def test_null_constant_exported(self):
        """Verify null is exported and equals None."""
        self.assertTrue(hasattr(mlog, "null"))
        self.assertIsNone(mlog.null)


if __name__ == "__main__":
    unittest.main()
