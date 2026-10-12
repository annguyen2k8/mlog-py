"""Unit and regression tests for UnitControl and UnitLocate Callable Namespace Objects.

Verifies Mindustry v160.7 opcodes, parameter mapping, dummy argument injection for ulocate,
backward compatibility with legacy ucontrol/ulocate calls, alias namespaces, and runtime execution.
"""

import unittest
from src.errors import CompileError
from src.mlog import UnitControl, compile_py
import src.mlog as mlog


class TestUnitControlNamespace(unittest.TestCase):
    """Test modern ucontrol.<method>(...) syntax compilation and semantics."""

    def test_idle_and_stop(self):
        code = "from mlog import ucontrol\nucontrol.idle()\nucontrol.stop()\n"
        res = compile_py(code)
        self.assertIn("ucontrol idle 0 0 0 0 0", res.mlog)
        self.assertIn("ucontrol stop 0 0 0 0 0", res.mlog)

    def test_move(self):
        code = "from mlog import ucontrol\nucontrol.move(10, 20)\n"
        res = compile_py(code)
        self.assertIn("ucontrol move 10 20 0 0 0", res.mlog)

    def test_approach(self):
        code = "from mlog import ucontrol\nucontrol.approach(15, 25, 4)\n"
        res = compile_py(code)
        self.assertIn("ucontrol approach 15 25 4 0 0", res.mlog)

    def test_pathfind(self):
        code = "from mlog import ucontrol\nucontrol.pathfind(30, 40)\n"
        res = compile_py(code)
        self.assertIn("ucontrol pathfind 30 40 0 0 0", res.mlog)

    def test_auto_pathfind_and_alias(self):
        code = "from mlog import ucontrol\nucontrol.auto_pathfind()\nucontrol.autoPathfind()\n"
        res = compile_py(code)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(lines[0], "ucontrol autoPathfind 0 0 0 0 0")
        self.assertEqual(lines[1], "ucontrol autoPathfind 0 0 0 0 0")

    def test_boost(self):
        code = "from mlog import ucontrol\nucontrol.boost(True)\n"
        res = compile_py(code)
        self.assertIn("ucontrol boost true 0 0 0 0", res.mlog)

    def test_target_and_targetp(self):
        code = "from mlog import ucontrol\nucontrol.target(50, 60, 1)\nucontrol.targetp('enemy1', 1)\n"
        res = compile_py(code)
        self.assertIn("ucontrol target 50 60 1 0 0", res.mlog)
        self.assertIn("ucontrol targetp enemy1 1 0 0 0", res.mlog)

    def test_item_drop_and_take(self):
        code = """from mlog import ucontrol
ucontrol.item_drop('core1', 50)
ucontrol.itemDrop('core1', 50)
ucontrol.item_take('core1', '@copper', 30)
ucontrol.itemTake('core1', '@copper', 30)
"""
        res = compile_py(code)
        self.assertIn("ucontrol itemDrop core1 50 0 0 0", res.mlog)
        self.assertIn("ucontrol itemTake core1 @copper 30 0 0", res.mlog)

    def test_pay_operations(self):
        code = """from mlog import ucontrol
ucontrol.pay_drop()
ucontrol.payDrop()
ucontrol.pay_take(1)
ucontrol.payTake(1)
ucontrol.pay_enter()
ucontrol.payEnter()
"""
        res = compile_py(code)
        self.assertIn("ucontrol payDrop 0 0 0 0 0", res.mlog)
        self.assertIn("ucontrol payTake 1 0 0 0 0", res.mlog)
        self.assertIn("ucontrol payEnter 0 0 0 0 0", res.mlog)

    def test_mine_flag_deconstruct_unbind(self):
        code = """from mlog import ucontrol
ucontrol.mine(12, 34)
ucontrol.flag(999)
ucontrol.deconstruct(12, 34)
ucontrol.unbind()
"""
        res = compile_py(code)
        self.assertIn("ucontrol mine 12 34 0 0 0", res.mlog)
        self.assertIn("ucontrol flag 999 0 0 0 0", res.mlog)
        self.assertIn("ucontrol deconstruct 12 34 0 0 0", res.mlog)
        self.assertIn("ucontrol unbind 0 0 0 0 0", res.mlog)

    def test_build(self):
        code = "from mlog import ucontrol\nucontrol.build(10, 20, '@router', 0, 0)\n"
        res = compile_py(code)
        self.assertIn("ucontrol build 10 20 @router 0 0", res.mlog)

    def test_get_block_and_within(self):
        code = """from mlog import ucontrol
ucontrol.get_block(10, 20, outType, outBuild, outFloor)
ucontrol.getBlock(10, 20, outType, outBuild, outFloor)
ucontrol.within(10, 20, 5, outRes)
"""
        res = compile_py(code)
        self.assertIn("ucontrol getBlock 10 20 outType outBuild outFloor", res.mlog)
        self.assertIn("ucontrol within 10 20 5 outRes 0", res.mlog)

    def test_unit_control_aliases(self):
        code = """from mlog import unitControl, unit_control
unitControl.move(1, 2)
unit_control.move(3, 4)
"""
        res = compile_py(code)
        self.assertIn("ucontrol move 1 2 0 0 0", res.mlog)
        self.assertIn("ucontrol move 3 4 0 0 0", res.mlog)


class TestUnitLocateNamespace(unittest.TestCase):
    """Test modern ulocate.<method>(...) syntax compilation and semantics."""

    def test_locate_ore_4_and_5_args(self):
        code = """from mlog import ulocate
ulocate.ore('@copper', outX, outY, found)
ulocate.ore('@lead', outX, outY, found, customBuild)
"""
        res = compile_py(code)
        self.assertIn("ulocate ore core true @copper outX outY found building", res.mlog)
        self.assertIn("ulocate ore core true @lead outX outY found customBuild", res.mlog)

    def test_locate_building(self):
        code = "from mlog import ulocate\nulocate.building('core', True, outX, outY, found, b)\n"
        res = compile_py(code)
        self.assertIn("ulocate building core true @copper outX outY found b", res.mlog)

    def test_locate_spawn_3_and_4_args(self):
        code = """from mlog import ulocate
ulocate.spawn(outX, outY, found)
ulocate.spawn(outX, outY, found, b)
"""
        res = compile_py(code)
        self.assertIn("ulocate spawn core true @copper outX outY found building", res.mlog)
        self.assertIn("ulocate spawn core true @copper outX outY found b", res.mlog)

    def test_locate_damaged(self):
        code = "from mlog import ulocate\nulocate.damaged(outX, outY, found, b)\n"
        res = compile_py(code)
        self.assertIn("ulocate damaged core true @copper outX outY found b", res.mlog)

    def test_unit_locate_aliases(self):
        code = """from mlog import unitLocate, unit_locate
unitLocate.ore('@copper', outX, outY, found)
unit_locate.spawn(outX, outY, found)
"""
        res = compile_py(code)
        self.assertIn("ulocate ore core true @copper outX outY found building", res.mlog)
        self.assertIn("ulocate spawn core true @copper outX outY found building", res.mlog)


class TestUnitBackwardCompatibility(unittest.TestCase):
    """Test legacy ucontrol(...) and ulocate(...) 100% backward compatibility."""

    def test_legacy_ucontrol_calls(self):
        code = """from mlog import ucontrol, UnitControl
ucontrol('move', 10, 20)
ucontrol(UnitControl.MOVE, 30, 40)
ucontrol('idle')
"""
        res = compile_py(code)
        self.assertIn("ucontrol move 10 20 0 0 0", res.mlog)
        self.assertIn("ucontrol move 30 40 0 0 0", res.mlog)
        self.assertIn("ucontrol idle 0 0 0 0 0", res.mlog)

    def test_legacy_ulocate_call(self):
        code = "from mlog import ulocate\nulocate('ore', 'core', 'true', '@copper', outX, outY, found, b)\n"
        res = compile_py(code)
        self.assertIn("ulocate ore core true @copper outX outY found b", res.mlog)


class TestUnitErrorHandling(unittest.TestCase):
    """Test validation errors for invalid arity, unknown methods."""

    def test_ucontrol_invalid_arity(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ucontrol\nucontrol.move(1)\n")
        self.assertIn("expected ucontrol.move(x, y)", str(ctx.exception))

        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ucontrol\nucontrol.idle(1)\n")
        self.assertIn("expected ucontrol.idle()", str(ctx.exception))

    def test_ucontrol_unknown_method(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ucontrol\nucontrol.fly(10, 20)\n")
        self.assertIn("unknown ucontrol method", str(ctx.exception))

    def test_ulocate_invalid_arity(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ulocate\nulocate.ore('@copper', outX)\n")
        self.assertIn("expected ulocate.ore", str(ctx.exception))

        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ulocate\nulocate.building('core', True, outX)\n")
        self.assertIn("expected ulocate.building", str(ctx.exception))

    def test_ulocate_unknown_method(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ulocate\nulocate.enemy(outX, outY)\n")
        self.assertIn("unknown ulocate method", str(ctx.exception))


class TestUnitRuntimeCallability(unittest.TestCase):
    """Test direct Python execution of ucontrol/ulocate objects."""

    def test_runtime_ucontrol(self):
        self.assertIsNone(mlog.ucontrol("idle"))
        self.assertIsNone(mlog.ucontrol.idle())
        self.assertIsNone(mlog.ucontrol.move(10, 20))
        self.assertIsNone(mlog.ucontrol.approach(10, 20, 5))
        self.assertIsNone(mlog.ucontrol.pathfind(10, 20))
        self.assertIsNone(mlog.ucontrol.auto_pathfind())
        self.assertIsNone(mlog.ucontrol.autoPathfind())
        self.assertIsNone(mlog.ucontrol.boost(True))
        self.assertIsNone(mlog.ucontrol.target(0, 0, 1))
        self.assertIsNone(mlog.ucontrol.targetp("u", 1))
        self.assertIsNone(mlog.ucontrol.item_drop("c", 10))
        self.assertIsNone(mlog.ucontrol.item_take("c", "@copper", 10))
        self.assertIsNone(mlog.ucontrol.pay_drop())
        self.assertIsNone(mlog.ucontrol.pay_take(1))
        self.assertIsNone(mlog.ucontrol.pay_enter())
        self.assertIsNone(mlog.ucontrol.mine(0, 0))
        self.assertIsNone(mlog.ucontrol.flag(1))
        self.assertIsNone(mlog.ucontrol.build(0, 0, "@router", 0, 0))
        self.assertIsNone(mlog.ucontrol.deconstruct(0, 0))
        self.assertIsNone(mlog.ucontrol.get_block(0, 0, "t", "b", "f"))
        self.assertIsNone(mlog.ucontrol.within(0, 0, 5, "res"))
        self.assertIsNone(mlog.ucontrol.unbind())
        self.assertIsNone(mlog.unitControl.move(1, 2))
        self.assertIsNone(mlog.unit_control.move(1, 2))

    def test_runtime_ulocate(self):
        self.assertIsNone(mlog.ulocate("ore", "core", "true", "@copper", 0, 0, 0, 0))
        self.assertIsNone(mlog.ulocate.ore("@copper", 0, 0, 0))
        self.assertIsNone(mlog.ulocate.building("core", True, 0, 0, 0, 0))
        self.assertIsNone(mlog.ulocate.spawn(0, 0, 0))
        self.assertIsNone(mlog.ulocate.damaged(0, 0, 0, 0))
        self.assertIsNone(mlog.unitLocate.ore("@copper", 0, 0, 0))
        self.assertIsNone(mlog.unit_locate.ore("@copper", 0, 0, 0))


if __name__ == "__main__":
    unittest.main()
