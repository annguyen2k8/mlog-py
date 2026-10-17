"""Tier 4 Regression Suite: World Processor & Map Scripting - Group D (Weather, Wave & World Effects).

Verifies Group D opcodes (weathersense, weatherset, spawnwave, effect) against live Mindustry v160.7 JVM engine.
Covers:
1. Privileged processor permission enforcement (standard processor rejects vs world processor executes).
2. Weather control and sensing via weatherset and weathersense (activation, deactivation, invalid weather targets).
3. Enemy wave progression and coordinate spawning via spawnwave (natural wave vs coordinate spawns).
4. World particle and explosion effects via effect (known effects, invalid effect types, coordinate boundaries).
5. End-to-end Python DSL compilation, execution on real engine, and decompiler roundtrip.
"""

import unittest
from src.decompiler import decompile
from src.mindustry_validator import is_mindustry_available, run_with_mindustry
from src.mlog import compile_py
from src.mlog_registry import (
    FetchType,
    Fx,
    Teams,
    Units,
    Weathers,
)


@unittest.skipUnless(is_mindustry_available(), "Mindustry validation harness unavailable")
class TestTier4WeatherAndEffects(unittest.TestCase):
    """Test suite for Tier 4 Group D: Weather, Wave & World Effects."""

    def test_privileged_processor_enforcement(self):
        """Verify that standard processors reject Group D opcodes while World Processors permit them."""
        # 1. Standard processor rejects 'weathersense'
        res_std = run_with_mindustry("weathersense res @rain\n")
        self.assertFalse(res_std.success)
        self.assertIn("InvalidStatement", res_std.message)

        # 2. Standard processor rejects 'weatherset'
        res_std = run_with_mindustry("weatherset @rain 1\n")
        self.assertFalse(res_std.success)
        self.assertIn("InvalidStatement", res_std.message)

        # 3. Standard processor rejects 'spawnwave'
        res_std = run_with_mindustry("spawnwave 50 50 0\n")
        self.assertFalse(res_std.success)
        self.assertIn("InvalidStatement", res_std.message)

        # 4. Standard processor rejects 'effect'
        res_std = run_with_mindustry("effect warn 50 50 2 0 0\n")
        self.assertFalse(res_std.success)
        self.assertIn("InvalidStatement", res_std.message)

        # 5. World Processor permits all of them
        res_world = run_with_mindustry(
            "#processor: world\n"
            "weathersense res @rain\n"
            "weatherset @rain 1\n"
            "spawnwave 0 0 1\n"
            "effect warn 50 50 2 0 0\n"
        )
        self.assertTrue(res_world.success, f"World processor rejected Group D opcodes: {res_world.message}")

    def test_weather_control_and_sensing(self):
        """Verify weatherset activating/deactivating weather events and weathersense reading state."""
        mlog = """#processor: world
# 1. Sense initial state of rain and snow (should be 0)
weathersense rain_before @rain
weathersense snow_before @snowing

# 2. Activate rain
weatherset @rain 1
weathersense rain_active @rain
weathersense snow_still_inactive @snowing

# 3. Deactivate rain
weatherset @rain 0

# 4. Activate sandstorm
weatherset @sandstorm 1
weathersense sand_active @sandstorm

# 5. Boundary case: query invalid weather target
weathersense invalid_target 999
weathersense null_target null

# 6. Boundary case: set invalid weather target (safe no-op)
weatherset null 1
weatherset 12345 1
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Weather execution failed: {res.message}")
        self.assertEqual(res.vars.get("rain_before"), 0.0)
        self.assertEqual(res.vars.get("snow_before"), 0.0)
        self.assertEqual(res.vars.get("rain_active"), 1.0)
        self.assertEqual(res.vars.get("snow_still_inactive"), 0.0)
        self.assertEqual(res.vars.get("sand_active"), 1.0)
        self.assertEqual(res.vars.get("invalid_target"), 0.0)
        self.assertEqual(res.vars.get("null_target"), 0.0)

    def test_spawnwave_natural_and_coordinates(self):
        """Verify spawnwave natural progression and coordinate-based enemy spawning."""
        mlog = """#processor: world
# 1. Record initial wave number
set initial_wave @waveNumber

# 2. Trigger natural wave progression (natural = 1)
spawnwave 0 0 1
set wave_after_natural @waveNumber

# 3. Trigger second natural wave progression
spawnwave 0 0 1
set wave_second_natural @waveNumber

# 4. Trigger coordinate-based enemy spawn (natural = 0) at (50, 50)
spawnwave 50 50 0
fetch unitCount crux_flares @crux 0 @flare
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"spawnwave execution failed: {res.message}")
        init_w = res.vars.get("initial_wave", 1.0)
        self.assertEqual(res.vars.get("wave_after_natural"), init_w + 1.0)
        self.assertEqual(res.vars.get("wave_second_natural"), init_w + 2.0)
        self.assertGreaterEqual(res.vars.get("crux_flares", 0.0), 1.0)

    def test_world_effect_execution_and_boundaries(self):
        """Verify effect instruction executes cleanly for valid and boundary effect types."""
        mlog = """#processor: world
# 1. Standard valid effects
effect warn 50 50 2 0 0
effect cross 50 50 2 0 0
effect spawn 50 50 0 0 0
effect explosion 50 50 5 0 0
effect smokeSmall 50 50 45 0 0
effect wave 50 50 10 16755455 0
effect bubble 50 50 1 0 0

# 2. Boundary: Unknown effect type (Mindustry LogicFx.get returns null, handled safely)
effect nonexistentEffect 50 50 0 0 0
effect 12345 50 50 0 0 0

# 3. Boundary: Out of bounds / negative world coordinates
effect warn -500 -500 0 0 0
effect explosion 99999 99999 100 0 0

set execution_done 1
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"effect execution failed: {res.message}")
        self.assertEqual(res.vars.get("execution_done"), 1.0)

    def test_group_d_dsl_and_decompiler_roundtrip(self):
        """Verify Group D opcodes compile from Python DSL, execute on JVM engine, and roundtrip cleanly."""
        dsl_code = """from mlog import effect, fetch, spawnwave, weathersense, weatherset, FetchType, Fx, Teams, Units, Weathers

# 1. Weather control and sensing
weatherset(Weathers.RAIN, 1)
weathersense(is_raining, Weathers.RAIN)

# 2. Wave manipulation
spawnwave(0, 0, 1)
spawnwave(50, 50, 0)
fetch(FetchType.UNIT_COUNT, total_crux_flares, Teams.CRUX, 0, Units.FLARE)

# 3. World particle effects
effect(Fx.WARN, 50, 50, 2, 0, 0)
effect(Fx.EXPLOSION, 50, 50, 4, 0, 0)
"""
        compile_res = compile_py(dsl_code)
        self.assertIn("weatherset @rain 1", compile_res.mlog)
        self.assertIn("weathersense is_raining @rain", compile_res.mlog)
        self.assertIn("spawnwave 0 0 1", compile_res.mlog)
        self.assertIn("spawnwave 50 50 0", compile_res.mlog)
        self.assertIn("fetch unitCount total_crux_flares @crux 0 @flare", compile_res.mlog)
        self.assertIn("effect warn 50 50 2 0 0", compile_res.mlog)
        self.assertIn("effect explosion 50 50 4 0 0", compile_res.mlog)

        # Decompile the compiled mlog
        decompiled_py = decompile(compile_res.mlog)
        self.assertIn("from mlog import effect, fetch, spawnwave, weathersense, weatherset", decompiled_py)
        self.assertIn("weatherset(\"@rain\", 1)", decompiled_py)
        self.assertIn("weathersense(is_raining, \"@rain\")", decompiled_py)
        self.assertIn("spawnwave(0, 0, 1)", decompiled_py)
        self.assertIn("spawnwave(50, 50, 0)", decompiled_py)
        self.assertIn("effect(\"warn\", 50, 50, 2, 0, 0)", decompiled_py)
        self.assertIn("effect(\"explosion\", 50, 50, 4, 0, 0)", decompiled_py)

        # End-to-end execute decompiled code after re-compilation
        recompiled = compile_py(decompiled_py)
        mlog_with_header = "#processor: world\n" + recompiled.mlog
        exec_res = run_with_mindustry(mlog_with_header)
        self.assertTrue(exec_res.success, f"recompiled mlog execution failed: {exec_res.message}")
        self.assertEqual(exec_res.vars.get("is_raining"), 1.0)
        self.assertGreaterEqual(exec_res.vars.get("total_crux_flares", 0.0), 1.0)


if __name__ == "__main__":
    unittest.main()
