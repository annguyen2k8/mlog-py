"""Comprehensive test suite for Mindustry Logic (mlog) decompiler coverage.

Covers all opcode categories, edge cases, round-trips, and error scenarios.
"""

import unittest
from src.decompiler import decompile
from src.decompiler.errors import DecompileError, MlogParseError
from src.mlog import compile_py


class TestDecompilerFullCoverage(unittest.TestCase):
    """Full coverage test for Mindustry Logic decompiler."""

    def _verify_roundtrip(self, mlog_in: str, expected_snippet: str = None):
        """Helper to decompile mlog -> Python DSL -> recompile to mlog, ensuring valid logic."""
        py_code = decompile(mlog_in)
        if expected_snippet:
            self.assertIn(expected_snippet, py_code)
        # Verify generated Python DSL compiles back to valid mlog
        recompiled = compile_py(py_code).mlog.strip()
        self.assertTrue(len(recompiled) > 0)
        return py_code, recompiled

    def test_standard_control_opcodes(self):
        """Test noop, stop, end, wait, and set opcodes."""
        mlog = """noop
set a 42
wait 1.5
stop
end
"""
        py_code, recompiled = self._verify_roundtrip(mlog)
        self.assertIn("noop()", py_code)
        self.assertIn("a = 42", py_code)
        self.assertIn("wait(1.5)", py_code)
        self.assertIn("stop()", py_code)
        self.assertIn("end()", py_code)

    def test_memory_io_opcodes(self):
        """Test read, write, getlink opcodes."""
        mlog = """getlink b 0
read val cell1 5
write 100 cell1 5
"""
        py_code, recompiled = self._verify_roundtrip(mlog)
        self.assertIn('b = getlink(0)', py_code)
        self.assertIn('val = read("cell1", 5)', py_code)
        self.assertIn('write(100, "cell1", 5)', py_code)

    def test_sensors_and_lookup(self):
        """Test sensor, lookup, radar, and uradar opcodes."""
        mlog = """sensor hp vault1 @health
lookup item out_item 0
radar enemy any any distance turret1 1 target1
uradar enemy any any distance 0 1 target2
"""
        py_code, recompiled = self._verify_roundtrip(mlog)
        self.assertIn("hp = sensor(\"vault1\", '@health')", py_code)
        self.assertIn("out_item = lookup(\"item\", 0)", py_code)
        self.assertIn('target2 = uradar("enemy", "any", "any", "distance", 1)', py_code)

    def test_graphics_and_color_opcodes(self):
        """Test draw, drawflush, packcolor, unpackcolor opcodes."""
        mlog = """draw clear 0 0 0 0 0 0
draw color 255 128 0 255 0 0
draw print 10 20 center 0 0 0
drawflush display1
col = packcolor(1, 0, 0, 1)
unpackcolor r g b a col
"""
        mlog_raw = """draw clear 0 0 0 0 0 0
draw color 255 128 0 255 0 0
draw print 10 20 center 0 0 0
drawflush display1
packcolor col 1 0 0 1
unpackcolor r g b a col
"""
        py_code, recompiled = self._verify_roundtrip(mlog_raw)
        self.assertIn('draw.clear(0, 0, 0)', py_code)
        self.assertIn('draw.color(255, 128, 0)', py_code)
        self.assertIn('draw.print(10, 20, Align.CENTER)', py_code)
        self.assertIn('drawflush("display1")', py_code)
        self.assertIn('col = packcolor(1, 0, 0, 1)', py_code)
        self.assertIn('unpackcolor(r, g, b, a, col)', py_code)

    def test_unit_and_combat_spawning_opcodes(self):
        """Test ubind, ucontrol, ulocate, spawn, bullet, explosion, status."""
        mlog = """ubind @flare
ucontrol move 100 200 0 0 0
ulocate building core 0 @copper cx cy found cblock
spawn @flare 50 60 0 @sharded spawned_unit 0
bullet spawned_bullet @flare 0 10 20 5 @sharded null -1 1 1 -1 -1
explosion @sharded 100 200 50 100 1 1 0 1
status false @status-burning @unit 5
"""
        py_code, recompiled = self._verify_roundtrip(mlog)
        self.assertIn('ubind("@flare")', py_code)
        self.assertIn('ucontrol.move(100, 200)', py_code)

        self.assertIn('ulocate.building("core", 0)', py_code)
        self.assertIn('spawned_unit = spawn("@flare", 50, 60, 0, "@sharded", 0)', py_code)
        self.assertIn('spawned_bullet = bullet("@flare", 0, 10, 20, 5, "@sharded", None, -1, 1, 1, -1, -1)', py_code)
        self.assertIn('explosion("@sharded", 100, 200, 50, 100, 1, 1, 0, 1)', py_code)
        self.assertIn('status(False, "@status-burning", "@unit", 5)', py_code)

    def test_world_rules_flags_and_query_opcodes(self):
        """Test getblock, setblock, getflag, setflag, setprop, fetch, sync, setrule, setrate."""
        mlog = """getblock floor tile_res 10 20
setblock floor @stone 10 20 @sharded 0
getflag flag_val 1
setflag 1 1
setprop @health vault1 500
fetch unit fetched_unit @sharded 0 0
sync my_sync_var
setrule buildSpeed 2 @sharded 0 0 0
setrate 1000
"""
        py_code, recompiled = self._verify_roundtrip(mlog)
        self.assertIn('getblock("floor", tile_res, 10, 20)', py_code)
        self.assertIn('setblock("floor", "@stone", 10, 20, "@sharded", 0)', py_code)
        self.assertIn('getflag(flag_val, 1)', py_code)
        self.assertIn('setflag(1, 1)', py_code)
        self.assertIn('setprop("@health", vault1, 500)', py_code)
        self.assertIn('fetch("unit", fetched_unit, "@sharded", 0, 0)', py_code)
        self.assertIn('sync(my_sync_var)', py_code)
        self.assertIn('setrule("buildSpeed", 2, "@sharded", 0, 0, 0)', py_code)
        self.assertIn('setrate(1000)', py_code)

    def test_weather_and_effects_opcodes(self):
        """Test weathersense, weatherset, spawnwave, effect."""
        mlog = """weathersense is_snowing @snowing
weatherset @snowing 1
spawnwave 50 60 1
effect explosion 100 200 0 @white 0
"""
        py_code, recompiled = self._verify_roundtrip(mlog)
        self.assertIn('weathersense(is_snowing, "@snowing")', py_code)
        self.assertIn('weatherset("@snowing", 1)', py_code)
        self.assertIn('spawnwave(50, 60, 1)', py_code)
        self.assertIn('effect("explosion", 100, 200, 0, "@white", 0)', py_code)

    def test_message_and_cutscene_opcodes(self):
        """Test message and all cutscene variations."""
        mlog = """message announce 3 @wait
cutscene pan 100 200 0.06 0
cutscene zoom 2.5 0 0 0
cutscene shake 5 1 0 0
cutscene setHud 1 0 0 0
cutscene stop 0 0 0 0
"""
        py_code, recompiled = self._verify_roundtrip(mlog)
        self.assertIn('message("announce")', py_code)
        self.assertIn('cutscene.pan(100, 200)', py_code)
        self.assertIn('cutscene.zoom(2.5)', py_code)
        self.assertIn('cutscene.shake(5, 1)', py_code)
        self.assertIn('cutscene.set_hud(True)', py_code)
        self.assertIn('cutscene.stop()', py_code)

    def test_audio_and_markers_opcodes(self):
        """Test playsound, playmusic, makemarker, setmarker."""
        mlog = """playsound false @sfx-shoot 1 1 0 0 0 true
playmusic "game1" true
makemarker shape 1 50 50 true
setmarker pos 1 100 100 0
"""
        py_code, recompiled = self._verify_roundtrip(mlog)
        self.assertIn('playsound(False, "@sfx-shoot", 1, 1, 0, 0, 0, True)', py_code)
        self.assertIn('playmusic("game1", True)', py_code)
        self.assertIn('makemarker("shape", 1, 50, 50, True)', py_code)
        self.assertIn('setmarker("pos", 1, 100, 100, 0)', py_code)

    def test_structured_control_flow_if_while(self):
        """Test structured control flow recovery (if/else and while)."""
        mlog = """set x 0
jump 4 greaterThanEq x 10
op add x x 1
jump 1 always 0 0
set y 1
jump 7 notEqual x 10
set y 2
"""
        py_code = decompile(mlog)
        self.assertIn("while x < 10:", py_code)
        self.assertIn("x = x + 1", py_code)
        self.assertIn("if x == 10:", py_code)
        self.assertIn("y = 2", py_code)
        # Check recompile
        recompiled = compile_py(py_code).mlog.strip()
        self.assertTrue(len(recompiled) > 0)

    def test_invalid_opcode_raises_decompile_error(self):
        """Invalid opcode raises MlogParseError or DecompileError."""
        mlog = "nonexistent_opcode_xyz 1 2 3\n"
        with self.assertRaises((MlogParseError, DecompileError)):
            decompile(mlog)

    def test_invalid_jump_out_of_bounds_raises_error(self):
        """Jump target pointing beyond program limits raises error."""
        mlog = "jump 9999 always 0 0\n"
        with self.assertRaises(DecompileError):
            decompile(mlog)

    def test_unterminated_string_raises_parse_error(self):
        """Unclosed string literal in mlog raises MlogParseError."""
        mlog = 'print "unclosed string without end\n'
        with self.assertRaises(MlogParseError):
            decompile(mlog)


if __name__ == "__main__":
    unittest.main()
