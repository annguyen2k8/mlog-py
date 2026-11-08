"""Comprehensive Mindustry Logic API Coverage & Decompiler Reconstruction Test Suite.

Covers:
- All 53 VM opcodes (28 Standard, 25 World Privileged).
- All subcommands and callable namespaces (control, ucontrol, ulocate, draw, cutscene, lookup, fetch, radar, uradar, sensor, status, sound, music, marker, query, message).
- Argument mapping: count, order, types, and dummy operand handling.
- Python DSL reconstruction: modern high-level idioms and safe fallbacks.
- Bidirectional compilation & round-trip bytecode verification.
- Preservation of noncanonical dummy operand spellings (ADR-004).
"""

import unittest

from src.decompiler import decompile
from src.decompiler.errors import DecompileError, MlogParseError
from src.mlog import compile_py


class TestDecompilerAPICoverage(unittest.TestCase):
    """Full API coverage test across all 53 Mindustry Logic opcodes and subcommands."""

    def _assert_roundtrip(self, mlog_in: str, expected_snippet: str = None) -> str:
        """Decompile mlog -> verify snippet in Python DSL -> recompile to mlog and assert exact equality."""
        py = decompile(mlog_in.strip() + "\n")
        if expected_snippet:
            self.assertIn(expected_snippet, py)
        recompiled = compile_py(py).mlog.strip()
        self.assertEqual(recompiled, mlog_in.strip())
        return py

    # =========================================================================
    # 1. Input & Output (io — 6 opcodes)
    # =========================================================================

    def test_io_read(self):
        self._assert_roundtrip("read val cell1 0", 'val = read("cell1", 0)')

    def test_io_write(self):
        self._assert_roundtrip('write 42 cell1 0', 'write(42, "cell1", 0)')

    def test_io_draw_subcommands(self):
        draw_cases = [
            ("draw clear 0 0 0 0 0 0", "draw.clear(0, 0, 0)"),
            ("draw color 255 128 0 255 0 0", "draw.color(255, 128, 0)"),
            ("draw color 255 128 0 100 0 0", "draw.color(255, 128, 0, 100)"),
            ("draw col 123456 0 0 0 0 0", "draw.col(123456)"),
            ("draw stroke 2 0 0 0 0 0", "draw.stroke(2)"),
            ("draw line 10 20 30 40 0 0", "draw.line(10, 20, 30, 40)"),
            ("draw rect 0 0 80 80 0 0", "draw.rect(0, 0, 80, 80)"),
            ("draw lineRect 5 5 50 50 0 0", "draw.line_rect(5, 5, 50, 50)"),
            ("draw poly 40 40 6 20 0 0", "draw.poly(40, 40, 6, 20)"),
            ("draw poly 40 40 6 20 45 0", "draw.poly(40, 40, 6, 20, 45)"),
            ("draw linePoly 40 40 8 15 0 0", "draw.line_poly(40, 40, 8, 15)"),
            ("draw triangle 0 0 10 20 30 0", "draw.triangle(0, 0, 10, 20, 30, 0)"),
            ("draw image 50 50 @copper 32 0 0", 'draw.image(50, 50, "@copper")'),
            ("draw print 10 20 @center 0 0 0", "draw.print(10, 20, Align.CENTER)"),
            ("draw translate 10 20 0 0 0 0", "draw.translate(10, 20)"),
            ("draw scale 2 2 0 0 0 0", "draw.scale(2, 2)"),
            ("draw rotate 0 0 45 0 0 0", "draw.rotate(45)"),
            ("draw reset 0 0 0 0 0 0", "draw.reset()"),
        ]
        for mlog_line, snippet in draw_cases:
            with self.subTest(draw=mlog_line):
                self._assert_roundtrip(mlog_line, snippet)

    def test_io_print(self):
        self._assert_roundtrip('print "hello world"', 'print("hello world")')

    def test_io_printchar(self):
        self._assert_roundtrip("printchar 65", "printchar(65)")

    def test_io_format(self):
        self._assert_roundtrip('format "formatted text"', 'format("formatted text")')

    # =========================================================================
    # 2. Block Control (block — 6 opcodes)
    # =========================================================================

    def test_block_drawflush(self):
        self._assert_roundtrip("drawflush display1", 'drawflush("display1")')

    def test_block_printflush(self):
        self._assert_roundtrip("printflush message1", 'printflush("message1")')

    def test_block_getlink(self):
        self._assert_roundtrip("getlink b 0", "b = getlink(0)")

    def test_block_control_subcommands(self):
        control_cases = [
            ("control enabled reactor1 1 0 0 0", 'control.enabled("reactor1", 1)'),
            ("control shoot turret1 10 20 1 0", 'control.shoot("turret1", 10, 20, 1)'),
            ("control shootp turret1 @unit 1 0 0", 'control.shootp("turret1", "@unit", 1)'),
            ("control config sorter1 @copper 0 0 0", 'control.config("sorter1", "@copper")'),
            ("control color light1 12345 0 0 0", 'control.color("light1", 12345)'),
        ]
        for mlog_line, snippet in control_cases:
            with self.subTest(control=mlog_line):
                self._assert_roundtrip(mlog_line, snippet)

    def test_block_control_parser_arity_validation(self):
        """MlogParser strictly enforces 6 arguments for control opcode."""
        with self.assertRaises(MlogParseError):
            decompile("control enabled reactor1 1\n")

    def test_block_control_noncanonical_zero_fallback(self):
        """Non-canonical zero dummy spellings preserve exact representation via fallback."""
        py = decompile("control shoot turret1 10 20 1 0.0\n")
        self.assertIn('control("shoot"', py)
        self.assertNotIn("control.shoot(", py)
        recompiled = compile_py(py).mlog.strip()
        self.assertEqual(recompiled, "control shoot turret1 10 20 1 0.0")

    def test_block_radar(self):
        self._assert_roundtrip(
            "radar enemy any any distance turret1 1 target",
            'target = radar("enemy", "any", "any", "distance", "turret1", 1)',
        )

    def test_block_sensor(self):
        self._assert_roundtrip(
            "sensor hp vault1 @health",
            'hp = sensor("vault1", raw("@health"))',
        )

    # =========================================================================
    # 3. Operations (operation — 6 opcodes)
    # =========================================================================

    def test_op_set(self):
        self._assert_roundtrip("set a 10", "a = 10")

    def test_op_logic_ops(self):
        self._assert_roundtrip("op add c a b", "c = a + b")
        self._assert_roundtrip("op min c a b", "c = min(a, b)")
        self._assert_roundtrip("op max c a b", "c = max(a, b)")
        self._assert_roundtrip("op not c a 0", "c = ~a")
        self._assert_roundtrip("op rand c 100 0", 'c = op("rand", 100)')

    def test_op_select(self):
        self._assert_roundtrip("select x equal a b 1 0", "x = 1 if a == b else 0")

    def test_op_lookup_types(self):
        types = ["item", "block", "unit", "liquid", "team"]
        for t in types:
            with self.subTest(lookup_type=t):
                self._assert_roundtrip(f"lookup {t} out 0", f'out = lookup("{t}", 0)')

    def test_op_packcolor(self):
        self._assert_roundtrip("packcolor col 1 0 0 1", "col = packcolor(1, 0, 0, 1)")

    def test_op_unpackcolor(self):
        self._assert_roundtrip("unpackcolor r g b a col", "unpackcolor(r, g, b, a, col)")

    # =========================================================================
    # 4. Flow Control (control — 5 opcodes)
    # =========================================================================

    def test_flow_wait(self):
        self._assert_roundtrip("wait 1.5", "wait(1.5)")

    def test_flow_stop(self):
        self._assert_roundtrip("stop", "stop()")

    def test_flow_end(self):
        self._assert_roundtrip("end", "end()")

    def test_flow_jump(self):
        mlog = "set a 0\njump 3 lessThan a 10\nset b 1\n"
        py = decompile(mlog)
        recompiled = compile_py(py).mlog.strip()
        self.assertTrue(len(recompiled) > 0)

    def test_flow_setrate(self):
        self._assert_roundtrip("setrate 1000", "setrate(1000)")

    # =========================================================================
    # 5. Unit Control (unit — 4 opcodes)
    # =========================================================================

    def test_unit_ubind(self):
        self._assert_roundtrip('ubind @flare', 'ubind("@flare")')

    def test_unit_ucontrol_all_actions(self):
        actions = [
            ("ucontrol idle 0 0 0 0 0", "ucontrol.idle()"),
            ("ucontrol stop 0 0 0 0 0", "ucontrol.stop()"),
            ("ucontrol move 100 200 0 0 0", "ucontrol.move(100, 200)"),
            ("ucontrol approach 50 60 10 0 0", "ucontrol.approach(50, 60, 10)"),
            ("ucontrol pathfind 10 20 0 0 0", "ucontrol.pathfind(10, 20)"),
            ("ucontrol autoPathfind 0 0 0 0 0", "ucontrol.auto_pathfind()"),
            ("ucontrol boost 1 0 0 0 0", "ucontrol.boost(1)"),
            ("ucontrol target 100 200 1 0 0", "ucontrol.target(100, 200, 1)"),
            ("ucontrol targetp unit 1 0 0 0", "ucontrol.targetp(unit, 1)"),
            ("ucontrol itemDrop core1 50 0 0 0", 'ucontrol.item_drop("core1", 50)'),
            ("ucontrol itemTake core1 @copper 30 0 0", 'ucontrol.item_take("core1", "@copper", 30)'),
            ("ucontrol payDrop 0 0 0 0 0", "ucontrol.pay_drop()"),
            ("ucontrol payTake 1 0 0 0 0", "ucontrol.pay_take(1)"),
            ("ucontrol payEnter 0 0 0 0 0", "ucontrol.pay_enter()"),
            ("ucontrol mine 15 25 0 0 0", "ucontrol.mine(15, 25)"),
            ("ucontrol flag 999 0 0 0 0", "ucontrol.flag(999)"),
            ("ucontrol build 10 20 @router 0 0", 'ucontrol.build(10, 20, "@router", 0, 0)'),
            ("ucontrol deconstruct 10 20 0 0 0", "ucontrol.deconstruct(10, 20)"),
            ("ucontrol getBlock 10 20 out_t out_b out_f", "ucontrol.get_block(10, 20, out_t, out_b, out_f)"),
            ("ucontrol within 10 20 5 in_range 0", "ucontrol.within(10, 20, 5, in_range)"),
            ("ucontrol unbind 0 0 0 0 0", "ucontrol.unbind()"),
        ]
        for mlog_line, snippet in actions:
            with self.subTest(ucontrol=mlog_line):
                self._assert_roundtrip(mlog_line, snippet)

    def test_unit_uradar(self):
        self._assert_roundtrip(
            "uradar enemy any any distance 0 1 target",
            'target = uradar("enemy", "any", "any", "distance", 1)',
        )

    def test_unit_ulocate_subcommands(self):
        locates = [
            ("ulocate ore core true @copper ox oy found ob", 'ox, oy, found, ob = ulocate.ore("@copper")'),
            ("ulocate building core false @copper ox oy found ob", 'ox, oy, found, ob = ulocate.building("core", False)'),
            ("ulocate spawn core true @copper ox oy found ob", "ox, oy, found, ob = ulocate.spawn()"),
            ("ulocate damaged core true @copper ox oy found ob", "ox, oy, found, ob = ulocate.damaged()"),
        ]
        for mlog_line, snippet in locates:
            with self.subTest(ulocate=mlog_line):
                self._assert_roundtrip(mlog_line, snippet)

    # =========================================================================
    # 6. Internal Opcode (1 opcode)
    # =========================================================================

    def test_internal_noop(self):
        self._assert_roundtrip("noop", "noop()")

    # =========================================================================
    # 7. World Processor Statements (world, privileged — 25 opcodes)
    # =========================================================================

    def test_world_query(self):
        self._assert_roundtrip(
            "query circle unit @sharded 10 20 5 0",
            'query("circle", "unit", "@sharded", 10, 20, 5, 0)',
        )

    def test_world_getblock(self):
        self._assert_roundtrip(
            "getblock floor tile 10 20",
            'getblock("floor", tile, 10, 20)',
        )

    def test_world_setblock(self):
        self._assert_roundtrip(
            "setblock floor @stone 10 20 @sharded 0",
            'setblock("floor", "@stone", 10, 20, "@sharded", 0)',
        )

    def test_world_spawn(self):
        self._assert_roundtrip(
            "spawn @flare 10 20 0 @sharded u 0",
            'u = spawn("@flare", 10, 20, 0, "@sharded", 0)',
        )

    def test_world_bullet(self):
        self._assert_roundtrip(
            "bullet b @flare 0 10 20 5 @sharded null -1 1 1 -1 -1",
            'b = bullet("@flare", 0, 10, 20, 5, "@sharded", None, -1, 1, 1, -1, -1)',
        )

    def test_world_status(self):
        self._assert_roundtrip(
            "status false @status-burning @unit 5",
            'status(False, "@status-burning", "@unit", 5)',
        )

    def test_world_weathersense(self):
        self._assert_roundtrip(
            "weathersense ws @snowing",
            'weathersense(ws, "@snowing")',
        )

    def test_world_weatherset(self):
        self._assert_roundtrip(
            "weatherset @snowing 1",
            'weatherset("@snowing", 1)',
        )

    def test_world_spawnwave(self):
        self._assert_roundtrip(
            "spawnwave 10 20 1",
            "spawnwave(10, 20, 1)",
        )

    def test_world_setrule(self):
        self._assert_roundtrip(
            "setrule buildSpeed 2 @sharded 0 0 0",
            'setrule("buildSpeed", 2, "@sharded", 0, 0, 0)',
        )

    def test_world_message(self):
        self._assert_roundtrip(
            "message announce 3 @wait",
            'message("announce")',
        )

    def test_world_cutscene_actions(self):
        cutscene_cases = [
            ("cutscene pan 10 20 0.06 0", "cutscene.pan(10, 20)"),
            ("cutscene zoom 2.5 0 0 0", "cutscene.zoom(2.5)"),
            ("cutscene shake 5 1 0 0", "cutscene.shake(5, 1)"),
            ("cutscene setHud 1 0 0 0", "cutscene.set_hud(True)"),
            ("cutscene stop 0 0 0 0", "cutscene.stop()"),
            ("cutscene active dest 0 0 0", "dest = cutscene.active()"),
            ("cutscene getHud hud 0 0 0", "hud = cutscene.get_hud()"),
        ]
        for mlog_line, snippet in cutscene_cases:
            with self.subTest(cutscene=mlog_line):
                self._assert_roundtrip(mlog_line, snippet)

    def test_world_effect(self):
        self._assert_roundtrip(
            "effect explosion 10 20 0 @white 0",
            'effect("explosion", 10, 20, 0, "@white", 0)',
        )

    def test_world_explosion(self):
        self._assert_roundtrip(
            "explosion @sharded 10 20 50 100 1 1 0 1",
            'explosion("@sharded", 10, 20, 50, 100, 1, 1, 0, 1)',
        )

    def test_world_fetch(self):
        self._assert_roundtrip(
            "fetch unit u @sharded 0 0",
            'fetch("unit", u, "@sharded", 0, 0)',
        )

    def test_world_sync(self):
        self._assert_roundtrip(
            "sync myvar",
            "sync(myvar)",
        )

    def test_world_getflag(self):
        self._assert_roundtrip(
            "getflag f 1",
            "getflag(f, 1)",
        )

    def test_world_setflag(self):
        self._assert_roundtrip(
            "setflag 1 1",
            "setflag(1, 1)",
        )

    def test_world_setprop(self):
        self._assert_roundtrip(
            "setprop @health vault1 100",
            'setprop("@health", vault1, 100)',
        )

    def test_world_playsound(self):
        self._assert_roundtrip(
            "playsound false @sfx-shoot 1 1 0 0 0 true",
            'playsound(False, "@sfx-shoot", 1, 1, 0, 0, 0, True)',
        )

    def test_world_playmusic(self):
        self._assert_roundtrip(
            'playmusic "game1" true',
            'playmusic("game1", True)',
        )

    def test_world_setmarker(self):
        self._assert_roundtrip(
            "setmarker pos 1 10 20 0",
            'setmarker("pos", 1, 10, 20, 0)',
        )

    def test_world_makemarker(self):
        self._assert_roundtrip(
            "makemarker shape 1 10 20 true",
            'makemarker("shape", 1, 10, 20, True)',
        )

    def test_world_localeprint(self):
        self._assert_roundtrip(
            'localeprint "prop"',
            'localeprint("prop")',
        )

    def test_world_clientdata(self):
        self._assert_roundtrip(
            "clientdata 1 2 0",
            "clientdata(1, 2, 0)",
        )


if __name__ == "__main__":
    unittest.main()
