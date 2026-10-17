"""Tier 4 Regression Suite: World Processor & Map Scripting - Group A (World State & Tile Manipulation).

Verifies Group A opcodes (query, getblock, setblock) against live Mindustry v160.7 JVM engine.
Covers:
1. Privileged processor permission enforcement (standard processor rejects vs world processor executes).
2. Distinction between world-level 'getblock' opcode and unit-level 'ucontrol getBlock' subcommand.
3. Layer-specific queries and mutations (floor, ore, block, building) and out-of-bounds safety.
4. Spatial query operations (circle, rect) across unit and building hierarchies.
5. End-to-end Python DSL compilation and decompiler roundtrip.
"""

import unittest
from src.compiler import Compiler
from src.decompiler import decompile
from src.mindustry_validator import is_mindustry_available, run_with_mindustry, validate_with_mindustry
from src.mlog import compile_py
from src.mlog_registry import (
    QueryShape,
    QueryType,
    Teams,
    TileLayer,
)


@unittest.skipUnless(is_mindustry_available(), "Mindustry validation harness unavailable")
class TestTier4WorldState(unittest.TestCase):
    """Test suite for Tier 4 Group A: World State & Tile Manipulation opcodes."""

    def test_privileged_processor_enforcement(self):
        """Verify that standard processors reject Group A opcodes while World Processors permit them."""
        # 1. Standard processor rejects 'getblock' as InvalidStatement
        mlog_std_get = "getblock block res 50 50\n"
        res_std_get = run_with_mindustry(mlog_std_get)
        self.assertFalse(res_std_get.success)
        self.assertIn("InvalidStatement", res_std_get.message)

        # 2. Standard processor rejects 'setblock' as InvalidStatement
        mlog_std_set = "setblock block @copper-wall 20 20 @sharded 0\n"
        res_std_set = run_with_mindustry(mlog_std_set)
        self.assertFalse(res_std_set.success)
        self.assertIn("InvalidStatement", res_std_set.message)

        # 3. Standard processor rejects 'query' as InvalidStatement
        mlog_std_query = "query circle unit @sharded 50 50 20 20\n"
        res_std_query = run_with_mindustry(mlog_std_query)
        self.assertFalse(res_std_query.success)
        self.assertIn("InvalidStatement", res_std_query.message)

        # 4. World processor permits all three statements cleanly
        mlog_world = """#processor: world
getblock block b_proc 50 50
setblock block @copper-wall 20 20 @sharded 0
query circle unit @sharded 50 50 20 20
"""
        res_world = run_with_mindustry(mlog_world)
        self.assertTrue(res_world.success, f"world processor execution failed: {res_world.message}")
        self.assertEqual(res_world.vars.get("b_proc"), "world-processor")

    def test_getblock_layers_and_out_of_bounds(self):
        """Verify getblock across floor, ore, block, and building layers and out-of-bounds boundary safety."""
        mlog = """#processor: world
#links: cell1
# 1. Tile at (50, 50) is the world processor itself
getblock block p_block 50 50
getblock building p_build 50 50

# 2. Tile at (51, 50) is the linked cell1
getblock block c_block 51 50
getblock building c_build 51 50

# 3. Tile at (25, 25) has stone floor and copper ore
getblock floor ore_floor 25 25
getblock ore ore_overlay 25 25

# 4. Out-of-bounds coordinate reads return null
getblock block oob_neg_block -1 -1
getblock floor oob_neg_floor -5 50
getblock ore oob_large_ore 999 999
getblock building oob_large_build 500 500
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"getblock execution failed: {res.message}")
        self.assertEqual(res.vars.get("p_block"), "world-processor")
        self.assertEqual(res.vars.get("p_build"), "world-processor")
        self.assertEqual(res.vars.get("c_block"), "memory-cell")
        self.assertEqual(res.vars.get("c_build"), "memory-cell")
        self.assertEqual(res.vars.get("ore_floor"), "stone")
        self.assertEqual(res.vars.get("ore_overlay"), "ore-copper")
        # Boundary cases
        self.assertEqual(res.vars.get("oob_neg_block"), "null")
        self.assertEqual(res.vars.get("oob_neg_floor"), "null")
        self.assertEqual(res.vars.get("oob_large_ore"), "null")
        self.assertEqual(res.vars.get("oob_large_build"), "null")

    def test_setblock_blocks_floors_ores_and_rotation(self):
        """Verify setblock mutates map tiles for blocks, floors, and ores and confirms with getblock."""
        mlog = """#processor: world
# 1. Place a copper-wall block with rotation 1 and team sharded
setblock block @copper-wall 30 30 @sharded 1
getblock block placed_block 30 30
getblock building placed_build 30 30

# 2. Mutate floor to dirt
setblock floor @dirt 31 31 @derelict 0
getblock floor placed_floor 31 31

# 3. Apply copper ore overlay, read, then clear overlay back to air
setblock ore @ore-copper 32 32 @derelict 0
getblock ore placed_ore 32 32
setblock ore @air 32 32 @derelict 0
getblock ore cleared_ore 32 32

# 4. Remove placed block by setting to @air
setblock block @air 30 30 @derelict 0
getblock block removed_block 30 30
getblock building removed_build 30 30
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"setblock execution failed: {res.message}")
        self.assertEqual(res.vars.get("placed_block"), "copper-wall")
        self.assertEqual(res.vars.get("placed_build"), "copper-wall")
        self.assertEqual(res.vars.get("placed_floor"), "dirt")
        self.assertEqual(res.vars.get("placed_ore"), "ore-copper")
        self.assertEqual(res.vars.get("cleared_ore"), "air")
        self.assertEqual(res.vars.get("removed_block"), "air")
        self.assertEqual(res.vars.get("removed_build"), "null")

    def test_query_circle_and_rect_units_and_buildings(self):
        """Verify query opcode spatial filtering (circle/rect) across unit and building hierarchies."""
        mlog = """#processor: world
#links: cell1
# 1. Query units in circle around processor (radius 20) -> finds sharded flares
query circle unit @sharded 50 50 20 20
sensor unit_q_len @queries @size
read u0 @queries 0
sensor u0_type u0 @type

# 2. Query units in empty area -> size is 0 and read is null
query circle unit @sharded 0 0 5 5
sensor empty_q_len @queries @size
read u_none @queries 0

# 3. Query buildings in circle around processor (radius 10) -> finds world-processor and cell1
query circle building @sharded 50 50 10 10
sensor build_circle_len @queries @size

# 4. Query buildings in rectangle covering core (40,40), processor (50,50), and cell1 (51,50)
query rect building @sharded 35 35 25 25
sensor build_rect_len @queries @size
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"query execution failed: {res.message}")
        self.assertEqual(res.vars.get("unit_q_len"), 2.0)
        self.assertEqual(res.vars.get("u0"), "flare")
        self.assertEqual(res.vars.get("u0_type"), "flare")
        self.assertEqual(res.vars.get("empty_q_len"), 0.0)
        self.assertEqual(res.vars.get("u_none"), "null")
        self.assertEqual(res.vars.get("build_circle_len"), 2.0)
        self.assertEqual(res.vars.get("build_rect_len"), 3.0)

    def test_distinction_between_world_getblock_and_ucontrol_getblock(self):
        """Verify distinct semantics between global world-statement getblock and unit-bound ucontrol getBlock."""
        # 1. ucontrol getBlock requires a bound unit and respects unit range
        mlog_ucontrol = """#links: cell1
ubind @flare
ucontrol getBlock 51 50 b_block b_build b_floor 0
ucontrol getBlock 1 1 out_block out_build out_floor 0
"""
        res_ucontrol = run_with_mindustry(mlog_ucontrol)
        self.assertTrue(res_ucontrol.success, f"ucontrol getBlock failed: {res_ucontrol.message}")
        self.assertEqual(res_ucontrol.vars.get("b_block"), "memory-cell")
        self.assertEqual(res_ucontrol.vars.get("out_block"), "null")  # Beyond flare range

        # 2. world-statement getblock does not require a unit and has infinite global range
        mlog_world = """#processor: world
#links: cell1
getblock block b_near 51 50
getblock floor f_far 1 1
"""
        res_world = run_with_mindustry(mlog_world)
        self.assertTrue(res_world.success, f"world getblock failed: {res_world.message}")
        self.assertEqual(res_world.vars.get("b_near"), "memory-cell")
        self.assertNotEqual(res_world.vars.get("f_far"), "null")

    def test_group_a_compiler_and_decompiler_roundtrip(self):
        """Verify Group A opcodes compile from Python DSL and decompile cleanly back to valid DSL."""
        dsl_code = """from mlog import QueryShape, QueryType, Teams, TileLayer, getblock, query, setblock

query(QueryShape.CIRCLE, QueryType.UNIT, Teams.SHARDED, 50, 50, 20, 20)
b = getblock(TileLayer.BLOCK, 50, 50)
getblock(TileLayer.FLOOR, out_floor, 20, 20)
setblock(TileLayer.BLOCK, "@copper-wall", 30, 30, Teams.SHARDED, 1)
setblock(TileLayer.FLOOR, "@dirt", 30, 30)
"""
        compile_res = compile_py(dsl_code)
        self.assertIn("query circle unit @sharded 50 50 20 20", compile_res.mlog)
        self.assertIn("getblock block b 50 50", compile_res.mlog)
        self.assertIn("getblock floor out_floor 20 20", compile_res.mlog)
        self.assertIn("setblock block @copper-wall 30 30 @sharded 1", compile_res.mlog)
        self.assertIn("setblock floor @dirt 30 30 @derelict 0", compile_res.mlog)

        # Decompile the compiled mlog
        decompiled_py = decompile(compile_res.mlog)
        self.assertIn("from mlog import getblock, query, setblock", decompiled_py)
        self.assertIn("query(\"circle\", \"unit\", \"@sharded\", 50, 50, 20, 20)", decompiled_py)
        self.assertIn("getblock(\"block\", b, 50, 50)", decompiled_py)
        self.assertIn("setblock(\"block\", \"@copper-wall\", 30, 30, \"@sharded\", 1)", decompiled_py)

        # End-to-end execute decompiled code after re-compilation
        recompiled = compile_py(decompiled_py)
        mlog_with_header = "#processor: world\n" + recompiled.mlog
        exec_res = run_with_mindustry(mlog_with_header)
        self.assertTrue(exec_res.success, f"recompiled mlog execution failed: {exec_res.message}")
        self.assertEqual(exec_res.vars.get("b"), "world-processor")


if __name__ == "__main__":
    unittest.main()
