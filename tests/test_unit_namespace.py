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

    def test_legacy_unit_control_aliases_removed(self):
        """Verify legacy unitControl and unit_control aliases are completely removed."""
        with self.assertRaises(Exception):
            compile_py("from mlog import unitControl\nunitControl.move(1, 2)\n")
        with self.assertRaises(Exception):
            compile_py("from mlog import unit_control\nunit_control.move(1, 2)\n")
        self.assertFalse(hasattr(mlog, "unitControl"))
        self.assertFalse(hasattr(mlog, "unit_control"))


class TestUnitLocateNamespace(unittest.TestCase):
    """Test modern ulocate.<method>(...) syntax compilation and semantics."""

    def test_locate_ore_4_and_5_args(self):
        code = """from mlog import ulocate
ulocate.ore('@copper', outX, outY, found)
ulocate.ore('@lead', outX, outY, found, customBuild)
"""
        res = compile_py(code)
        self.assertIn("ulocate ore core true @copper outX outY found __tmp0", res.mlog)
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
        self.assertIn("ulocate spawn core true @copper outX outY found __tmp0", res.mlog)
        self.assertIn("ulocate spawn core true @copper outX outY found b", res.mlog)

    def test_locate_damaged(self):
        code = "from mlog import ulocate\nulocate.damaged(outX, outY, found, b)\n"
        res = compile_py(code)
        self.assertIn("ulocate damaged core true @copper outX outY found b", res.mlog)

    def test_legacy_unit_locate_aliases_removed(self):
        """Verify legacy unitLocate and unit_locate aliases are completely removed."""
        with self.assertRaises(Exception):
            compile_py("from mlog import unitLocate\nunitLocate.ore('@copper', outX, outY, found)\n")
        with self.assertRaises(Exception):
            compile_py("from mlog import unit_locate\nunit_locate.spawn(outX, outY, found)\n")
        self.assertFalse(hasattr(mlog, "unitLocate"))
        self.assertFalse(hasattr(mlog, "unit_locate"))


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
        self.assertFalse(hasattr(mlog, "unitControl"))
        self.assertFalse(hasattr(mlog, "unit_control"))

    def test_runtime_ulocate(self):
        self.assertIsNone(mlog.ulocate("ore", "core", "true", "@copper", 0, 0, 0, 0))
        self.assertIsNone(mlog.ulocate.ore("@copper", 0, 0, 0))
        self.assertIsNone(mlog.ulocate.building("core", True, 0, 0, 0, 0))
        self.assertIsNone(mlog.ulocate.spawn(0, 0, 0))
        self.assertIsNone(mlog.ulocate.damaged(0, 0, 0, 0))
        self.assertFalse(hasattr(mlog, "unitLocate"))
        self.assertFalse(hasattr(mlog, "unit_locate"))

        # Pure Python runtime tuple unpacking
        cx, cy, cfound, cbuild = mlog.ulocate.building("core", False)
        self.assertEqual((cx, cy, cfound, cbuild), (0.0, 0.0, 0, None))

        ox, oy, ofound = mlog.ulocate.ore("@copper")
        self.assertEqual((ox, oy, ofound), (0.0, 0.0, 0))

        sx, sy, sfound, sbuild = mlog.ulocate.spawn()
        self.assertEqual((sx, sy, sfound, sbuild), (0.0, 0.0, 0, None))

        dx, dy, dfound, dbuild = mlog.ulocate.damaged()
        self.assertEqual((dx, dy, dfound, dbuild), (0.0, 0.0, 0, None))


class TestUnitLocateTupleUnpacking(unittest.TestCase):
    """Comprehensive test suite for ulocate tuple unpacking syntax and semantics."""

    def test_ulocate_building_unpacking(self):
        """Verify building search with 4 target variables lowers cleanly."""
        code = """from mlog import ulocate
core_x, core_y, found_core, core_build = ulocate.building("core", False)
enemy_x, enemy_y, found_enemy, enemy_build = ulocate.building("core", True)
"""
        res = compile_py(code)
        self.assertIn("ulocate building core false @copper core_x core_y found_core core_build", res.mlog)
        self.assertIn("ulocate building core true @copper enemy_x enemy_y found_enemy enemy_build", res.mlog)

    def test_ulocate_ore_unpacking(self):
        """Verify ore search with 3 target variables lowers cleanly with dummy building."""
        code = """from mlog import ulocate
ore_x, ore_y, found_ore = ulocate.ore("@copper")
lead_x, lead_y, found_lead = ulocate.ore("@lead")
"""
        res = compile_py(code)
        self.assertIn("ulocate ore core true @copper ore_x ore_y found_ore __tmp0", res.mlog)
        self.assertIn("ulocate ore core true @lead lead_x lead_y found_lead __tmp1", res.mlog)

    def test_ulocate_spawn_unpacking(self):
        """Verify spawn search with 4 and 3 target variables lowers cleanly."""
        code = """from mlog import ulocate
sx, sy, sfound, sbuild = ulocate.spawn()
sx2, sy2, sfound2 = ulocate.spawn()
"""
        res = compile_py(code)
        self.assertIn("ulocate spawn core true @copper sx sy sfound sbuild", res.mlog)
        self.assertIn("ulocate spawn core true @copper sx2 sy2 sfound2 __tmp0", res.mlog)

    def test_ulocate_damaged_unpacking(self):
        """Verify damaged search with 4 target variables lowers cleanly."""
        code = """from mlog import ulocate
dx, dy, dfound, dbuild = ulocate.damaged()
"""
        res = compile_py(code)
        self.assertIn("ulocate damaged core true @copper dx dy dfound dbuild", res.mlog)

    def test_ulocate_list_unpacking_syntax(self):
        """Verify bracket list unpacking syntax [a, b, c] lowers identically."""
        code = """from mlog import ulocate
[core_x, core_y, found_core, core_build] = ulocate.building("core", False)
[ore_x, ore_y, found_ore] = ulocate.ore("@copper")
"""
        res = compile_py(code)
        self.assertIn("ulocate building core false @copper core_x core_y found_core core_build", res.mlog)
        self.assertIn("ulocate ore core true @copper ore_x ore_y found_ore __tmp0", res.mlog)

    def test_wrong_receiving_variable_count(self):
        """Verify mismatched receiving variable count raises descriptive CompileError."""
        # building expects 3 or 4
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ulocate\ncx, cy = ulocate.building('core', False)\n")
        self.assertIn("expects 3 or 4 target variables", str(ctx.exception))

        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ulocate\ncx, cy, cfound, cb, extra = ulocate.building('core', False)\n")
        self.assertIn("expects 3 or 4 target variables", str(ctx.exception))

        # ore expects 3 or 4
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ulocate\nox, oy = ulocate.ore('@copper')\n")
        self.assertIn("expects 3 or 4 target variables", str(ctx.exception))

        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ulocate\nox, oy, ofound, ob, extra = ulocate.ore('@copper')\n")
        self.assertIn("expects 3 or 4 target variables", str(ctx.exception))

        # damaged expects 3 or 4
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ulocate\ndx, dy = ulocate.damaged()\n")
        self.assertIn("expects 3 or 4 target variables", str(ctx.exception))

        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ulocate\ndx, dy, df, db, extra = ulocate.damaged()\n")
        self.assertIn("expects 3 or 4 target variables", str(ctx.exception))

        # spawn expects 3 or 4
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ulocate\nsx, sy = ulocate.spawn()\n")
        self.assertIn("expects 3 or 4 target variables", str(ctx.exception))

        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ulocate\nsx, sy, sf, sb, extra = ulocate.spawn()\n")
        self.assertIn("expects 3 or 4 target variables", str(ctx.exception))

    def test_duplicate_target_variable_rejected(self):
        """Verify duplicate variable names in tuple unpacking targets are rejected."""
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ulocate\ncx, cx, cfound, cb = ulocate.building('core', False)\n")
        self.assertIn("duplicate variable name 'cx'", str(ctx.exception))

        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ulocate\nox, oy, ox = ulocate.ore('@copper')\n")
        self.assertIn("duplicate variable name 'ox'", str(ctx.exception))

    def test_target_variable_not_clobbered(self):
        """Verify user variable named 'building' is NOT overwritten by ulocate.ore dummy output."""
        code = """from mlog import ulocate
building = 123
ore_x, ore_y, found_ore = ulocate.ore("@copper")
"""
        res = compile_py(code)
        # Verify the emitted mlog does NOT use user variable 'building' for outBuild
        self.assertNotIn("ulocate ore core true @copper ore_x ore_y found_ore building", res.mlog)
        self.assertIn("ulocate ore core true @copper ore_x ore_y found_ore __tmp0", res.mlog)

    def test_ulocate_4_variable_ore_unpacking(self):
        """Verify ore search with 4 target variables binds the user's fourth target."""
        code = """from mlog import ulocate
ox, oy, ofound, obuild = ulocate.ore("@copper")
"""
        res = compile_py(code)
        self.assertIn("ulocate ore core true @copper ox oy ofound obuild", res.mlog)

    def test_ulocate_3_variable_building_and_damaged_unpacking(self):
        """Verify building and damaged with 3 target variables compile cleanly using compiler temps."""
        code = """from mlog import ulocate
cx, cy, cfound = ulocate.building("core", False)
dx, dy, dfound = ulocate.damaged()
"""
        res = compile_py(code)
        self.assertIn("ulocate building core false @copper cx cy cfound __tmp0", res.mlog)
        self.assertIn("ulocate damaged core true @copper dx dy dfound __tmp1", res.mlog)

    def test_pure_python_all_unpacking_variants(self):
        """Verify pure Python execution supports canonical tuple unpacking, wrappers, intermediate variables, and nested unpacking."""
        from mlog import ulocate, LocateResult, OreLocateResult

        # Canonical unpacking
        c4_x, c4_y, c4_f, c4_b = ulocate.building("core", False)
        o3_x, o3_y, o3_f = ulocate.ore("@copper")
        s4_x, s4_y, s4_f, s4_b = ulocate.spawn()
        d4_x, d4_y, d4_f, d4_b = ulocate.damaged()

        self.assertEqual((c4_x, c4_y, c4_f, c4_b), (0.0, 0.0, 0, None))
        self.assertEqual((o3_x, o3_y, o3_f), (0.0, 0.0, 0))
        self.assertEqual((s4_x, s4_y, s4_f, s4_b), (0.0, 0.0, 0, None))
        self.assertEqual((d4_x, d4_y, d4_f, d4_b), (0.0, 0.0, 0, None))

        # Wrapper functions (previously failed under caller bytecode sniffing)
        def find_core():
            return ulocate.building("core", False)

        def find_ore():
            return ulocate.ore("@copper")

        wc_x, wc_y, wc_f, wc_b = find_core()
        self.assertEqual((wc_x, wc_y, wc_f, wc_b), (0.0, 0.0, 0, None))
        wo_x, wo_y, wo_f = find_ore()
        self.assertEqual((wo_x, wo_y, wo_f), (0.0, 0.0, 0))

        # Intermediate variable assignment and attribute access
        res_b = ulocate.building("core", False)
        self.assertIsInstance(res_b, LocateResult)
        self.assertEqual((res_b.x, res_b.y, res_b.found, res_b.building), (0.0, 0.0, 0, None))
        ib_x, ib_y, ib_f, ib_b = res_b
        self.assertEqual((ib_x, ib_y, ib_f, ib_b), (0.0, 0.0, 0, None))

        res_o = ulocate.ore("@copper")
        self.assertIsInstance(res_o, OreLocateResult)
        self.assertEqual((res_o.x, res_o.y, res_o.found), (0.0, 0.0, 0))
        io_x, io_y, io_f = res_o
        self.assertEqual((io_x, io_y, io_f), (0.0, 0.0, 0))

        # Nested unpacking
        (no_x, no_y, no_f), tag = ulocate.ore("@copper"), "marker"
        self.assertEqual((no_x, no_y, no_f), (0.0, 0.0, 0))
        self.assertEqual(tag, "marker")

        (nb_x, nb_y, nb_f, nb_b), num = ulocate.building("core", False), 42
        self.assertEqual((nb_x, nb_y, nb_f, nb_b), (0.0, 0.0, 0, None))
        self.assertEqual(num, 42)

        # Arity mismatches raise standard Python ValueError
        with self.assertRaises(ValueError):
            a, b = ulocate.ore("@copper")

        with self.assertRaises(ValueError):
            a, b, c, d, e = ulocate.building("core", False)

        # Mock notification docstring check
        self.assertIn("does NOT connect to or query a live Mindustry instance", LocateResult.__doc__)
        self.assertIn("does NOT connect to or query a live Mindustry instance", OreLocateResult.__doc__)

    def test_single_variable_assignment_rejected(self):
        """Verify assigning multi-output ulocate to a single variable without unpacking fails."""
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ulocate\nres = ulocate.building('core', False)\n")
        self.assertIn("must be unpacked into a tuple", str(ctx.exception))

        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ulocate\nres = ulocate.ore('@copper')\n")
        self.assertIn("must be unpacked into a tuple", str(ctx.exception))

    def test_invalid_unpacking_targets(self):
        """Verify non-variable targets (subscripts, Vars) inside unpacking are rejected."""
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ulocate, Array\narr = Array('cell1', 10)\ncx, arr[0], cfound, cb = ulocate.building('core', False)\n")
        self.assertIn("simple variable names", str(ctx.exception))

        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ulocate, Vars\ncx, cy, cfound, Vars = ulocate.building('core', False)\n")
        self.assertIn("cannot unpack into 'Vars'", str(ctx.exception))

        with self.assertRaises(CompileError) as ctx:
            compile_py("a, b, c, d = 42\n")
        self.assertIn("tuple unpacking is only supported for 'ulocate'", str(ctx.exception))

    def test_invalid_argument_counts_for_unpacking(self):
        """Verify calling ulocate with incorrect parameter counts raises CompileError."""
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ulocate\ncx, cy, cfound, cb = ulocate.building('core')\n")
        self.assertIn("invalid arguments for ulocate.building", str(ctx.exception))

        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ulocate\nox, oy, ofound = ulocate.ore()\n")
        self.assertIn("invalid arguments for ulocate.ore", str(ctx.exception))

        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ulocate\nsx, sy, sf, sb = ulocate.spawn('extra')\n")
        self.assertIn("invalid arguments for ulocate.spawn", str(ctx.exception))

        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ulocate\ndx, dy, df, db = ulocate.damaged('extra')\n")
        self.assertIn("invalid arguments for ulocate.damaged", str(ctx.exception))

    def test_statement_call_helpful_errors(self):
        """Verify statement calls with unpack-style arity guide the user to unpacking."""
        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ulocate\nulocate.building('core', False)\n")
        self.assertIn("tuple unpacking use: core_x, core_y, found, building", str(ctx.exception))

        with self.assertRaises(CompileError) as ctx:
            compile_py("from mlog import ulocate\nulocate.ore('@copper')\n")
        self.assertIn("tuple unpacking use: out_x, out_y, out_found", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
