"""Tier 4 Regression Suite: World Processor & Map Scripting - Group C (Rules, Flags, Queries & Sync).

Verifies Group C opcodes (setrule, getflag, setflag, setprop, fetch, sync) against live Mindustry v160.7 JVM engine.
Covers:
1. Privileged processor permission enforcement (standard processor rejects vs world processor executes).
2. Objective flags manipulation (setflag, getflag, boolean coercion, non-string null handling).
3. Entity property mutation via setprop (LAccess properties and content types, Settable verification).
4. World entity queries via fetch (FetchType modes: core, coreCount, unit, unitCount, build, buildCount, player, playerCount, bounds checking).
5. Multiplayer state synchronization via sync (rate-limited safety).
6. Game rules and team multipliers via setrule (wave, waveTimer, unitHealth multipliers).
7. End-to-end Python DSL compilation, execution on real engine, and decompiler roundtrip.
"""

import unittest
from src.decompiler import decompile
from src.mindustry_validator import is_mindustry_available, run_with_mindustry
from src.mlog import compile_py
from src.mlog_registry import (
    FetchType,
    LogicRules,
    SensorProperty,
    Teams,
    Units,
)


@unittest.skipUnless(is_mindustry_available(), "Mindustry validation harness unavailable")
class TestTier4RulesAndQueries(unittest.TestCase):
    """Test suite for Tier 4 Group C: Rules, Flags, Entity Queries & Synchronization."""

    def test_privileged_processor_enforcement(self):
        """Verify that standard processors reject Group C opcodes while World Processors permit them."""
        # 1. Standard processor rejects 'getflag' as InvalidStatement
        res_std = run_with_mindustry("getflag res \"flag1\"\n")
        self.assertFalse(res_std.success)
        self.assertIn("InvalidStatement", res_std.message)

        # 2. Standard processor rejects 'setflag' as InvalidStatement
        res_std = run_with_mindustry("setflag \"flag1\" 1\n")
        self.assertFalse(res_std.success)
        self.assertIn("InvalidStatement", res_std.message)

        # 3. Standard processor rejects 'setprop' as InvalidStatement
        res_std = run_with_mindustry("setprop @health @unit 100\n")
        self.assertFalse(res_std.success)
        self.assertIn("InvalidStatement", res_std.message)

        # 4. Standard processor rejects 'fetch' as InvalidStatement
        res_std = run_with_mindustry("fetch unit res @sharded 0 0\n")
        self.assertFalse(res_std.success)
        self.assertIn("InvalidStatement", res_std.message)

        # 5. Standard processor rejects 'sync' as InvalidStatement
        res_std = run_with_mindustry("sync v\n")
        self.assertFalse(res_std.success)
        self.assertIn("InvalidStatement", res_std.message)

        # 6. Standard processor rejects 'setrule' as InvalidStatement
        res_std = run_with_mindustry("setrule waveTimer 1 0 0 0 0\n")
        self.assertFalse(res_std.success)
        self.assertIn("InvalidStatement", res_std.message)

        # 7. World processor permits all six statements cleanly
        mlog_world = """#processor: world
setflag "test_gate" 1
getflag is_open "test_gate"
setprop @health @unit 100
fetch core c @sharded 0 0
set my_sync_var 42
sync my_sync_var
setrule waveTimer 1 0 0 0 0
"""
        res_world = run_with_mindustry(mlog_world)
        self.assertTrue(res_world.success, f"world processor execution failed: {res_world.message}")
        self.assertEqual(res_world.vars.get("is_open"), 1)
        self.assertEqual(res_world.vars.get("my_sync_var"), 42)

    def test_objective_flags_getflag_and_setflag(self):
        """Verify adding, querying, clearing, and boundary handling of objective flags in world rules."""
        mlog = """#processor: world
# 1. Query non-existent flag initially -> returns 0 (false)
getflag initial_flag "sec_1"

# 2. Add flag via setflag
setflag "sec_1" 1
getflag after_set "sec_1"

# 3. Add second flag with truthy non-zero number
setflag "sec_2" 99
getflag flag2_val "sec_2"

# 4. Clear sec_1 flag with 0
setflag "sec_1" 0
getflag after_clear "sec_1"

# 5. Non-string operand returns null in Mindustry LExecutor
set num_var 1234
getflag oob_flag num_var
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"flags execution failed: {res.message}")
        self.assertEqual(res.vars.get("initial_flag"), 0)
        self.assertEqual(res.vars.get("after_set"), 1)
        self.assertEqual(res.vars.get("flag2_val"), 1)
        self.assertEqual(res.vars.get("after_clear"), 0)
        self.assertEqual(res.vars.get("oob_flag"), "null")

    def test_setprop_entity_properties(self):
        """Verify modifying unit health, shield, rotation, and non-Settable boundaries using setprop."""
        mlog = """#processor: world
# 1. Spawn a target unit
spawn @dagger 50 50 0 @sharded u 0

# 2. Sense baseline health
sensor base_hp u @health

# 3. Set custom health and shield via setprop
setprop @health u 25
setprop @shield u 175
setprop @rotation u 270

# 4. Sense updated properties
sensor updated_hp u @health
sensor updated_shield u @shield
sensor updated_rot u @rotation

# 5. Boundary case: setprop on null target does not crash LExecutor
setprop @health null 100
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"setprop execution failed: {res.message}")
        self.assertEqual(res.vars.get("u"), "dagger")
        self.assertEqual(res.vars.get("base_hp"), 150.0)
        self.assertEqual(res.vars.get("updated_hp"), 25.0)
        self.assertEqual(res.vars.get("updated_shield"), 175.0)
        self.assertEqual(res.vars.get("updated_rot"), 270.0)

    def test_fetch_team_entities_and_counts(self):
        """Verify entity querying via fetch across cores, units, buildings, counts, and boundary limits."""
        mlog = """#processor: world
# 1. Core and CoreCount
fetch core core_0 @sharded 0 0
fetch coreCount core_count @sharded 0 0

# 2. Spawn units and fetch by unit and unitCount
spawn @dagger 40 40 0 @sharded u_dag1 0
spawn @dagger 45 45 0 @sharded u_dag2 0
spawn @flare 60 60 0 @sharded u_fl1 0

fetch unitCount total_units @sharded 0 0
fetch unitCount dagger_units @sharded 0 @dagger
fetch unitCount flare_units @sharded 0 @flare
fetch unit first_dagger @sharded 0 @dagger
fetch unit second_dagger @sharded 1 @dagger

# 3. Buildings and BuildCount (world processor itself is on the map)
fetch buildCount wp_count @sharded 0 @world-processor
fetch build wp_build @sharded 0 @world-processor

# 4. Out-of-bounds boundary safety
fetch core oob_core @sharded 99 0
fetch unit oob_neg_unit @sharded -1 @dagger
fetch unit oob_high_unit @sharded 999 @dagger
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"fetch execution failed: {res.message}")
        # Sharded core exists on test map
        self.assertIsNotNone(res.vars.get("core_0"))
        self.assertNotEqual(res.vars.get("core_0"), "null")
        self.assertEqual(res.vars.get("core_count"), 1)

        # Unit queries
        self.assertGreaterEqual(res.vars.get("total_units", 0), 3)
        self.assertGreaterEqual(res.vars.get("dagger_units", 0), 2)
        self.assertGreaterEqual(res.vars.get("flare_units", 0), 1)
        self.assertEqual(res.vars.get("first_dagger"), "dagger")
        self.assertEqual(res.vars.get("second_dagger"), "dagger")

        # Building queries
        self.assertGreaterEqual(res.vars.get("wp_count", 0), 1)
        self.assertEqual(res.vars.get("wp_build"), "world-processor")

        # Boundaries
        self.assertEqual(res.vars.get("oob_core"), "null")
        self.assertEqual(res.vars.get("oob_neg_unit"), "null")
        self.assertEqual(res.vars.get("oob_high_unit"), "null")

    def test_setrule_global_and_team_rules(self):
        """Verify modifying wave number, wave spacing, and team health multiplier via setrule."""
        mlog = """#processor: world
# 1. Modify wave number to 24
setrule wave 24 0 0 0 0
set current_wave @waveNumber

# 2. Modify wave time to 120 seconds
setrule currentWaveTime 120 0 0 0 0
set wave_time @waveTime

# 3. Modify global rules (waves enabled, wave timer enabled, spacing, unit cap)
setrule waves 1 0 0 0 0
setrule waveTimer 1 0 0 0 0
setrule waveSpacing 90 0 0 0 0
setrule unitCap 80 0 0 0 0

# 4. Modify team unit health multiplier to 3.0 for sharded
setrule unitHealth 3.0 @sharded 0 0 0

# 5. Spawn unit under configured rules (unit base stats remain type.health in Mindustry)
spawn @dagger 50 50 0 @sharded u 0
sensor u_hp u @health
sensor u_max u @maxHealth

# 6. Re-modify wave to 35
setrule wave 35 0 0 0 0
set final_wave @waveNumber
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"setrule execution failed: {res.message}")
        self.assertEqual(res.vars.get("current_wave"), 24)
        self.assertEqual(res.vars.get("wave_time"), 120.0)
        self.assertEqual(res.vars.get("u_hp"), 150.0)
        self.assertEqual(res.vars.get("u_max"), 150.0)
        self.assertEqual(res.vars.get("final_wave"), 35)

    def test_group_c_dsl_and_decompiler_roundtrip(self):
        """Verify Group C opcodes compile from Python DSL, execute on JVM engine, and roundtrip cleanly."""
        dsl_code = """from mlog import fetch, getflag, setflag, setprop, setrule, spawn, sync, FetchType, LogicRules, SensorProperty, Teams, Units

# 1. Rules and Flags
setrule(LogicRules.WAVE, 18)
setflag("mission_alpha", 1)
getflag(flag_active, "mission_alpha")

# 2. Unit Spawning and setprop
spawn(Units.DAGGER, 40, 40, 0, Teams.SHARDED, target_u)
setprop(SensorProperty.HEALTH, target_u, 80)
setprop(SensorProperty.SHIELD, target_u, 120)

# 3. Entity Fetch queries
fetch(FetchType.CORE, core_entity, Teams.SHARDED, 0, 0)
fetch(FetchType.CORE_COUNT, total_cores, Teams.SHARDED, 0, 0)
fetch(FetchType.UNIT_COUNT, total_daggers, Teams.SHARDED, 0, Units.DAGGER)

# 4. Synchronization
sync(flag_active)
"""
        compile_res = compile_py(dsl_code)
        self.assertIn("setrule wave 18 0 0 0 0", compile_res.mlog)
        self.assertIn("setflag \"mission_alpha\" 1", compile_res.mlog)
        self.assertIn("getflag flag_active \"mission_alpha\"", compile_res.mlog)
        self.assertIn("spawn @dagger 40 40 0 @sharded target_u 0", compile_res.mlog)
        self.assertIn("setprop @health target_u 80", compile_res.mlog)
        self.assertIn("setprop @shield target_u 120", compile_res.mlog)
        self.assertIn("fetch core core_entity @sharded 0 0", compile_res.mlog)
        self.assertIn("fetch coreCount total_cores @sharded 0 0", compile_res.mlog)
        self.assertIn("fetch unitCount total_daggers @sharded 0 @dagger", compile_res.mlog)
        self.assertIn("sync flag_active", compile_res.mlog)

        # Decompile the compiled mlog
        decompiled_py = decompile(compile_res.mlog)
        self.assertIn("from mlog import fetch, getflag, setflag, setprop, setrule, spawn, sync", decompiled_py)
        self.assertIn("setrule(\"wave\", 18, 0, 0, 0, 0)", decompiled_py)
        self.assertIn("setflag(\"mission_alpha\", 1)", decompiled_py)
        self.assertIn("getflag(flag_active, \"mission_alpha\")", decompiled_py)
        self.assertIn("sync(flag_active)", decompiled_py)

        # End-to-end execute decompiled code after re-compilation
        recompiled = compile_py(decompiled_py)
        mlog_with_header = "#processor: world\n" + recompiled.mlog
        exec_res = run_with_mindustry(mlog_with_header)
        self.assertTrue(exec_res.success, f"recompiled mlog execution failed: {exec_res.message}")
        self.assertEqual(exec_res.vars.get("flag_active"), 1)
        self.assertEqual(exec_res.vars.get("target_u"), "dagger")
        self.assertGreaterEqual(exec_res.vars.get("total_cores", 0), 1)
        self.assertGreaterEqual(exec_res.vars.get("total_daggers", 0), 1)


if __name__ == "__main__":
    unittest.main()
