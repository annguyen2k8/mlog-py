"""Tier 4 Regression Suite: World Processor & Map Scripting - Group E (Message, Cutscene, SetRate).

Verifies Group E opcodes against live Mindustry v160.7 JVM engine.
Covers:
1. Privileged processor permission enforcement (standard processor rejects message/cutscene vs world processor permits them; setrate permitted on all).
2. 'message' opcode: announce, notify, toast, mission text buffer flushing, duration, and outSuccess retry/blocking logic.
3. 'cutscene' opcode: camera pan coordinates (world unconv), zoom clamping, screen shake intensity/time, HUD visibility toggle and query, active state.
4. 'setrate' opcode: scaling IPT up to 1000 on World Processor.
5. Python DSL compilation, namespace methods, and decompiler roundtrip.
"""

import unittest
from src.compiler import Compiler
from src.decompiler import decompile
from src.mindustry_validator import is_mindustry_available, run_with_mindustry, validate_with_mindustry
from src.mlog import compile_py
from src.mlog_registry import (
    CutsceneAction,
    MessageType,
    REG_CUTSCENE_ACTIONS,
    REG_MESSAGE_TYPES,
)


@unittest.skipUnless(is_mindustry_available(), "Mindustry validation harness unavailable")
class TestTier4MessagingAndCutscene(unittest.TestCase):
    """Test suite for Tier 4 Group E: message, cutscene, setrate."""

    def test_privileged_processor_enforcement(self):
        """Verify standard processor rejects message/cutscene while permitting setrate."""
        # 1. Standard processor rejects message
        mlog_std_msg = "message announce 3 @wait\n"
        res_std_msg = run_with_mindustry(mlog_std_msg)
        self.assertFalse(res_std_msg.success)
        self.assertIn("InvalidStatement", res_std_msg.message)

        # 2. Standard processor rejects cutscene
        mlog_std_cut = "cutscene pan 100 100 0.06 0\n"
        res_std_cut = run_with_mindustry(mlog_std_cut)
        self.assertFalse(res_std_cut.success)
        self.assertIn("InvalidStatement", res_std_cut.message)

        # 3. Standard processor permits setrate (standard opcode)
        mlog_std_rate = "setrate 6\n"
        res_std_rate = run_with_mindustry(mlog_std_rate)
        self.assertTrue(res_std_rate.success)
        self.assertEqual(res_std_rate.ipt, 6)

        # 4. World processor permits message, cutscene, and high setrate
        mlog_world = """#processor: world
print "System Online"
message announce 4 @wait
cutscene pan 50 60 0.05 0
setrate 500
"""
        res_world = run_with_mindustry(mlog_world)
        self.assertTrue(res_world.success, f"World processor execution failed: {res_world.message}")
        self.assertEqual(res_world.ipt, 500)
        self.assertEqual(res_world.announce_text, "System Online")
        self.assertEqual(res_world.text_buffer, "")

    def test_message_announce_semantics(self):
        """Verify message announce flushes textBuffer and delivers announcement."""
        mlog = """#processor: world
print "Core under attack!"
message announce 5.5 @wait
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Message announce failed: {res.message}")
        self.assertEqual(res.announce_text, "Core under attack!")
        self.assertEqual(res.text_buffer, "")

    def test_message_toast_and_notify_semantics(self):
        """Verify message toast and notify deliver formatted messages and flush buffer."""
        # Toast
        mlog_toast = """#processor: world
print "Research Completed"
message toast 3.2 @wait
"""
        res_toast = run_with_mindustry(mlog_toast)
        self.assertTrue(res_toast.success, f"Toast message failed: {res_toast.message}")
        self.assertEqual(res_toast.toast_text, "Research Completed")
        self.assertEqual(res_toast.text_buffer, "")

        # Notify
        mlog_notify = """#processor: world
print "Sector Secured"
message notify 2.0 @wait
"""
        res_notify = run_with_mindustry(mlog_notify)
        self.assertTrue(res_notify.success, f"Notify message failed: {res_notify.message}")
        self.assertEqual(res_notify.notify_text, "Sector Secured")
        self.assertEqual(res_notify.text_buffer, "")

    def test_message_mission_semantics(self):
        """Verify message mission sets state.rules.mission and flushes buffer."""
        mlog = """#processor: world
print "Objective: Destroy Enemy Reactor"
message mission 0 @wait
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Mission message failed: {res.message}")
        self.assertEqual(res.mission_text, "Objective: Destroy Enemy Reactor")
        self.assertEqual(res.text_buffer, "")

    def test_message_out_success_and_retry(self):
        """Verify outSuccess variable receives success (1) or busy failure (0)."""
        # Happy path without busy UI
        mlog_ok = """#processor: world
print "Ping"
message announce 3 out_stat
"""
        res_ok = run_with_mindustry(mlog_ok)
        self.assertTrue(res_ok.success)
        self.assertEqual(res_ok.vars.get("out_stat"), 1.0)

        # Busy UI returns 0 without crashing
        mlog_busy = """#processor: world
#announce_busy
print "Ping"
message announce 3 out_stat
"""
        res_busy = run_with_mindustry(mlog_busy)
        self.assertTrue(res_busy.success)
        self.assertEqual(res_busy.vars.get("out_stat"), 0.0)

    def test_cutscene_pan_semantics(self):
        """Verify cutscene pan updates camera coordinates (unconv 8x) and speed."""
        mlog = """#processor: world
cutscene pan 20 40 0.08 0
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Cutscene pan failed: {res.message}")
        self.assertTrue(res.cutscene_active)
        self.assertEqual(res.cutscene_speed, 0.08)
        self.assertIsNotNone(res.cutscene_pan)
        # World.unconv multiplies tile coordinates by tilesize (8)
        self.assertEqual(res.cutscene_pan, (160.0, 320.0))

    def test_cutscene_zoom_and_stop(self):
        """Verify cutscene zoom clamps level and stop terminates cutscene mode."""
        mlog = """#processor: world
cutscene zoom 0.65 0 0 0
cutscene stop 0 0 0 0
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Cutscene zoom and stop failed: {res.message}")
        self.assertFalse(res.cutscene_active)
        self.assertEqual(res.cutscene_zoom, 0.65)

    def test_cutscene_shake_semantics(self):
        """Verify cutscene shake updates renderer shake intensity."""
        mlog = """#processor: world
cutscene shake 12.5 1.5 0 0
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Cutscene shake failed: {res.message}")
        self.assertEqual(res.shake_intensity, 12.5)

    def test_cutscene_hud_and_active_queries(self):
        """Verify cutscene getHud, setHud, and active state reflection."""
        mlog = """#processor: world
cutscene pan 10 10 0.1 0
cutscene active is_act 0 0 0
cutscene setHud 0 0 0 0
cutscene getHud hud_shown 0 0 0
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Cutscene queries failed: {res.message}")
        self.assertTrue(res.cutscene_hide_hud)
        self.assertEqual(res.vars.get("is_act"), 1.0)
        self.assertEqual(res.vars.get("hud_shown"), 0.0)

    def test_setrate_world_processor_scaling(self):
        """Verify setrate scales up to 1000 instructions per tick on World Processor."""
        mlog = """#processor: world
setrate 950
set cur_ipt @ipt
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"SetRate world processor scaling failed: {res.message}")
        self.assertEqual(res.ipt, 950)
        self.assertEqual(res.vars.get("cur_ipt"), 950.0)

    def test_dsl_compilation_and_execution(self):
        """Verify Python DSL compiles to clean mlog and executes on JVM."""
        py_src = """#processor: world
from mlog import print, message, cutscene, setrate, MessageType, CutsceneAction

print("Mission Start")
message(MessageType.ANNOUNCE, 4)
cutscene.pan(30, 50, 0.07)
cutscene.zoom(0.8)
cutscene.shake(8, 2)
is_active = cutscene.active()
cutscene.set_hud(False)
hud_visible = cutscene.get_hud()
setrate(450)
"""
        compile_res = compile_py(py_src)
        mlog_lines = [l.strip() for l in compile_res.mlog.strip().splitlines() if l.strip()]

        self.assertIn("message announce 4 @wait", compile_res.mlog)
        self.assertIn("cutscene pan 30 50 0.07 0", compile_res.mlog)
        self.assertIn("cutscene zoom 0.8 0 0 0", compile_res.mlog)
        self.assertIn("cutscene shake 8 2 0 0", compile_res.mlog)
        self.assertIn("cutscene active is_active 0 0 0", compile_res.mlog)
        self.assertIn("cutscene setHud 0 0 0 0", compile_res.mlog)
        self.assertIn("cutscene getHud hud_visible 0 0 0", compile_res.mlog)
        self.assertIn("setrate 450", compile_res.mlog)

        # Execute on Mindustry engine
        res = run_with_mindustry("#processor: world\n" + compile_res.mlog)
        self.assertTrue(res.success, f"Compiled DSL failed on JVM: {res.message}")
        self.assertEqual(res.announce_text, "Mission Start")
        self.assertEqual(res.cutscene_pan, (240.0, 400.0))
        self.assertEqual(res.cutscene_zoom, 0.8)
        self.assertEqual(res.shake_intensity, 8.0)
        self.assertEqual(res.vars.get("is_active"), 1.0)
        self.assertEqual(res.vars.get("hud_visible"), 0.0)
        self.assertEqual(res.ipt, 450)

    def test_decompiler_roundtrip(self):
        """Verify mlog -> Python -> mlog roundtrip for Group E statements."""
        mlog_orig = """#processor: world
print "Sector Discovered"
message toast 4.5 @wait
cutscene pan 15 25 0.06 0
cutscene zoom 1.2 0 0 0
cutscene shake 5 1 0 0
cutscene stop 0 0 0 0
setrate 200
"""
        decomp_py = decompile(mlog_orig)
        compile_again = compile_py(decomp_py)

        self.assertIn("message toast 4.5 @wait", compile_again.mlog)
        self.assertIn("cutscene pan 15 25 0.06 0", compile_again.mlog)
        self.assertIn("cutscene zoom 1.2 0 0 0", compile_again.mlog)
        self.assertIn("cutscene shake 5 1 0 0", compile_again.mlog)
        self.assertIn("cutscene stop 0 0 0 0", compile_again.mlog)
        self.assertIn("setrate 200", compile_again.mlog)

        # Run recompiled mlog on JVM
        res = run_with_mindustry("#processor: world\n" + compile_again.mlog)
        self.assertTrue(res.success, f"Recompiled roundtrip failed on JVM: {res.message}")
        self.assertEqual(res.toast_text, "Sector Discovered")
        self.assertEqual(res.ipt, 200)

    def test_invalid_arguments_validation(self):
        """Verify invalid message types, cutscene actions, and argument counts raise errors."""
        c = Compiler()

        # Unknown message type
        with self.assertRaises(Exception):
            c.compile("from mlog import message\nmessage('invalid_type', 3)\n")

        # Unknown cutscene action
        with self.assertRaises(Exception):
            c.compile("from mlog import cutscene\ncutscene('nonexistent_action')\n")

        # cutscene.pan missing required coordinates
        with self.assertRaises(Exception):
            c.compile("from mlog import cutscene\ncutscene.pan(10)\n")

        # cutscene.shake missing duration
        with self.assertRaises(Exception):
            c.compile("from mlog import cutscene\ncutscene.shake(5)\n")


if __name__ == "__main__":
    unittest.main()
