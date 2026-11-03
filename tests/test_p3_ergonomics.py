"""Regression tests for P3 Ergonomics & Argument Binding:
1. Argument Binding & Validation (CRIT-01, CRIT-02, CRIT-03, MED-04)
2. Expression form for ucontrol.within
3. Tuple unpacking for ucontrol.get_block and ulocate keyword support
4. Output destination binding (dest=/out=) for sensor, read, uradar
5. IDE stubs and runtime execution consistency
"""

import unittest
from mlog import (
    compile_py,
    sensor,
    read,
    uradar,
    ucontrol,
    ulocate,
    status,
    StatusEffects,
    Items,
    RadarTarget,
    RadarSort,
)
from mlog.errors import CompileError
from mlog.validator import MlogValidator
from mlog.mindustry_validator import is_mindustry_available, validate_with_mindustry


class TestP3Ergonomics(unittest.TestCase):
    """Test suite for P3 Argument Binding, Expression Forms, Unpacking, and Destinations."""

    def compile_code(self, source: str) -> str:
        """Compile DSL source and validate syntax."""
        res = compile_py(source, validate=True)
        mlog_text = res.mlog.strip()
        MlogValidator.validate(mlog_text)
        return mlog_text

    def validate_with_jvm(self, mlog_text: str):
        """Validate generated mlog against real Mindustry v160.7 engine if available."""
        if is_mindustry_available():
            world_opcodes = ("query", "message", "spawn", "setrule", "weather", "effect", "explosion", "setmarker", "makemarker")
            if any(op in mlog_text for op in world_opcodes) and "#processor" not in mlog_text:
                test_mlog = "#processor: world\n" + mlog_text
            else:
                test_mlog = mlog_text
            valid, err, *_ = validate_with_mindustry(test_mlog)
            self.assertTrue(valid, f"JVM validation failed: {err}")

    # =========================================================================
    # 1. Argument Binding & Validation (CRIT-01, CRIT-02, CRIT-03, MED-04)
    # =========================================================================

    def test_crit01_flat_intrinsics_reject_keywords(self):
        """Flat intrinsics must strictly reject keyword arguments (no silent dropping)."""
        invalid_calls = [
            "ubind(unit=UnitType.flare)",
            "wait(seconds=1.0)",
            "print('hello', end='')",
            "setrate(rate=60)",
            "set(dest=x, value=1)",
            "op('add', dest=z, a=x, b=y)",
            "write(input=1, cell=cell1, address=0)",
            "control('enabled', target=block, p1=1)",
            "sound.play('pew', vol=1)",
            "sound.play_at('pew', x=10, y=20, volume=1)",
            "music.play('fine', vol=1)",
            "marker.texture(id=m1, name='square')",
            "marker.color(id=m1, color=col)",
        ]
        for call_expr in invalid_calls:
            source = f"from mlog import *\n{call_expr}\n"
            with self.assertRaises(CompileError, msg=f"Should reject: {call_expr}"):
                self.compile_code(source)

    def test_crit02_status_duplicate_arguments(self):
        """status.apply and status.clear must reject duplicate arguments via positional + keyword."""
        # Positional unit + keyword unit
        with self.assertRaises(CompileError) as ctx:
            self.compile_code("from mlog import status, StatusEffects\nstatus.apply(u, StatusEffects.BURNING, unit=u)")
        self.assertIn("duplicate argument 'unit'", str(ctx.exception))

        # Positional effect + keyword effect
        with self.assertRaises(CompileError) as ctx:
            self.compile_code("from mlog import status, StatusEffects\nstatus.clear(u, StatusEffects.BURNING, effect=StatusEffects.BURNING)")
        self.assertIn("duplicate argument 'effect'", str(ctx.exception))

        # Positional duration + keyword duration
        with self.assertRaises(CompileError) as ctx:
            self.compile_code("from mlog import status, StatusEffects\nstatus.apply(u, StatusEffects.BURNING, 5, duration=10)")
        self.assertIn("duplicate argument 'duration'", str(ctx.exception))

    def test_crit03_array_parameter_binding_and_duplicate_detection(self):
        """Array() must bind positional and keyword parameters correctly without shifting."""
        # 1. Positional block and size
        code = self.compile_code("arr = Array('cell1', 64)\narr[0] = 42")
        self.assertIn("write 42 cell1 0", code)

        # 2. Positional block, keyword size
        code = self.compile_code("arr = Array('cell1', size=64)\narr[1] = 43")
        self.assertIn("write 43 cell1 1", code)

        # 3. All keywords
        code = self.compile_code("arr = Array(block='bank1', size=128)\narr[2] = 44")
        self.assertIn("write 44 bank1 2", code)

        # 4. Duplicate size via positional and keyword
        with self.assertRaises(CompileError) as ctx:
            self.compile_code("arr = Array('cell1', 64, size=128)")
        self.assertIn("duplicate argument 'size'", str(ctx.exception))

        # 5. Duplicate block via positional and keyword
        with self.assertRaises(CompileError) as ctx:
            self.compile_code("arr = Array('cell1', 64, block='cell2')")
        self.assertIn("duplicate argument 'block'", str(ctx.exception))

    def test_med04_marker_arity_validation(self):
        """marker methods must validate argument count based on expected parameters."""
        # Valid calls
        code = self.compile_code("""
from mlog import marker
marker.remove(m1)
marker.color(m1, c)
marker.texture(m1, 'shape-circle')
""")
        self.assertIn("setmarker remove m1", code)
        self.assertIn("setmarker color m1 c", code)
        self.assertIn('setmarker texture m1 0 "shape-circle" 0', code)
        self.validate_with_jvm(code)

        # Missing argument
        with self.assertRaises(CompileError) as ctx:
            self.compile_code("from mlog import marker\nmarker.color(m1)")
        self.assertIn("expected 2 arguments", str(ctx.exception))

        # Excess argument
        with self.assertRaises(CompileError) as ctx:
            self.compile_code("from mlog import marker\nmarker.remove(m1, extra)")
        self.assertIn("expected 1 argument", str(ctx.exception))

    # =========================================================================
    # 2. Expression Forms (ucontrol.within)
    # =========================================================================

    def test_ucontrol_within_expression_form(self):
        """ucontrol.within(x, y, radius) supports expression form binding directly to target destination."""
        source = """
from mlog import ucontrol
in_range = ucontrol.within(10, 20, 5)
if ucontrol.within(10, 20, 5):
    ucontrol.idle()
"""
        code = self.compile_code(source)
        lines = code.splitlines()
        # Direct binding to in_range without temporary variable
        self.assertEqual(lines[0], "ucontrol within 10 20 5 in_range 0")
        self.validate_with_jvm(code)

    def test_ucontrol_within_statement_form_backward_compatibility(self):
        """ucontrol.within(x, y, radius, out_result) maintains 100% backward compatibility."""
        source = """
from mlog import ucontrol
ucontrol.within(10, 20, 5, res)
"""
        code = self.compile_code(source)
        self.assertEqual(code, "ucontrol within 10 20 5 res 0")
        self.validate_with_jvm(code)

    # =========================================================================
    # 3. Tuple Unpacking (ucontrol.get_block, ulocate keywords)
    # =========================================================================

    def test_ucontrol_get_block_tuple_unpacking(self):
        """ucontrol.get_block(x, y) supports tuple unpacking into (b_type, b_build, b_floor)."""
        source = """
from mlog import ucontrol
b_type, b_build, b_floor = ucontrol.get_block(15, 25)
b_type2, b_build2, b_floor2 = ucontrol.getBlock(30, 40)
"""
        code = self.compile_code(source)
        lines = code.splitlines()
        self.assertEqual(lines[0], "ucontrol getBlock 15 25 b_type b_build b_floor")
        self.assertEqual(lines[1], "ucontrol getBlock 30 40 b_type2 b_build2 b_floor2")
        self.validate_with_jvm(code)

    def test_ucontrol_get_block_statement_form_backward_compatibility(self):
        """ucontrol.get_block statement form with 5 arguments remains supported."""
        source = """
from mlog import ucontrol
ucontrol.get_block(15, 25, out_type, out_building, out_floor)
"""
        code = self.compile_code(source)
        self.assertEqual(code, "ucontrol getBlock 15 25 out_type out_building out_floor")
        self.validate_with_jvm(code)

    def test_ucontrol_get_block_unpacking_invalid_target_count(self):
        """ucontrol.get_block unpacking requires exactly 3 targets."""
        with self.assertRaises(CompileError) as ctx:
            self.compile_code("from mlog import ucontrol\na, b = ucontrol.get_block(10, 20)")
        self.assertIn("cannot unpack 2 variables from ucontrol.get_block", str(ctx.exception))

    def test_ulocate_keyword_arguments_in_unpacking(self):
        """ulocate.building and ulocate.ore support keyword arguments when unpacking."""
        source = """
from mlog import ulocate, Items
core_x, core_y, found_core, core_build = ulocate.building(group="core", enemy=True)
ore_x, ore_y, found_ore = ulocate.ore(ore=Items.copper)
"""
        code = self.compile_code(source)
        lines = code.splitlines()
        self.assertEqual(lines[0], "ulocate building core true @copper core_x core_y found_core core_build")
        self.assertEqual(lines[1], "ulocate ore core true @copper ore_x ore_y found_ore __tmp0")
        self.validate_with_jvm(code)

    def test_ulocate_duplicate_arguments(self):
        """ulocate must reject duplicate arguments via positional and keyword."""
        with self.assertRaises(CompileError) as ctx:
            self.compile_code("from mlog import ulocate\nx, y, f, b = ulocate.building('core', group='core')")
        self.assertIn("duplicate argument 'group'", str(ctx.exception))

    # =========================================================================
    # 4. Output Destination Binding (dest=/out=)
    # =========================================================================

    def test_sensor_dest_and_out_keywords(self):
        """sensor supports dest= and out= keywords and rejects invalid combinations."""
        source = """
from mlog import sensor, Items
sensor(vault1, Items.copper, dest=x)
sensor(vault1, Items.lead, out=y)
z = sensor(vault1, Items.silicon)
sensor(w, vault1, Items.coal)
"""
        code = self.compile_code(source)
        lines = code.splitlines()
        self.assertEqual(lines[0], "sensor x vault1 @copper")
        self.assertEqual(lines[1], "sensor y vault1 @lead")
        self.assertEqual(lines[2], "sensor z vault1 @silicon")
        self.assertEqual(lines[3], "sensor w vault1 @coal")
        self.validate_with_jvm(code)

        # Duplicate destination
        with self.assertRaises(CompileError) as ctx:
            self.compile_code("from mlog import sensor, Items\nsensor(res, vault1, Items.copper, dest=x)")
        self.assertIn("duplicate argument 'dest'", str(ctx.exception))

        # Both dest and out
        with self.assertRaises(CompileError) as ctx:
            self.compile_code("from mlog import sensor, Items\nsensor(vault1, Items.copper, dest=x, out=y)")
        self.assertIn("cannot pass both 'dest' and 'out'", str(ctx.exception))

        # Unexpected keyword
        with self.assertRaises(CompileError) as ctx:
            self.compile_code("from mlog import sensor, Items\nsensor(vault1, Items.copper, invalid=x)")
        self.assertIn("unexpected keyword argument 'invalid'", str(ctx.exception))

    def test_read_dest_and_out_keywords(self):
        """read supports dest= and out= keywords and rejects invalid combinations."""
        source = """
from mlog import read
read(cell1, 0, dest=x)
read(cell1, 1, out=y)
z = read(cell1, 2)
read(w, cell1, 3)
"""
        code = self.compile_code(source)
        lines = code.splitlines()
        self.assertEqual(lines[0], "read x cell1 0")
        self.assertEqual(lines[1], "read y cell1 1")
        self.assertEqual(lines[2], "read z cell1 2")
        self.assertEqual(lines[3], "read w cell1 3")
        self.validate_with_jvm(code)

        # Duplicate destination
        with self.assertRaises(CompileError) as ctx:
            self.compile_code("from mlog import read\nread(res, cell1, 0, dest=x)")
        self.assertIn("duplicate argument 'dest'", str(ctx.exception))

        # Both dest and out
        with self.assertRaises(CompileError) as ctx:
            self.compile_code("from mlog import read\nread(cell1, 0, dest=x, out=y)")
        self.assertIn("cannot pass both 'dest' and 'out'", str(ctx.exception))

        # Unexpected keyword
        with self.assertRaises(CompileError) as ctx:
            self.compile_code("from mlog import read\nread(cell1, 0, invalid=x)")
        self.assertIn("unexpected keyword argument 'invalid'", str(ctx.exception))

    def test_uradar_dest_and_out_keywords(self):
        """uradar supports dest= and out= keywords and default argument semantics."""
        source = """
from mlog import uradar, RadarTarget, RadarSort
uradar(out=t1)
uradar(RadarTarget.enemy, dest=t2)
t3 = uradar(RadarTarget.enemy, RadarTarget.flying)
uradar(RadarTarget.enemy, RadarTarget.any, RadarTarget.any, RadarSort.distance, 1, t4)
"""
        code = self.compile_code(source)
        lines = code.splitlines()
        self.assertEqual(lines[0], "uradar enemy any any distance 0 1 t1")
        self.assertEqual(lines[1], "uradar enemy any any distance 0 1 t2")
        self.assertEqual(lines[2], "uradar enemy flying any distance 0 1 t3")
        self.assertEqual(lines[3], "uradar enemy any any distance 0 1 t4")
        self.validate_with_jvm(code)

        # Duplicate destination
        with self.assertRaises(CompileError) as ctx:
            self.compile_code("from mlog import uradar, RadarTarget, RadarSort\nuradar(RadarTarget.enemy, RadarTarget.any, RadarTarget.any, RadarSort.distance, 1, t4, dest=x)")
        self.assertIn("duplicate argument 'out'", str(ctx.exception))

        # Both dest and out
        with self.assertRaises(CompileError) as ctx:
            self.compile_code("from mlog import uradar\nuradar(out=x, dest=y)")
        self.assertIn("cannot pass both 'dest' and 'out'", str(ctx.exception))

        # Unexpected keyword
        with self.assertRaises(CompileError) as ctx:
            self.compile_code("from mlog import uradar\nuradar(invalid=x)")
        self.assertIn("unexpected keyword argument 'invalid'", str(ctx.exception))

    # =========================================================================
    # 5. Runtime execution consistency (plain CPython)
    # =========================================================================

    def test_runtime_cpython_consistency(self):
        """Runtime stub calls must execute cleanly without raising TypeError under plain CPython."""
        # sensor, read, uradar keywords
        self.assertEqual(sensor("vault1", "@copper", dest="x"), 0)
        self.assertEqual(sensor("vault1", "@copper", out="y"), 0)
        self.assertEqual(read("cell1", 0, dest="x"), 0)
        self.assertEqual(read("cell1", 0, out="y"), 0)
        self.assertEqual(uradar(out="t1"), 0)
        self.assertEqual(uradar(dest="t2"), 0)

        # ucontrol.get_block unpacking
        b_type, b_build, b_floor = ucontrol.get_block(10, 20)
        self.assertIsNone(b_type)
        self.assertIsNone(b_build)
        self.assertIsNone(b_floor)

        # ucontrol.within expression
        self.assertEqual(ucontrol.within(10, 20, 5), 0)


if __name__ == "__main__":
    unittest.main()
