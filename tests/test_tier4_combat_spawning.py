"""Tier 4 Regression Suite: World Processor & Map Scripting - Group B (Unit & Combat Spawning).

Verifies Group B opcodes (spawn, bullet, explosion, status) against live Mindustry v160.7 JVM engine.
Covers:
1. Privileged processor permission enforcement (standard processor rejects vs world processor executes).
2. Unit spawning, positioning, rotation, and team assignment.
3. Bullet creation from unit weapon types and turret ammo configurations.
4. Status effect application, duration sensing, and clearing.
5. Logic explosions with distance/target filtering (air vs ground, friendly fire immunity, negative damage).
6. End-to-end Python DSL compilation, execution on real engine, and decompiler roundtrip.
"""

import unittest
from src.compiler import Compiler
from src.decompiler import decompile
from src.mindustry_validator import is_mindustry_available, run_with_mindustry
from src.mlog import compile_py
from src.mlog_registry import (
    StatusEffects,
    Teams,
    Units,
)


@unittest.skipUnless(is_mindustry_available(), "Mindustry validation harness unavailable")
class TestTier4CombatSpawning(unittest.TestCase):
    """Test suite for Tier 4 Group B: Unit & Combat Spawning opcodes."""

    def test_privileged_processor_enforcement(self):
        """Verify that standard processors reject Group B opcodes while World Processors permit them."""
        # 1. Standard processor rejects 'spawn' as InvalidStatement
        mlog_std_spawn = "spawn @dagger 50 50 0 @sharded u 0\n"
        res_std_spawn = run_with_mindustry(mlog_std_spawn)
        self.assertFalse(res_std_spawn.success)
        self.assertIn("InvalidStatement", res_std_spawn.message)

        # 2. Standard processor rejects 'bullet' as InvalidStatement
        mlog_std_bullet = "bullet b @dagger 0 50 50 0 @sharded null -1 1 1 -1 -1\n"
        res_std_bullet = run_with_mindustry(mlog_std_bullet)
        self.assertFalse(res_std_bullet.success)
        self.assertIn("InvalidStatement", res_std_bullet.message)

        # 3. Standard processor rejects 'status' as InvalidStatement
        mlog_std_status = "status false @status-burning u 10\n"
        res_std_status = run_with_mindustry(mlog_std_status)
        self.assertFalse(res_std_status.success)
        self.assertIn("InvalidStatement", res_std_status.message)

        # 4. Standard processor rejects 'explosion' as InvalidStatement
        mlog_std_explosion = "explosion @sharded 50 50 10 50 1 1 0 0\n"
        res_std_explosion = run_with_mindustry(mlog_std_explosion)
        self.assertFalse(res_std_explosion.success)
        self.assertIn("InvalidStatement", res_std_explosion.message)

        # 5. World processor permits all four statements cleanly
        mlog_world = """#processor: world
spawn @dagger 50 50 0 @sharded u 0
status false @status-burning u 10
explosion @sharded 50 50 10 50 1 1 0 0
bullet b @dagger 0 50 50 0 @sharded null -1 1 1 -1 -1
"""
        res_world = run_with_mindustry(mlog_world)
        self.assertTrue(res_world.success, f"world processor execution failed: {res_world.message}")
        self.assertEqual(res_world.vars.get("u"), "dagger")
        self.assertIsNotNone(res_world.vars.get("b"))
        self.assertNotEqual(res_world.vars.get("b"), "null")

    def test_spawn_units_and_team_assignment(self):
        """Verify unit spawning across multiple types, teams, and out-of-bounds/invalid boundaries."""
        mlog = """#processor: world
spawn @dagger 30 30 45 @sharded u_dagger 0
spawn @flare 60 60 180 @crux u_flare 0
spawn @mono 10 10 0 @sharded u_mono 0

# Sense unit type and team properties
sensor type_dagger u_dagger @type
sensor team_dagger u_dagger @team
sensor type_flare u_flare @type
sensor team_flare u_flare @team

# Unit cap enforcement: derelict team has 0 unit cap, so spawn returns null
spawn @mono 10 10 0 @derelict u_derelict 0

# Invalid / null type boundary test
spawn null 50 50 0 @sharded u_null 0
spawn @dagger -100 -100 0 @sharded u_oob 0
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"execution failed: {res.message}")
        self.assertEqual(res.vars.get("u_dagger"), "dagger")
        self.assertEqual(res.vars.get("u_flare"), "flare")
        self.assertEqual(res.vars.get("u_mono"), "mono")
        self.assertEqual(res.vars.get("type_dagger"), "dagger")
        self.assertEqual(res.vars.get("type_flare"), "flare")
        self.assertEqual(res.vars.get("u_derelict"), "null")
        self.assertEqual(res.vars.get("u_null"), "null")
        self.assertEqual(res.vars.get("u_oob"), "dagger")

    def test_bullet_spawning_from_unit_and_turret(self):
        """Verify bullet spawning from unit weapons, turret ammo, and invalid boundary configurations."""
        mlog = """#processor: world
# 1. Bullet from unit weapon (@dagger, weapon index 0)
bullet b_unit @dagger 0 50 50 90 @sharded null -1 1 1 -1 -1

# 2. Bullet from turret ammo (@duo turret with @copper ammo)
bullet b_turret @duo @copper 50 50 45 @sharded null -1 1 1 -1 -1

# 3. Invalid boundaries: null from, null ammo, out-of-range index
bullet b_inv_from null 0 50 50 0 @sharded null -1 1 1 -1 -1
bullet b_inv_ammo @duo null 50 50 0 @sharded null -1 1 1 -1 -1
bullet b_inv_idx @dagger 999 50 50 0 @sharded null -1 1 1 -1 -1
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"execution failed: {res.message}")
        # b_unit and b_turret create valid Bullet objects
        self.assertIn("Bullet", str(res.vars.get("b_unit")))
        self.assertIn("Bullet", str(res.vars.get("b_turret")))
        # Invalid cases return null
        self.assertEqual(res.vars.get("b_inv_from"), "null")
        self.assertEqual(res.vars.get("b_inv_ammo"), "null")
        self.assertEqual(res.vars.get("b_inv_idx"), "null")

    def test_status_apply_duration_and_clear(self):
        """Verify status effect application, sensing duration, clearing, and boundary safety."""
        mlog = """#processor: world
spawn @dagger 50 50 0 @sharded u 0

# Apply burning status for 10 seconds
status false @status-burning u 10
sensor dur_burning u @status-burning

# Apply wet status for 5 seconds
status false @status-wet u 5
sensor dur_wet u @status-wet

# Clear burning status
status true @status-burning u 0
sensor dur_burning_cleared u @status-burning

# Boundary safety: status on null unit and null effect
status false null null 10
status false @status-burning null 10
status false null u 10
set ok 1
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"execution failed: {res.message}")
        self.assertEqual(res.vars.get("dur_burning"), 10.0)
        self.assertEqual(res.vars.get("dur_wet"), 5.0)
        self.assertEqual(res.vars.get("dur_burning_cleared"), 0.0)
        self.assertEqual(res.vars.get("ok"), 1.0)

    def test_explosion_damage_and_filtering(self):
        """Verify explosion damage semantics: friendly fire immunity, air/ground filtering, negative damage."""
        mlog = """#processor: world
# Spawn an enemy ground unit (@dagger, Team crux, 150 max health)
spawn @dagger 50 50 0 @crux enemy 0
sensor hp_initial enemy @health

# 1. Friendly fire check: @crux explosion does not damage @crux enemy
explosion @crux 50 50 10 30 1 1 0 0
sensor hp_after_friendly enemy @health

# 2. Air-only explosion: dagger is ground unit, so air-only explosion deals 0 damage
explosion @sharded 50 50 10 30 1 0 0 0
sensor hp_after_air enemy @health

# 3. Negative damage check: damage < 0 is ignored
explosion @sharded 50 50 10 -50 1 1 0 0
sensor hp_after_neg enemy @health

# 4. Ground explosion: deals 40 damage to ground dagger (150 -> 110)
explosion @sharded 50 50 10 40 0 1 0 0
sensor hp_after_ground enemy @health
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"execution failed: {res.message}")
        self.assertEqual(res.vars.get("hp_initial"), 150.0)
        self.assertEqual(res.vars.get("hp_after_friendly"), 150.0)
        self.assertEqual(res.vars.get("hp_after_air"), 150.0)
        self.assertEqual(res.vars.get("hp_after_neg"), 150.0)
        self.assertEqual(res.vars.get("hp_after_ground"), 110.0)

    def test_group_b_dsl_and_decompiler_roundtrip(self):
        """Verify end-to-end Python DSL compilation, JVM execution, and decompiler roundtrip."""
        dsl_code = """from mlog import spawn, bullet, status, explosion, Units, Teams, StatusEffects

u = spawn(Units.DAGGER, 50, 50, 90, Teams.SHARDED, 1)
status(False, StatusEffects.BURNING, u, 10)
explosion(Teams.SHARDED, 50, 50, 20, 50, 1, 1, 0, 1)
b = bullet(Units.DAGGER, 0, 50, 50, 90, Teams.SHARDED)
"""
        # 1. Compile DSL to mlog
        res = compile_py(dsl_code)
        self.assertIn("spawn @dagger 50 50 90 @sharded u 1", res.mlog)
        self.assertIn("status 0 @status-burning u 10", res.mlog)
        self.assertIn("explosion @sharded 50 50 20 50 1 1 0 1", res.mlog)
        self.assertIn("bullet b @dagger 0 50 50 90 @sharded null -1 1 1 -1 -1", res.mlog)

        # 2. Execute on real Mindustry JVM engine (with #processor: world header)
        jvm_mlog = "#processor: world\n" + res.mlog
        jvm_res = run_with_mindustry(jvm_mlog)
        self.assertTrue(jvm_res.success, f"JVM execution of compiled DSL failed: {jvm_res.message}")
        self.assertEqual(jvm_res.vars.get("u"), "dagger")
        self.assertIsNotNone(jvm_res.vars.get("b"))

        # 3. Decompile back to Python DSL
        decomp = decompile(res.mlog)
        self.assertIn("spawn", decomp)
        self.assertIn("status", decomp)
        self.assertIn("explosion", decomp)
        self.assertIn("bullet", decomp)

        # 4. Recompile decompiled Python and verify roundtrip invariance
        recompiled = compile_py(decomp)
        self.assertEqual(res.mlog.strip(), recompiled.mlog.strip())


if __name__ == "__main__":
    unittest.main()
