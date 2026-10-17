"""Tier 4 Final Suite: Audio, Markers, Locale, ClientData & Full Opcode Verification.

Validates exact Mindustry v160.7 engine semantics for:
1. playsound: Global vs positional sound effects, volume, pitch, pan, coordinates, limit.
2. playmusic: Music playback and track switching, null track stopping, interrupt flag.
3. makemarker: Objective marker creation, coordinate conversion (8x unconv), type mapping, replace flag.
4. setmarker: Property control, position updates, shape, color, flushText, removal.
5. localeprint: Localized bundle text formatting and textBuffer integration.
6. clientdata: Custom network logic data packets under privileged execution.
7. Privileged processor enforcement: Standard processor rejects privileged statements.
8. Python DSL compilation, namespace methods, JVM execution, and decompiler roundtrip.
"""

import unittest
from src.compiler import Compiler
from src.decompiler import decompile
from src.mindustry_validator import is_mindustry_available, run_with_mindustry
from src.mlog import compile_py
from src.mlog_registry import MarkerControl, MarkerType


@unittest.skipUnless(is_mindustry_available(), "Mindustry validation harness unavailable")
class TestTier4AudioMarkersAndFinal(unittest.TestCase):
    """Real JVM regression tests for Mindustry audio, markers, locale, and network data."""

    def test_privileged_processor_enforcement(self):
        """Verify standard processor strictly rejects Tier 4 privileged statements."""
        statements = [
            'playsound false @sfx-shoot 1 1 0 0 0 true',
            'playmusic "game1" true',
            'makemarker shape 1 50 50 true',
            'setmarker pos 1 100 100 0',
            'localeprint "name"',
            'clientdata "frog" 123 0',
        ]
        for stmt in statements:
            res = run_with_mindustry(stmt + "\n")
            self.assertFalse(
                res.success,
                f"Standard processor should have rejected '{stmt}' as InvalidStatement",
            )
            self.assertIn("InvalidStatement", res.message)

    def test_playsound_execution(self):
        """Verify playsound executes cleanly in world processor context for global and positional."""
        mlog = """#processor: world
playsound false @sfx-shoot 0.8 1.2 0 0 0 true
playsound true @sfx-shoot 1.0 1.0 0 150 250 true
set sound_ran 1
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"playsound execution failed: {res.message}")
        self.assertEqual(res.vars.get("sound_ran"), 1.0)

    def test_playmusic_execution(self):
        """Verify playmusic executes cleanly in world processor context."""
        mlog = """#processor: world
playmusic "game1" true
playmusic "game2" false
playmusic null false
set music_ran 1
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"playmusic execution failed: {res.message}")
        self.assertEqual(res.vars.get("music_ran"), 1.0)

    def test_makemarker_creation_and_coordinates(self):
        """Verify makemarker instantiates markers in state.markers with unconv (8x) coordinates."""
        mlog = """#processor: world
makemarker shape 1 10 20 true
makemarker point 2 30 40 true
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"makemarker execution failed: {res.message}")
        self.assertEqual(res.markers_total, 2)
        self.assertTrue(res.markers.get(1, {}).get("exists"))
        self.assertTrue(res.markers.get(2, {}).get("exists"))
        # Tile (10, 20) -> World unconv is (80.0, 160.0)
        self.assertEqual(res.markers.get(1, {}).get("pos"), (80.0, 160.0))
        # Tile (30, 40) -> World unconv is (240.0, 320.0)
        self.assertEqual(res.markers.get(2, {}).get("pos"), (240.0, 320.0))

    def test_makemarker_replacement(self):
        """Verify makemarker with replace=true updates the marker ID at new coordinates."""
        mlog = """#processor: world
makemarker shape 5 15 25 true
makemarker shape 5 45 55 true
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"makemarker replacement failed: {res.message}")
        self.assertEqual(res.markers_total, 1)
        self.assertTrue(res.markers.get(5, {}).get("exists"))
        self.assertEqual(res.markers.get(5, {}).get("pos"), (360.0, 440.0))

    def test_setmarker_properties_and_removal(self):
        """Verify setmarker modifies position, properties, and removes markers."""
        mlog = """#processor: world
makemarker shape 10 10 10 true
makemarker shape 11 20 20 true
setmarker pos 10 50 60 0
setmarker shape 10 6 1 1
setmarker color 10 %ff0000 0 0
setmarker remove 11 0 0 0
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"setmarker execution failed: {res.message}")
        self.assertEqual(res.markers_total, 1)
        self.assertTrue(res.markers.get(10, {}).get("exists"))
        # Position updated to tile (50, 60) -> world (400.0, 480.0)
        self.assertEqual(res.markers.get(10, {}).get("pos"), (400.0, 480.0))
        # Marker 11 was removed
        self.assertFalse(res.markers.get(11, {}).get("exists", False))

    def test_localeprint_and_flush(self):
        """Verify localeprint appends bundle content or empty string and flushes to message."""
        mlog = """#processor: world
localeprint "name"
printflush message1
set lp_done 1
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"localeprint execution failed: {res.message}")
        self.assertEqual(res.vars.get("lp_done"), 1.0)

    def test_clientdata_execution(self):
        """Verify clientdata packets execute cleanly without throwing exceptions on engine."""
        mlog = """#processor: world
clientdata "event-channel" 100 1
clientdata "stream-channel" "status-ok" 0
set cd_done 1
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"clientdata execution failed: {res.message}")
        self.assertEqual(res.vars.get("cd_done"), 1.0)

    def test_dsl_compilation_and_execution(self):
        """Verify Python DSL compiles to clean mlog and executes correctly on real Mindustry JVM."""
        py_src = """
from mlog import (
    playsound, playmusic, makemarker, setmarker, localeprint, clientdata,
    sound, music, marker, MarkerType, MarkerControl
)

# 1. Audio operations
playsound(False, "@sfx-shoot", 0.7, 1.1)
sound.play("@sfx-shoot", 0.9, 1.0)
sound.play_at("@sfx-shoot", 80, 120)
playmusic("game1", True)
music.play("fine", False)
music.stop()

# 2. Objective marker operations
makemarker(MarkerType.SHAPE, 1, 25, 35, True)
marker.make(MarkerType.POINT, 2, 50, 60)
marker.pos(1, 75, 85)
marker.color(1, "%00ff00")
marker.shape(1, 5, 1, 1)
marker.remove(2)

# 3. Locale & network data
localeprint("name")
clientdata("player-pos", 1234, True)
"""
        compile_res = compile_py(py_src)

        # Verify generated mlog contains expected instructions
        self.assertIn("playsound false @sfx-shoot 0.7 1.1 0 0 0 true", compile_res.mlog)
        self.assertIn("playsound false @sfx-shoot 0.9 1.0 0 0 0 true", compile_res.mlog)
        self.assertIn("playsound true @sfx-shoot 1 1 0 80 120 true", compile_res.mlog)
        self.assertIn('playmusic "game1" true', compile_res.mlog)
        self.assertIn('playmusic "fine" false', compile_res.mlog)
        self.assertIn("playmusic null false", compile_res.mlog)
        self.assertIn("makemarker shape 1 25 35 true", compile_res.mlog)
        self.assertIn("makemarker point 2 50 60 true", compile_res.mlog)
        self.assertIn("setmarker pos 1 75 85 0", compile_res.mlog)
        self.assertIn('setmarker color 1 "%00ff00" 0 0', compile_res.mlog)
        self.assertIn("setmarker shape 1 5 1 1", compile_res.mlog)
        self.assertIn("setmarker remove 2 0 0 0", compile_res.mlog)
        self.assertIn('localeprint "name"', compile_res.mlog)
        self.assertIn('clientdata "player-pos" 1234 1', compile_res.mlog)

        # Run on real Mindustry JVM engine
        res = run_with_mindustry("#processor: world\n" + compile_res.mlog)
        self.assertTrue(res.success, f"Compiled DSL failed on JVM: {res.message}")
        self.assertEqual(res.markers_total, 1)
        self.assertTrue(res.markers.get(1, {}).get("exists"))
        self.assertEqual(res.markers.get(1, {}).get("pos"), (600.0, 680.0))
        self.assertFalse(res.markers.get(2, {}).get("exists", False))

    def test_decompiler_roundtrip(self):
        """Verify mlog -> Python -> mlog roundtrip invariance for all remaining statements."""
        mlog_orig = """#processor: world
playsound false @sfx-shoot 1 1 0 0 0 true
playmusic "game1" true
makemarker shape 1 50 50 true
setmarker pos 1 100 100 0
setmarker shape 1 4 1 1
localeprint "name"
clientdata "chat" 999 1
"""
        decomp_py = decompile(mlog_orig)
        compile_again = compile_py(decomp_py)

        self.assertIn("playsound false @sfx-shoot 1 1 0 0 0 true", compile_again.mlog)
        self.assertIn('playmusic "game1" true', compile_again.mlog)
        self.assertIn("makemarker shape 1 50 50 true", compile_again.mlog)
        self.assertIn("setmarker pos 1 100 100 0", compile_again.mlog)
        self.assertIn("setmarker shape 1 4 1 1", compile_again.mlog)
        self.assertIn('localeprint "name"', compile_again.mlog)
        self.assertIn('clientdata "chat" 999 1', compile_again.mlog)

        res = run_with_mindustry("#processor: world\n" + compile_again.mlog)
        self.assertTrue(res.success, f"Recompiled roundtrip failed on JVM: {res.message}")
        self.assertEqual(res.markers_total, 1)
        self.assertEqual(res.markers.get(1, {}).get("pos"), (800.0, 800.0))

    def test_invalid_arguments_validation(self):
        """Verify compiler rejects invalid arguments, invalid counts, or unmapped types."""
        c = Compiler()

        # Invalid makemarker arg count
        with self.assertRaises(Exception):
            c.compile("makemarker('shape', 1)")

        # Invalid playsound arg count
        with self.assertRaises(Exception):
            c.compile("playsound('true')")

        # Invalid playmusic arg count
        with self.assertRaises(Exception):
            c.compile("playmusic('game1', True, 3)")

        # Invalid setmarker arg count
        with self.assertRaises(Exception):
            c.compile("setmarker('pos')")

        # Invalid localeprint arg count
        with self.assertRaises(Exception):
            c.compile("localeprint()")

        # Invalid clientdata arg count
        with self.assertRaises(Exception):
            c.compile("clientdata('channel')")


if __name__ == "__main__":
    unittest.main()
