"""Tier 3 Runtime Execution Tests for Mindustry v160.7 Opcodes.

Validates exact runtime semantics using Mindustry JVM engine (LExecutor) via `run_with_mindustry`.

Covers:
- Group A (Pure Arithmetic/Logic/Control opcodes running directly without mock state):
  - select (all 8 ConditionOps, pure ternary lowering, intrinsic select)
  - packcolor & unpackcolor (color packing, unpacking, clamping in Mathf.clamp)
  - noop (execution step counting, zero side-effects)
  - integrated pipelines combining select, packcolor, noop, and unpackcolor
- Group B (Text Buffer & Message Block Emulation):
  - print (concatenation, number and object formatting, explicit newlines, 400-char buffer cap)
  - printchar (numeric character codes, Unicode characters)
  - format (lowest placeholder matching {0}..{9}, repeated and out-of-order placeholders)
  - printflush (flushing to real MessageBlock.MessageBuild, buffer clearing, unlinked handling)
  - compiled Python print/format/printflush pipelines
- Group C (Timing & Rate Semantics):
  - wait (tick yielding on <= 0, exact virtual time progression at 60 FPS, loop timer resets, IPT independence)
  - setrate (IPT clamp bounds across processor types, integer truncation, scheduler accumulator pacing)
- Group D (World State & Sensors):
  - getlink (bounds checking, negative/overflow clamp to null, @links count, float truncation)
  - sensor (numeric/object properties, null/dead semantics, CharSequence size, privileged camera access control)
  - getblock (TileLayer layers floor/ore/block/building on world processor, out-of-bounds null, standard processor sandbox rejection)
"""

import math
import unittest

from src.decompiler import decompile
from src.mindustry_validator import is_mindustry_available, run_with_mindustry
from src.mlog import SensorProperty, compile_py


class TestTier3Runtime(unittest.TestCase):
    """Test suite executing opcodes on real Mindustry LExecutor."""

    def setUp(self):
        if not is_mindustry_available():
            self.skipTest("Mindustry JVM harness is not available in this environment")

    # -----------------------------------------------------------------------
    # 1. 'select' Opcode Semantics in LExecutor
    # -----------------------------------------------------------------------

    def test_select_all_condition_ops(self):
        """Verify all 8 ConditionOps in 'select' opcode execute accurately in LExecutor."""
        mlog = """
select res_eq1 equal 5 5 100 200
select res_eq2 equal 5 6 100 200
select res_neq1 notEqual 5 6 100 200
select res_neq2 notEqual 5 5 100 200
select res_lt1 lessThan 3 5 100 200
select res_lt2 lessThan 5 3 100 200
select res_lte1 lessThanEq 5 5 100 200
select res_lte2 lessThanEq 6 5 100 200
select res_gt1 greaterThan 7 5 100 200
select res_gt2 greaterThan 5 7 100 200
select res_gte1 greaterThanEq 5 5 100 200
select res_gte2 greaterThanEq 4 5 100 200
select res_seq1 strictEqual 42 42 100 200
select res_seq2 strictEqual null null 100 200
select res_seq3 strictEqual 0 null 100 200
select res_alw always 0 0 100 200
"""
        ok, vars_d, msg = run_with_mindustry(mlog)
        self.assertTrue(ok, f"select execution failed: {msg}")
        self.assertEqual(vars_d.get("res_eq1"), 100.0)
        self.assertEqual(vars_d.get("res_eq2"), 200.0)
        self.assertEqual(vars_d.get("res_neq1"), 100.0)
        self.assertEqual(vars_d.get("res_neq2"), 200.0)
        self.assertEqual(vars_d.get("res_lt1"), 100.0)
        self.assertEqual(vars_d.get("res_lt2"), 200.0)
        self.assertEqual(vars_d.get("res_lte1"), 100.0)
        self.assertEqual(vars_d.get("res_lte2"), 200.0)
        self.assertEqual(vars_d.get("res_gt1"), 100.0)
        self.assertEqual(vars_d.get("res_gt2"), 200.0)
        self.assertEqual(vars_d.get("res_gte1"), 100.0)
        self.assertEqual(vars_d.get("res_gte2"), 200.0)
        self.assertEqual(vars_d.get("res_seq1"), 100.0)
        self.assertEqual(vars_d.get("res_seq2"), 100.0)
        self.assertEqual(vars_d.get("res_seq3"), 200.0)
        self.assertEqual(vars_d.get("res_alw"), 100.0)

    def test_select_compiled_python_ternary(self):
        """Verify compiled Python ternary lowers to select and executes in LExecutor."""
        py_src = """
a = 15
b = 10
res1 = 100 if a > b else 200
res2 = 100 if a < b else 200
res3 = 100 if a == 15 else 200
res4 = 100 if a != 15 else 200
"""
        res = compile_py(py_src)
        self.assertTrue(all("select" in l for l in res.mlog.strip().splitlines() if "res" in l))

        ok, vars_d, msg = run_with_mindustry(res.mlog)
        self.assertTrue(ok, f"Execution failed: {msg}")
        self.assertEqual(vars_d.get("res1"), 100.0)
        self.assertEqual(vars_d.get("res2"), 200.0)
        self.assertEqual(vars_d.get("res3"), 100.0)
        self.assertEqual(vars_d.get("res4"), 200.0)

    def test_select_compiled_intrinsics(self):
        """Verify compiled intrinsic select() calls execute correctly in LExecutor."""
        py_src = """
from mlog import select
r1 = select("lessThan", 10, 20, 1, 2)
r2 = select("greaterThan", 10, 20, 1, 2)
r3 = select("equal", 5, 5, 10, 20)
"""
        res = compile_py(py_src)
        ok, vars_d, msg = run_with_mindustry(res.mlog)
        self.assertTrue(ok, f"Execution failed: {msg}")
        self.assertEqual(vars_d.get("r1"), 1.0)
        self.assertEqual(vars_d.get("r2"), 2.0)
        self.assertEqual(vars_d.get("r3"), 10.0)

    # -----------------------------------------------------------------------
    # 2. 'packcolor' & 'unpackcolor' Semantics in LExecutor
    # -----------------------------------------------------------------------

    def test_packcolor_and_unpackcolor_roundtrip(self):
        """Verify color packing and unpacking preserve RGBA components in LExecutor."""
        mlog = """
packcolor packed 1.0 0.5 0.25 1.0
unpackcolor r g b a packed
"""
        ok, vars_d, msg = run_with_mindustry(mlog)
        self.assertTrue(ok, f"Execution failed: {msg}")
        self.assertIn("packed", vars_d)
        self.assertAlmostEqual(vars_d.get("r"), 1.0, places=2)
        self.assertAlmostEqual(vars_d.get("g"), 0.5, places=2)
        self.assertAlmostEqual(vars_d.get("b"), 0.25, places=2)
        self.assertAlmostEqual(vars_d.get("a"), 1.0, places=2)

    def test_packcolor_clamping_semantics(self):
        """Verify packcolor clamps out-of-range floats to [0, 1] matching Mathf.clamp."""
        mlog = """
packcolor packed -0.5 1.8 0.0 2.0
unpackcolor r g b a packed
"""
        ok, vars_d, msg = run_with_mindustry(mlog)
        self.assertTrue(ok, f"Execution failed: {msg}")
        self.assertAlmostEqual(vars_d.get("r"), 0.0, places=2)
        self.assertAlmostEqual(vars_d.get("g"), 1.0, places=2)
        self.assertAlmostEqual(vars_d.get("b"), 0.0, places=2)
        self.assertAlmostEqual(vars_d.get("a"), 1.0, places=2)

    def test_packcolor_unpackcolor_compiled_intrinsics(self):
        """Verify compiled Python packcolor() and unpackcolor() execute in LExecutor."""
        py_src = """
from mlog import packcolor, unpackcolor
c = packcolor(0.2, 0.4, 0.6, 0.8)
unpackcolor(r, g, b, a, c)
"""
        res = compile_py(py_src)
        self.assertIn("packcolor c 0.2 0.4 0.6 0.8", res.mlog)
        self.assertIn("unpackcolor r g b a c", res.mlog)

        ok, vars_d, msg = run_with_mindustry(res.mlog)
        self.assertTrue(ok, f"Execution failed: {msg}")
        self.assertAlmostEqual(vars_d.get("r"), 0.2, places=1)
        self.assertAlmostEqual(vars_d.get("g"), 0.4, places=1)
        self.assertAlmostEqual(vars_d.get("b"), 0.6, places=1)
        self.assertAlmostEqual(vars_d.get("a"), 0.8, places=1)

    def test_unpackcolor_tuple_unpacking_compiled_form(self):
        """Verify 'r, g, b, a = unpackcolor(c)' emits the RGBA-ordered 5-operand form."""
        py_src = """
from mlog import packcolor, unpackcolor
c = packcolor(0.2, 0.4, 0.6, 0.8)
r, g, b, a = unpackcolor(c)
"""
        res = compile_py(py_src)
        self.assertIn("unpackcolor r g b a c", res.mlog)

        ok, vars_d, msg = run_with_mindustry(res.mlog)
        self.assertTrue(ok, f"Execution failed: {msg}")
        self.assertAlmostEqual(vars_d.get("r"), 0.2, places=1)
        self.assertAlmostEqual(vars_d.get("g"), 0.4, places=1)
        self.assertAlmostEqual(vars_d.get("b"), 0.6, places=1)
        self.assertAlmostEqual(vars_d.get("a"), 0.8, places=1)

    def test_unpackcolor_distinct_channel_order_on_engine(self):
        """Pin the RGBA operand order with maximally distinct channels."""
        mlog = """
packcolor packed 1.0 0.5 0.25 0.75
unpackcolor out_r out_g out_b out_a packed
"""
        ok, vars_d, msg = run_with_mindustry(mlog)
        self.assertTrue(ok, f"Execution failed: {msg}")
        self.assertAlmostEqual(vars_d.get("out_r"), 1.0, places=2)
        self.assertAlmostEqual(vars_d.get("out_g"), 0.5, places=2)
        self.assertAlmostEqual(vars_d.get("out_b"), 0.25, places=2)
        self.assertAlmostEqual(vars_d.get("out_a"), 0.75, places=2)

    def test_unpackcolor_source_reused_as_target(self):
        """LExecutor.UnpackColorI reads `value` before writing outputs; aliasing is safe."""
        mlog = """
packcolor packed 0.2 0.4 0.6 0.8
unpackcolor packed g b a packed
"""
        ok, vars_d, msg = run_with_mindustry(mlog)
        self.assertTrue(ok, f"Execution failed: {msg}")
        self.assertAlmostEqual(vars_d.get("packed"), 0.2, places=1)
        self.assertAlmostEqual(vars_d.get("g"), 0.4, places=1)
        self.assertAlmostEqual(vars_d.get("b"), 0.6, places=1)
        self.assertAlmostEqual(vars_d.get("a"), 0.8, places=1)

    # -----------------------------------------------------------------------
    # 3. 'noop' Runtime Semantics in LExecutor
    # -----------------------------------------------------------------------

    def test_noop_step_counting_and_zero_side_effects(self):
        """Verify noop executes as a NoopI step without mutating any register state."""
        mlog = """
set x 10
noop
op add x x 5
noop
noop
set y 20
"""
        ok, vars_d, msg = run_with_mindustry(mlog)
        self.assertTrue(ok, f"Execution failed: {msg}")
        # Total steps must match total instruction lines (6 instructions)
        self.assertIn("RUN_OK:6", msg)
        self.assertEqual(vars_d.get("x"), 15.0)
        self.assertEqual(vars_d.get("y"), 20.0)

    # -----------------------------------------------------------------------
    # 4. Integrated Pure Opcode Pipeline Execution
    # -----------------------------------------------------------------------

    def test_integrated_pure_opcodes_pipeline(self):
        """Verify complex pipeline combining select, packcolor, noop, unpackcolor, and arithmetic."""
        mlog = """
set flag 1
select chosen_r equal flag 1 0.75 0.1
noop
packcolor col chosen_r 0.5 0.25 1.0
noop
unpackcolor r g b a col
op add total r g
"""
        ok, vars_d, msg = run_with_mindustry(mlog)
        self.assertTrue(ok, f"Execution failed: {msg}")
        self.assertAlmostEqual(vars_d.get("chosen_r"), 0.75, places=2)
        self.assertAlmostEqual(vars_d.get("r"), 0.75, places=2)
        self.assertAlmostEqual(vars_d.get("g"), 0.5, places=2)
        self.assertAlmostEqual(vars_d.get("total"), 1.25, places=2)

    # -----------------------------------------------------------------------
    # 5. Group B: 'print' Opcode Semantics in LExecutor
    # -----------------------------------------------------------------------

    def test_print_concatenation_and_type_conversions(self):
        """Verify print concatenates without newlines, and formats ints, floats, objects, nulls."""
        mlog = """print "Status: "
print 1
print " (ratio: "
print 0.75
print ", item: "
print @copper
print ", null: "
print null
print ")"
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.text_buffer, "Status: 1 (ratio: 0.75, item: copper, null: null)")

    def test_print_explicit_escapes_and_newlines(self):
        """Verify print preserves Mindustry LAssembler escape sequences: \\n, \\", \\\\, and \\uXXXX."""
        mlog = 'print "Line 1\\nLine 2\\\\Backslash\\n\\"Quoted\\"\\nStar: \\u2605"\n'
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.text_buffer, 'Line 1\nLine 2\\Backslash\n"Quoted"\nStar: ★')

    def test_print_buffer_capacity_limit_400(self):
        """Verify LExecutor caps textBuffer at maxTextBuffer (400 chars)."""
        part100 = "0123456789" * 10
        mlog = f'print "{part100}"\nprint "{part100}"\nprint "{part100}"\nprint "{part100}"\nprint "EXTRA_OVERFLOW"\n'
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(len(res.text_buffer), 400)
        self.assertTrue(res.text_buffer.startswith(part100 * 4))
        self.assertNotIn("EXTRA_OVERFLOW", res.text_buffer)

    # -----------------------------------------------------------------------
    # 6. Group B: 'printchar' Opcode Semantics in LExecutor
    # -----------------------------------------------------------------------

    def test_printchar_numeric_and_unicode_characters(self):
        """Verify printchar converts integer and float character codes to characters."""
        mlog = """printchar 72
printchar 101
printchar 108.9
printchar 108
printchar 111
printchar 32
printchar 9733
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.text_buffer, "Hello ★")

    # -----------------------------------------------------------------------
    # 7. Group B: 'format' Opcode Semantics in LExecutor
    # -----------------------------------------------------------------------

    def test_format_placeholder_resolution(self):
        """Verify format resolves lowest placeholders {0}..{9} sequentially, repeated, and out-of-order."""
        mlog = """print "In-order: {0} + {1} = {2}\\n"
format 10
format 20
format 30
print "Out-order: B={1}, A={0}\\n"
format "alpha"
format "beta"
print "Repeated: {0} and {0}\\n"
format 99
format 88
print "No-match: Hello"
format 42
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        expected = (
            "In-order: 10 + 20 = 30\n"
            "Out-order: B=beta, A=alpha\n"
            "Repeated: 99 and 88\n"
            "No-match: Hello"
        )
        self.assertEqual(res.text_buffer, expected)

    # -----------------------------------------------------------------------
    # 8. Group B: 'printflush' and Mock MessageBlock Semantics in LExecutor
    # -----------------------------------------------------------------------

    def test_printflush_message_block_and_buffer_reset(self):
        """Verify printflush transfers textBuffer to MessageBuild and resets textBuffer to empty."""
        mlog = """print "Header: System Diagnostics\\n"
print "Status: OK\\n"
printflush message1
print "Second message: Alert\\n"
printflush message2
print "Unflushed tail"
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        # textBuffer must contain only what was printed AFTER the last printflush
        self.assertEqual(res.text_buffer, "Unflushed tail")
        # message1 and message2 received the flushed contents
        self.assertIn("message1", res.messages)
        self.assertIn("message2", res.messages)
        self.assertEqual(res.messages["message1"], "Header: System Diagnostics\nStatus: OK\n")
        self.assertEqual(res.messages["message2"], "Second message: Alert\n")

    def test_printflush_unlinked_message_clears_buffer(self):
        """Verify printflush to unlinked/non-existent message still resets textBuffer without errors."""
        mlog = """print "Discarded text"
printflush unlinked_block
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.text_buffer, "")
        self.assertNotIn("unlinked_block", res.messages)

    def test_printflush_failure_modes_enemy_and_dead_blocks(self):
        """Verify printflush fails cleanly when target block is enemy team or dead (isValid=false).

        LExecutor requires (target.building() instanceof LPrintable d && d.printable(exec)).
        If team mismatch or building is dead, d.printable(exec) returns false:
        - Target message content remains empty (flush rejected)
        - exec.textBuffer is still cleared unconditionally
        """
        mlog = """print "Enemy data"
printflush enemy_message1
print "Dead data"
printflush dead_message1
print "Trailing text"
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        # Both enemy and dead message blocks exist in links, but neither accepted the flush
        self.assertIn("enemy_message1", res.messages)
        self.assertEqual(res.messages["enemy_message1"], "")
        self.assertIn("dead_message1", res.messages)
        self.assertEqual(res.messages["dead_message1"], "")
        # textBuffer contains the un-flushed trailing text
        self.assertEqual(res.text_buffer, "Trailing text")

    # -----------------------------------------------------------------------
    # 9. Group B: Compiled Python Intrinsics Pipeline
    # -----------------------------------------------------------------------

    def test_compiled_python_print_and_printflush_intrinsics(self):
        """Verify compiled Python code using mlog print, printchar, format, printflush executes cleanly."""
        py_src = """from mlog import print, printchar, format, printflush

print("Score: {0}, grade: ")
format(95)
printchar(65)
print("\\n")
printflush("message1")
"""
        res = compile_py(py_src)
        run_res = run_with_mindustry(res.mlog)
        self.assertTrue(run_res.success, f"Execution failed: {run_res.message}")
        self.assertEqual(run_res.text_buffer, "")
        self.assertIn("message1", run_res.messages)
        self.assertEqual(run_res.messages["message1"], "Score: 95, grade: A\n")

    def test_print_number_and_object_formatting_engine(self):
        """Verify LExecutor.PrintI formats numbers with 0.00001 epsilon and resolves game objects/nulls."""
        mlog = """print 5.0
print " "
print 5.000005
print " "
print 5.0001
print " "
print 0.0
print " "
print -10.0
print " "
print @copper
print " "
print @sharded
print " "
print null
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        expected = "5 5 5.0001 0 -10 copper sharded null"
        self.assertEqual(res.text_buffer, expected)
        self.assertEqual(res.text_buffer_len, len(expected))

    def test_print_boundary_exact_400_truncation(self):
        """Verify LExecutor.PrintI truncates exact slice at 400 and ignores further prints."""
        prefix395 = "A" * 395
        # Print 395 chars, then print 10 chars (should take only 5), then print extra
        mlog = f"""print "{prefix395}"
print "1234567890"
print "EXTRA_IGNORED"
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.text_buffer_len, 400)
        self.assertEqual(len(res.text_buffer), 400)
        self.assertTrue(res.text_buffer.startswith(prefix395))
        self.assertTrue(res.text_buffer.endswith("12345"))
        self.assertNotIn("67890", res.text_buffer)
        self.assertNotIn("EXTRA_IGNORED", res.text_buffer)

    def test_printchar_content_emoji_and_non_printable_objects(self):
        """Verify LExecutor.PrintCharI handles numeric floor, UnlockableContent emoji, and rejects non-content objects."""
        mlog = """printchar 65
printchar @copper
printchar cell1
printchar 66.8
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        # 65 -> 'A', @copper -> \0 (headless emojiChar 0), cell1 -> non-content ignored, 66.8 -> floor 66 -> 'B'
        self.assertEqual(res.text_buffer, "A\x00B")
        self.assertEqual(res.text_buffer_len, 3)

    def test_format_lowest_placeholder_and_overflow_truncation(self):
        """Verify LExecutor.FormatI prioritizes lowest placeholder {0}..{9} and clamps expanded buffer to 400."""
        # 1. Lowest placeholder priority and tie breaking
        mlog1 = """print "{5} and {2} and {2}\\n"
format "FIRST"
format "SECOND"
format "THIRD"
"""
        res1 = run_with_mindustry(mlog1)
        self.assertTrue(res1.success, f"Execution failed: {res1.message}")
        self.assertEqual(res1.text_buffer, "THIRD and FIRST and SECOND\n")

        # 2. Buffer overflow during format expansion truncated to 400
        prefix380 = "X" * 380
        mlog2 = f"""print "{prefix380}{{0}}"
format "0123456789012345678901234567890123456789"
"""
        res2 = run_with_mindustry(mlog2)
        self.assertTrue(res2.success, f"Execution failed: {res2.message}")
        self.assertEqual(res2.text_buffer_len, 400)
        self.assertEqual(len(res2.text_buffer), 400)

    def test_printflush_to_non_printable_targets_always_clears_buffer(self):
        """Verify printflush to non-LPrintable targets (cell, duo, switch, display, literal) always clears textBuffer."""
        mlog = """print "Cell test"
printflush cell1
print "Turret test"
printflush duo1
print "Switch test"
printflush switch1
print "Display test"
printflush display1
print "Literal test"
printflush 999
print "Final survivor"
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        # Every printflush unconditionally cleared textBuffer, leaving only the trailing text
        self.assertEqual(res.text_buffer, "Final survivor")
        self.assertEqual(res.text_buffer_len, len("Final survivor"))
        # None of the non-printable targets should receive flushed messages
        self.assertNotIn("cell1", res.messages)
        self.assertNotIn("duo1", res.messages)
        self.assertNotIn("switch1", res.messages)
        self.assertNotIn("display1", res.messages)



    # -----------------------------------------------------------------------
    # 10. Group C: 'setrate' Opcode and Execution Rate Clamping
    # -----------------------------------------------------------------------

    def test_setrate_standard_processor_clamping_bounds(self):
        """Verify setrate updates ipt and clamps to [1, 8] on standard logicProcessor."""
        mlog = """setrate 4
set cur_ipt1 @ipt
setrate 0
set cur_ipt_zero @ipt
setrate -25
set cur_ipt_neg @ipt
setrate 100
set cur_ipt_max @ipt
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("cur_ipt1"), 4.0)
        self.assertEqual(res.vars.get("cur_ipt_zero"), 1.0)
        self.assertEqual(res.vars.get("cur_ipt_neg"), 1.0)
        self.assertEqual(res.vars.get("cur_ipt_max"), 8.0)
        self.assertEqual(res.ipt, 8)

    def test_setrate_hyper_and_world_processor_bounds(self):
        """Verify setrate respects processor-specific maximums (25 for hyper, 1000 for world)."""
        # Hyper processor
        mlog_hyper = """#processor: hyper
setrate 15
set r15 @ipt
setrate 999
set r_max @ipt
"""
        res_hyper = run_with_mindustry(mlog_hyper)
        self.assertTrue(res_hyper.success, f"Hyper execution failed: {res_hyper.message}")
        self.assertEqual(res_hyper.vars.get("r15"), 15.0)
        self.assertEqual(res_hyper.vars.get("r_max"), 25.0)
        self.assertEqual(res_hyper.ipt, 25)

        # World processor
        mlog_world = """#processor: world
setrate 500
set r500 @ipt
setrate 5000
set r_world_max @ipt
"""
        res_world = run_with_mindustry(mlog_world)
        self.assertTrue(res_world.success, f"World execution failed: {res_world.message}")
        self.assertEqual(res_world.vars.get("r500"), 500.0)
        self.assertEqual(res_world.vars.get("r_world_max"), 1000.0)
        self.assertEqual(res_world.ipt, 1000)

    # -----------------------------------------------------------------------
    # 11. Group C: 'wait' Opcode and Virtual Clock Timing Semantics
    # -----------------------------------------------------------------------

    def test_wait_zero_and_negative_single_tick_yield(self):
        """Verify wait <= 0 performs a 1-tick yield without rewinding instruction counter."""
        mlog = """set t0 @tick
wait 0
set t1 @tick
op sub dt0 t1 t0
wait -10
set t2 @tick
op sub dt_neg t2 t1
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("dt0"), 1.0)
        self.assertEqual(res.vars.get("dt_neg"), 1.0)
        self.assertEqual(res.ticks, 3)

    def test_wait_positive_duration_virtual_clock_ticks(self):
        """Verify wait duration translates to exact virtual ticks (duration * 60 ticks/sec)."""
        # 0.5s = 30 ticks, 0.25s = 15 ticks
        mlog = """set t0 @tick
wait 0.5
set t1 @tick
op sub dt_half t1 t0
wait 0.25
set t2 @tick
op sub dt_quarter t2 t1
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("dt_half"), 30.0)
        self.assertEqual(res.vars.get("dt_quarter"), 15.0)
        # Total ticks: 1 (start) + 30 (wait 0.5) + 15 (wait 0.25) = 46 ticks
        self.assertEqual(res.ticks, 46)

    def test_wait_tiny_positive_duration(self):
        """Verify wait with tiny duration (< 1/60 sec) completes after exactly 1 tick."""
        mlog = """set t0 @tick
wait 0.001
set t1 @tick
op sub dt t1 t0
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("dt"), 1.0)
        self.assertEqual(res.ticks, 2)

    # -----------------------------------------------------------------------
    # 12. Group C: Compiled Python wait() and setrate() Intrinsics
    # -----------------------------------------------------------------------

    def test_compiled_python_wait_and_setrate_intrinsics(self):
        """Verify compiled Python wait() and setrate() execute cleanly on JVM engine."""
        py_src = """from mlog import setrate, wait, Vars
setrate(5)
cur_rate = Vars.ipt
t_start = Vars.tick
wait(0.2)
t_end = Vars.tick
elapsed = t_end - t_start
"""
        res = compile_py(py_src)
        run_res = run_with_mindustry(res.mlog)
        self.assertTrue(run_res.success, f"Execution failed: {run_res.message}")
        self.assertEqual(run_res.vars.get("cur_rate"), 5.0)
        self.assertEqual(run_res.vars.get("elapsed"), 12.0)  # 0.2s * 60 = 12 ticks
        self.assertEqual(run_res.ipt, 5)


    # -----------------------------------------------------------------------
    # 13. Differential Tests Against Engine Scheduler Equations
    # -----------------------------------------------------------------------

    def test_setrate_dynamic_throttling_and_loop_timing(self):
        """Verify dynamic setrate modifications throttle loop execution as predicted by engine equations."""
        # Loop: 10 iterations of 3 instructions = 30 instructions
        # At IPT=5: exactly 6 ticks of elapsed time
        mlog_rate5 = """setrate 5
set i 0
set t0 @tick
op add d 1 1
op add i i 1
jump 3 lessThan i 10
set t1 @tick
op sub dt t1 t0
"""
        res5 = run_with_mindustry(mlog_rate5)
        self.assertTrue(res5.success, f"Rate 5 execution failed: {res5.message}")
        self.assertEqual(res5.vars.get("dt"), 6.0)
        self.assertEqual(res5.ipt, 5)

        # Dynamic rate change: starts at 2 IPT, then switches to 8 IPT
        mlog_dyn = """setrate 2
set i 0
set t0 @tick
op add i i 1
jump 3 lessThan i 4
setrate 8
op add i i 1
jump 6 lessThan i 12
set t1 @tick
op sub dt t1 t0
"""
        res_dyn = run_with_mindustry(mlog_dyn)
        self.assertTrue(res_dyn.success, f"Dynamic execution failed: {res_dyn.message}")
        self.assertEqual(res_dyn.vars.get("i"), 12.0)
        self.assertEqual(res_dyn.vars.get("dt"), 5.0)
        self.assertEqual(res_dyn.ipt, 8)

    def test_differential_wait_and_timing_equations_against_engine_model(self):
        """Verify wait timing matches independent 32-bit float engine simulation model for all test cases."""
        import ctypes

        def engine_simulated_wait_ticks(seconds: float) -> int:
            if seconds <= 0:
                return 1
            cur_time = ctypes.c_float(0.0)
            delta = ctypes.c_float(1.0 / 60.0)
            ticks = 0
            while cur_time.value < seconds and ticks < 1000:
                cur_time = ctypes.c_float(cur_time.value + delta.value)
                ticks += 1
            return ticks

        test_cases = [-10.0, 0.0, 0.001, 0.25, 0.5]
        for val in test_cases:
            expected_ticks = engine_simulated_wait_ticks(val)
            mlog = f"""set t0 @tick
wait {val}
set t1 @tick
op sub dt t1 t0
"""
            res = run_with_mindustry(mlog)
            self.assertTrue(res.success, f"Wait {val} failed: {res.message}")
            actual_dt = res.vars.get("dt")
            self.assertEqual(
                actual_dt,
                float(expected_ticks),
                f"Wait {val} diverged: expected {expected_ticks} ticks from engine model, got {actual_dt}",
            )


    # -----------------------------------------------------------------------
    # 14. Group C Supplemental Edge Cases
    # -----------------------------------------------------------------------

    def test_wait_consecutive_zero_yield_ticks(self):
        """Verify each consecutive 'wait 0' yields accumulator and consumes exactly 1 tick."""
        mlog = """set t0 @tick
wait 0
wait 0
wait 0
set t1 @tick
op sub dt t1 t0
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("dt"), 3.0)
        self.assertEqual(res.ticks, 4)

    def test_setrate_negative_and_zero_clamping(self):
        """Verify setrate clamps zero and negative values to 1 IPT per Mathf.clamp."""
        mlog = """setrate 0
set r0 @ipt
setrate -10
set r_neg @ipt
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("r0"), 1.0)
        self.assertEqual(res.vars.get("r_neg"), 1.0)
        self.assertEqual(res.ipt, 1)

    # -----------------------------------------------------------------------
    # 15. Group D: 'read' and 'write' Opcode Semantics in LExecutor
    # -----------------------------------------------------------------------

    def test_read_and_write_memory_cell_roundtrip(self):
        """Verify reading and writing float values to MemoryCell preserves values and default slots return 0.0."""
        mlog = """write 42.5 cell1 0
write 999.125 cell1 63
read val0 cell1 0
read val63 cell1 63
read unwritten cell1 5
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("val0"), 42.5)
        self.assertEqual(res.vars.get("val63"), 999.125)
        self.assertEqual(res.vars.get("unwritten"), 0.0)

    def test_read_and_write_memory_bank_capacity(self):
        """Verify MemoryBank supports address up to 511 (capacity 512)."""
        mlog = """write 12345.678 bank1 511
read bank_last bank1 511
read bank_first bank1 0
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("bank_last"), 12345.678)
        self.assertEqual(res.vars.get("bank_first"), 0.0)

    def test_read_write_out_of_bounds_and_unlinked(self):
        """Verify out-of-bounds read returns null, out-of-bounds write is a no-op, and unlinked target returns null."""
        mlog = """read oob_neg cell1 -1
read oob_pos cell1 64
write 9999 cell1 64
read oob_pos_after cell1 64
read bank_oob bank1 512
read unlinked unlinked_target 0
write 100 unlinked_target 0
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("oob_neg"), "null")
        self.assertEqual(res.vars.get("oob_pos"), "null")
        self.assertEqual(res.vars.get("oob_pos_after"), "null")
        self.assertEqual(res.vars.get("bank_oob"), "null")
        self.assertEqual(res.vars.get("unlinked"), "null")

    def test_read_string_character_codes(self):
        """Verify read on CharSequence target returns ASCII/Unicode character code or null if out of bounds (NaN normalizes to null)."""
        mlog = """read c0 "Hello" 0
read c1 "Hello" 1
read c_neg "Hello" -1
read c_oob "Hello" 10
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("c0"), 72.0)  # 'H'
        self.assertEqual(res.vars.get("c1"), 101.0)  # 'e'
        # In Mindustry LVar.setnum(), Double.isNaN(v) is classified as invalid() and normalized to null
        self.assertEqual(res.vars.get("c_neg"), "null")
        self.assertEqual(res.vars.get("c_oob"), "null")

    def test_write_and_read_objects(self):
        """Verify writing and reading content and string objects to MemoryCell."""
        mlog = """write @copper cell1 2
read obj_item cell1 2
write "payload_test" cell1 3
read obj_str cell1 3
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("obj_item"), "copper")
        self.assertEqual(res.vars.get("obj_str"), "payload_test")

    # -----------------------------------------------------------------------
    # 16. Group D: 'getlink' Opcode Semantics in LExecutor
    # -----------------------------------------------------------------------

    def test_getlink_indices_and_out_of_bounds(self):
        """Verify getlink retrieves linked buildings by index and returns null on invalid index."""
        mlog = """write 1 cell1 0
printflush message1
getlink b0 0
getlink b1 1
getlink b_neg -1
getlink b_oob 2
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("b0"), "memory-cell")
        self.assertEqual(res.vars.get("b1"), "message")
        self.assertEqual(res.vars.get("b_neg"), "null")
        self.assertEqual(res.vars.get("b_oob"), "null")

    def test_getlink_passed_to_sensor(self):
        """Verify building retrieved via getlink can be inspected dynamically with sensor."""
        mlog = """write 1 cell1 0
printflush message1
getlink link0 0
sensor t0 link0 @type
getlink link1 1
sensor t1 link1 @type
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("t0"), "memory-cell")
        self.assertEqual(res.vars.get("t1"), "message")

    # -----------------------------------------------------------------------
    # 17. Group D: 'sensor' Opcode Semantics in LExecutor
    # -----------------------------------------------------------------------

    def test_sensor_building_properties(self):
        """Verify sensor retrieves memoryCapacity, type, team, dead, and health properties from buildings."""
        mlog = """sensor cap_cell cell1 @memoryCapacity
sensor cap_bank bank1 @memoryCapacity
sensor t_cell cell1 @type
sensor t_bank bank1 @type
sensor team_cell cell1 @team
sensor is_dead cell1 @dead
sensor hp_cell cell1 @health
sensor max_hp_cell cell1 @maxHealth
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("cap_cell"), 64.0)
        self.assertEqual(res.vars.get("cap_bank"), 512.0)
        self.assertEqual(res.vars.get("t_cell"), "memory-cell")
        self.assertEqual(res.vars.get("t_bank"), "memory-bank")
        self.assertEqual(res.vars.get("team_cell"), 1.0)  # Team.sharded id = 1
        self.assertEqual(res.vars.get("is_dead"), 0.0)
        self.assertEqual(res.vars.get("hp_cell"), 1.0)
        self.assertEqual(res.vars.get("max_hp_cell"), 1.0)

    def test_sensor_dead_building_and_null(self):
        """Verify sensor dead handling: dead building is 1, null @dead is 1, null other is null, and string @size."""
        mlog = """sensor dead_live cell1 @dead
sensor dead_marked dead_cell1 @dead
sensor dead_from_null null @dead
sensor hp_from_null null @health
sensor str_size "Mindustry" @size
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("dead_live"), 0.0)
        self.assertEqual(res.vars.get("dead_marked"), 1.0)
        self.assertEqual(res.vars.get("dead_from_null"), 1.0)
        self.assertEqual(res.vars.get("hp_from_null"), "null")
        self.assertEqual(res.vars.get("str_size"), 9.0)

    # -----------------------------------------------------------------------
    # 18. Group D: 'radar' Opcode Semantics in LExecutor
    # -----------------------------------------------------------------------

    def test_radar_finds_near_enemy_unit(self):
        """Verify radar scanning from @this finds mock enemy unit in range and returns Unit object."""
        mlog = """set u near_enemy_unit
radar enemy any any distance @this 1 hit_unit
sensor hit_type hit_unit @type
sensor hit_team hit_unit @team
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("hit_unit"), "flare")
        self.assertEqual(res.vars.get("hit_type"), "flare")
        self.assertEqual(res.vars.get("hit_team"), 2.0)  # Team.crux id = 2

    def test_radar_out_of_range_and_invalid_sources(self):
        """Verify radar returns null when enemy is out of range, source is null, or source is non-ranged."""
        mlog = """set u far_enemy_unit
radar enemy any any distance @this 1 far_hit
radar enemy any any distance null 1 null_hit
printflush message1
radar enemy any any distance message1 1 non_ranged_hit
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("far_hit"), "null")
        self.assertEqual(res.vars.get("null_hit"), "null")
        self.assertEqual(res.vars.get("non_ranged_hit"), "null")

    # -----------------------------------------------------------------------
    # 19. Group D: 'lookup' Opcode Semantics in LExecutor
    # -----------------------------------------------------------------------

    def test_lookup_content_types_and_bounds(self):
        """Verify lookup opcode across item, liquid, block, and team content types, and boundary checks."""
        mlog = """lookup item i0 0
lookup item i1 1
lookup liquid l0 0
lookup block b0 0
lookup team t1 1
lookup team t2 2
lookup item oob 9999
lookup item oob_neg -1
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("i0"), "copper")
        self.assertEqual(res.vars.get("i1"), "lead")
        self.assertEqual(res.vars.get("l0"), "water")
        self.assertEqual(res.vars.get("b0"), "graphite-press")
        self.assertEqual(res.vars.get("t1"), "sharded")
        self.assertEqual(res.vars.get("t2"), "crux")
        self.assertEqual(res.vars.get("oob"), "null")
        self.assertEqual(res.vars.get("oob_neg"), "null")

    # -----------------------------------------------------------------------
    # 20. Group D: Compiled Python Intrinsics Pipeline
    # -----------------------------------------------------------------------

    def test_compiled_python_group_d_intrinsics(self):
        """Verify compiled Python program using Group D intrinsics executes accurately on JVM engine."""
        py_src = """from mlog import read, write, getlink, lookup, sensor, radar, Vars

write(100.5, cell1, 0)
val = read(cell1, 0)
b = getlink(0)
cap = sensor(cell1, '@memoryCapacity')
item0 = lookup('item', 0)
target = radar('enemy', 'any', 'any', 'distance', Vars.this, 1)
"""
        res = compile_py(py_src)
        run_res = run_with_mindustry(res.mlog)
        self.assertTrue(run_res.success, f"Execution failed: {run_res.message}")
        self.assertEqual(run_res.vars.get("val"), 100.5)
        self.assertEqual(run_res.vars.get("b"), "memory-cell")
        self.assertEqual(run_res.vars.get("cap"), 64.0)
        self.assertEqual(run_res.vars.get("item0"), "copper")
        self.assertEqual(run_res.vars.get("target"), "null")


    # -----------------------------------------------------------------------
    # 21. Group E: 'draw' & 'drawflush' Opcode Semantics in LExecutor
    # -----------------------------------------------------------------------

    def test_draw_commands_buffering(self):
        """Verify draw opcodes buffer display commands in LExecutor.graphicsBuffer."""
        mlog = """draw clear 0 0 0 0 0 0
draw color 255 128 64 255 0 0
draw stroke 2 0 0 0 0 0
draw line 10 10 50 50 0 0
draw rect 20 20 40 40 0 0
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.graphics_buffer_size, 5)

    def test_drawflush_to_display_and_clear(self):
        """Verify drawflush transfers graphics commands to LogicDisplayBuild and clears buffer."""
        mlog = """draw clear 255 0 0 0 0 0
draw color 0 255 0 255 0 0
draw rect 5 5 20 20 0 0
drawflush display1
sensor bsize display1 @bufferSize
sensor ops display1 @operations
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.graphics_buffer_size, 0)
        self.assertIn("display1", res.displays)
        self.assertEqual(res.displays["display1"]["commands"], 3)
        self.assertEqual(res.displays["display1"]["operations"], 1)
        self.assertEqual(res.vars.get("bsize"), 3.0)
        self.assertEqual(res.vars.get("ops"), 1.0)

    def test_drawflush_unlinked_target(self):
        """Verify drawflush to null or unlinked block safely clears buffer without error."""
        mlog = """draw color 255 255 255 255 0 0
draw rect 0 0 10 10 0 0
drawflush null
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.graphics_buffer_size, 0)

    # -----------------------------------------------------------------------
    # 22. Group E: 'control' Opcode Semantics in LExecutor
    # -----------------------------------------------------------------------

    def test_control_building_enabled_toggle(self):
        """Verify control opcode toggles building enabled state on switch and turret."""
        mlog = """control enabled switch1 0 0 0 0
sensor s_off switch1 @enabled
control enabled switch1 1 0 0 0
sensor s_on switch1 @enabled
control enabled duo1 0 0 0 0
sensor d_off duo1 @enabled
control enabled duo1 1 0 0 0
sensor d_on duo1 @enabled
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("s_off"), 0.0)
        self.assertEqual(res.vars.get("s_on"), 1.0)
        self.assertEqual(res.vars.get("d_off"), 0.0)
        self.assertEqual(res.vars.get("d_on"), 1.0)

    def test_control_unlinked_safe_noop(self):
        """Verify control on unlinked or null building safely no-ops without crashing."""
        mlog = """control enabled null 0 0 0 0
set ok 1
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("ok"), 1.0)

    # -----------------------------------------------------------------------
    # 23. Group E: 'ubind' Opcode Semantics in LExecutor
    # -----------------------------------------------------------------------

    def test_ubind_type_cycling_and_null(self):
        """Verify ubind binds unit types, cycles through team units, and sets null for empty types."""
        mlog = """ubind @flare
sensor u1_x @unit @x
ubind @flare
sensor u2_x @unit @x
ubind @mono
sensor u3_type @unit @type
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("u1_x"), 51.25)
        self.assertEqual(res.vars.get("u2_x"), 52.5)
        self.assertEqual(res.vars.get("u3_type"), "null")

    def test_ubind_specific_unit_object(self):
        """Verify ubind can bind directly to a specific Unit reference."""
        mlog = """ubind friendly_unit
sensor u_team @unit @team
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("u_team"), 1.0)
        self.assertEqual(res.bound_unit, "flare")

    # -----------------------------------------------------------------------
    # 24. Group E: 'ucontrol' Opcode Semantics in LExecutor
    # -----------------------------------------------------------------------

    def test_ucontrol_flag_and_within_semantics(self):
        """Verify ucontrol flag and within sub-actions execute on bound unit."""
        mlog = """ubind @flare
ucontrol flag 1234567 0 0 0 0
sensor f @unit @flag
ucontrol within 51.25 51.25 5 in_range 0
ucontrol within 0 0 5 out_range 0
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("f"), 1234567.0)
        self.assertEqual(res.vars.get("in_range"), 1.0)
        self.assertEqual(res.vars.get("out_range"), 0.0)

    def test_ucontrol_boost_stop_unbind(self):
        """Verify ucontrol boost, stop, and unbind sub-actions execute cleanly."""
        mlog = """ubind @flare
ucontrol boost 1 0 0 0 0
ucontrol stop 0 0 0 0 0
ucontrol unbind 0 0 0 0 0
set done 1
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("done"), 1.0)

    # -----------------------------------------------------------------------
    # 25. Group E: 'uradar' Opcode Semantics in LExecutor
    # -----------------------------------------------------------------------

    def test_uradar_from_bound_unit(self):
        """Verify uradar scans for enemy units from the perspective of bound unit."""
        mlog = """ubind @flare
uradar enemy any any distance 0 1 target
sensor t_type target @type
sensor t_health target @health
sensor t_team target @team
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("target"), "flare")
        self.assertEqual(res.vars.get("t_type"), "flare")
        self.assertEqual(res.vars.get("t_health"), 70.0)
        self.assertEqual(res.vars.get("t_team"), 2.0)  # Crux team

    def test_uradar_out_of_range_and_unbound(self):
        """Verify uradar returns null when enemy is out of range or no unit is bound."""
        mlog = """ubind @mono
uradar enemy any any distance 0 1 unbound_target
ubind @flare
set u far_enemy_unit
uradar enemy any any distance 0 1 far_target
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("unbound_target"), "null")
        self.assertEqual(res.vars.get("far_target"), "null")

    # -----------------------------------------------------------------------
    # 26. Group E: 'ulocate' Opcode Semantics in LExecutor
    # -----------------------------------------------------------------------

    def test_ulocate_core_spawn_and_ore(self):
        """Verify ulocate locates core building, wave spawn, and ore positions accurately."""
        mlog = """ubind @flare
ulocate building core false @copper cx cy cfound cbuild
sensor ctype cbuild @type
ulocate spawn core false @copper sx sy sfound sbuild
ulocate ore core false @copper ox oy ofound obuild
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("cfound"), 1.0)
        self.assertEqual(res.vars.get("cx"), 40.0)
        self.assertEqual(res.vars.get("cy"), 40.0)
        self.assertEqual(res.vars.get("ctype"), "core-shard")
        self.assertEqual(res.vars.get("sfound"), 1.0)
        self.assertEqual(res.vars.get("sx"), 10.0)
        self.assertEqual(res.vars.get("sy"), 10.0)
        self.assertEqual(res.vars.get("ofound"), 1.0)
        self.assertEqual(res.vars.get("ox"), 25.0)
        self.assertEqual(res.vars.get("oy"), 25.0)

    def test_ulocate_missing_target_returns_not_found(self):
        """Verify ulocate sets found=0 when searching for non-existent target."""
        mlog = """ubind @flare
ulocate building core true @copper ex ey efound ebuild
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("efound"), 0.0)
        self.assertEqual(res.vars.get("ebuild"), "null")

    def test_ulocate_tuple_unpacking_runtime_jvm(self):
        """Verify compiled Python ulocate tuple unpacking behaves accurately on real JVM engine.

        Tests target exists (core, ore), target does not exist (enemy core),
        dummy register isolation (building variable preservation), 4-variable ore unpacking,
        and output coordinates/found/building registers on Mindustry v160.7.
        """
        py_src = """from mlog import ubind, ulocate, sensor

ubind('@flare')
# Target exists: friendly core
core_x, core_y, found_core, core_build = ulocate.building("core", False)
core_type = sensor(core_build, "@type")

# Target exists: copper ore deposit with dummy building isolation
building = 999.0
ore_x, ore_y, found_ore = ulocate.ore("@copper")

# 4-variable ore unpacking: obuild receives null because ore deposit is not a building
ox4, oy4, ofound4, obuild4 = ulocate.ore("@copper")

# Target does not exist: enemy core (pre-initialize coordinates to test retention)
enemy_x = 777.0
enemy_y = 888.0
enemy_x, enemy_y, found_enemy, enemy_build = ulocate.building("core", True)
"""
        res_comp = compile_py(py_src, filename="test_unpack.py")
        res = run_with_mindustry(res_comp.mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")

        # 1. Friendly core found
        self.assertEqual(res.vars.get("found_core"), 1.0)
        self.assertEqual(res.vars.get("core_x"), 40.0)
        self.assertEqual(res.vars.get("core_y"), 40.0)
        self.assertEqual(res.vars.get("core_type"), "core-shard")

        # 2. Copper ore found with dummy building isolation
        self.assertEqual(res.vars.get("found_ore"), 1.0)
        self.assertEqual(res.vars.get("ore_x"), 25.0)
        self.assertEqual(res.vars.get("ore_y"), 25.0)
        # Verify user's 'building' variable was NOT overwritten by dummy output!
        self.assertEqual(res.vars.get("building"), 999.0)

        # 3. 4-variable ore unpacking
        self.assertEqual(res.vars.get("ofound4"), 1.0)
        self.assertEqual(res.vars.get("ox4"), 25.0)
        self.assertEqual(res.vars.get("oy4"), 25.0)
        self.assertEqual(res.vars.get("obuild4"), "null")

        # 4. Enemy core not found: coordinates retained, build is null
        self.assertEqual(res.vars.get("found_enemy"), 0.0)
        self.assertEqual(res.vars.get("enemy_x"), 777.0)
        self.assertEqual(res.vars.get("enemy_y"), 888.0)
        self.assertEqual(res.vars.get("enemy_build"), "null")

    # -----------------------------------------------------------------------
    # 27. Group E: Compiled Python Intrinsics & Namespaces Pipeline
    # -----------------------------------------------------------------------

    def test_compiled_python_group_e_intrinsics_pipeline(self):
        """Verify compiled Python program combining Group E intrinsics executes cleanly on JVM."""
        py_src = """from mlog import ubind, ucontrol, uradar, ulocate, draw, drawflush, control, sensor

ubind('@flare')
ucontrol.flag(777)
flag_val = sensor('@unit', '@flag')
ucontrol.within(51.25, 51.25, 5, is_near)

draw('color', 100, 150, 200, 255, 0, 0)
draw('rect', 10, 10, 30, 30, 0, 0)
drawflush(display1)

control('enabled', switch1, 0, 0, 0, 0)
sw_en = sensor(switch1, '@enabled')

target = uradar('enemy', 'any', 'any', 'distance', 1)
target_hp = sensor(target, '@health')

ulocate('building', 'core', 0, '@copper', cx, cy, cfound, cbuild)
"""
        res = compile_py(py_src)
        run_res = run_with_mindustry(res.mlog)
        self.assertTrue(run_res.success, f"Execution failed: {run_res.message}")
        self.assertEqual(run_res.vars.get("flag_val"), 777.0)
        self.assertEqual(run_res.vars.get("is_near"), 1.0)
        self.assertEqual(run_res.vars.get("sw_en"), 0.0)
        self.assertEqual(run_res.vars.get("target_hp"), 70.0)
        self.assertEqual(run_res.vars.get("cfound"), 1.0)
        self.assertEqual(run_res.vars.get("cx"), 40.0)
        self.assertEqual(run_res.vars.get("cy"), 40.0)
        self.assertEqual(run_res.displays.get("display1", {}).get("commands"), 2)
        self.assertEqual(run_res.displays.get("display1", {}).get("operations"), 1)


    # -----------------------------------------------------------------------
    # 28. Group A Deep Verification: stop, end, jump, and op Edge Cases
    # -----------------------------------------------------------------------

    def test_stop_instruction_terminates_execution(self):
        """Verify 'stop' immediately halts instruction execution and subsequent instructions are skipped."""
        mlog = """
set a 10
set b 5
stop
set a 99
set b 99
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("a"), 10.0)
        self.assertEqual(res.vars.get("b"), 5.0)

    def test_end_instruction_resets_program_counter(self):
        """Verify 'end' terminates current cycle pass by setting counter = instructions.length."""
        mlog = """
set before_end 1
end
set after_end 1
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("before_end"), 1.0)
        # 'after_end' is registered by LAssembler but never executed by LExecutor due to 'end', remaining uninitialized 'null'
        self.assertEqual(res.vars.get("after_end"), "null")

    def test_jump_conditional_operators(self):
        """Verify jump evaluates condition branches accurately on JVM."""
        mlog = """
set x 5
jump 4 equal x 5
set j1 0
jump 5 always 0 0
set j1 1

jump 8 notEqual x 5
set j2 1
jump 9 always 0 0
set j2 0

jump 12 lessThan x 10
set j3 0
jump 13 always 0 0
set j3 1

jump 16 greaterThan x 2
set j4 0
jump 17 always 0 0
set j4 1
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        self.assertEqual(res.vars.get("j1"), 1.0)
        self.assertEqual(res.vars.get("j2"), 1.0)
        self.assertEqual(res.vars.get("j3"), 1.0)
        self.assertEqual(res.vars.get("j4"), 1.0)

    def test_op_division_by_zero_and_special_ops(self):
        """Verify op handles division by zero (returning null in Mindustry) and math functions."""
        mlog = """
op div div_zero 10 0
op idiv idiv_zero 10 0
op mod mod_zero 10 0
op min m1 15 25
op max m2 15 25
op abs a1 -42 0
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Execution failed: {res.message}")
        # In Mindustry LVar.setnum: invalid(NaN/Infinity) sets objval = null (isobj = true)
        self.assertEqual(res.vars.get("div_zero"), "null")
        self.assertEqual(res.vars.get("idiv_zero"), "null")
        self.assertEqual(res.vars.get("mod_zero"), "null")
        self.assertEqual(res.vars.get("m1"), 15.0)
        self.assertEqual(res.vars.get("m2"), 25.0)
        self.assertEqual(res.vars.get("a1"), 42.0)

    # -----------------------------------------------------------------------
    # Group C: Timing & Rate Semantics in LExecutor (wait & setrate)
    # -----------------------------------------------------------------------

    def test_setrate_processor_clamping_and_ipt_mutation(self):
        """Verify setrate IPT clamp bounds across processor types and @ipt variable mutation."""
        # 1. Micro processor: instructionsPerTick=2, privileged=false -> clamped to [1, 2]
        mlog_micro = """
#processor: micro
set init_ipt @ipt
setrate 10
set max_clamped @ipt
setrate 1
set min_valid @ipt
setrate -5
set min_clamped @ipt
"""
        res_micro = run_with_mindustry(mlog_micro)
        self.assertTrue(res_micro.success, f"Micro processor setrate failed: {res_micro.message}")
        self.assertEqual(res_micro.vars.get("init_ipt"), 2.0)
        self.assertEqual(res_micro.vars.get("max_clamped"), 2.0)
        self.assertEqual(res_micro.vars.get("min_valid"), 1.0)
        self.assertEqual(res_micro.vars.get("min_clamped"), 1.0)
        self.assertEqual(res_micro.ipt, 1)

        # 2. Logic processor: instructionsPerTick=8, privileged=false -> clamped to [1, 8]
        mlog_logic = """
set init_ipt @ipt
setrate 50
set max_clamped @ipt
setrate 4
set mid_valid @ipt
setrate 0
set min_clamped @ipt
"""
        res_logic = run_with_mindustry(mlog_logic)
        self.assertTrue(res_logic.success, f"Logic processor setrate failed: {res_logic.message}")
        self.assertEqual(res_logic.vars.get("init_ipt"), 8.0)
        self.assertEqual(res_logic.vars.get("max_clamped"), 8.0)
        self.assertEqual(res_logic.vars.get("mid_valid"), 4.0)
        self.assertEqual(res_logic.vars.get("min_clamped"), 1.0)
        self.assertEqual(res_logic.ipt, 1)

        # 3. Hyper processor: instructionsPerTick=25, privileged=false -> clamped to [1, 25]
        mlog_hyper = """
#processor: hyper
set init_ipt @ipt
setrate 100
set max_clamped @ipt
setrate 15
set mid_valid @ipt
"""
        res_hyper = run_with_mindustry(mlog_hyper)
        self.assertTrue(res_hyper.success, f"Hyper processor setrate failed: {res_hyper.message}")
        self.assertEqual(res_hyper.vars.get("init_ipt"), 25.0)
        self.assertEqual(res_hyper.vars.get("max_clamped"), 25.0)
        self.assertEqual(res_hyper.vars.get("mid_valid"), 15.0)
        self.assertEqual(res_hyper.ipt, 15)

        # 4. World processor: privileged=true, maxInstructionsPerTick=1000 -> clamped to [1, 1000]
        mlog_world = """
#processor: world
set init_ipt @ipt
setrate 500
set mid_rate @ipt
setrate 9999
set max_rate @ipt
"""
        res_world = run_with_mindustry(mlog_world)
        self.assertTrue(res_world.success, f"World processor setrate failed: {res_world.message}")
        self.assertEqual(res_world.vars.get("init_ipt"), 8.0)
        self.assertEqual(res_world.vars.get("mid_rate"), 500.0)
        self.assertEqual(res_world.vars.get("max_rate"), 1000.0)
        self.assertEqual(res_world.ipt, 1000)

    def test_setrate_boundary_and_type_coercion(self):
        """Verify setrate truncates fractional rates and coerces objects and null cleanly."""
        mlog = """
setrate 5.8
set rate_float @ipt
setrate @copper
set rate_obj @ipt
setrate null
set rate_null @ipt
set my_rate 3
setrate my_rate
set rate_var @ipt
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Setrate coercion failed: {res.message}")
        # In Mindustry SetRateI: amount.numi() casts (int)num()
        self.assertEqual(res.vars.get("rate_float"), 5.0)
        # @copper is non-null object -> num() == 1.0 -> numi() == 1 -> clamped to 1
        self.assertEqual(res.vars.get("rate_obj"), 1.0)
        # null object -> num() == 0.0 -> numi() == 0 -> clamped to min IPT 1
        self.assertEqual(res.vars.get("rate_null"), 1.0)
        # dynamic variable
        self.assertEqual(res.vars.get("rate_var"), 3.0)
        self.assertEqual(res.ipt, 3)

    def test_setrate_scheduler_accumulator_pacing(self):
        """Verify setrate directly paces the instruction scheduler across ticks."""
        # Baseline on micro processor (IPT=2): 6 instructions span exactly 3 ticks (2 inst/tick)
        mlog_baseline = """
#processor: micro
set a @tick
set b @tick
set c @tick
set d @tick
set e @tick
set f @tick
"""
        res_base = run_with_mindustry(mlog_baseline)
        self.assertTrue(res_base.success, f"Micro baseline failed: {res_base.message}")
        self.assertEqual(res_base.vars.get("a"), 0.0)
        self.assertEqual(res_base.vars.get("b"), 0.0)
        self.assertEqual(res_base.vars.get("c"), 1.0)
        self.assertEqual(res_base.vars.get("d"), 1.0)
        self.assertEqual(res_base.vars.get("e"), 2.0)
        self.assertEqual(res_base.vars.get("f"), 2.0)
        self.assertEqual(res_base.ticks, 3)

        # Dynamic rate decrease: dropping rate to 1 forces subsequent instructions to 1 inst/tick
        mlog_dynamic = """
#processor: micro
set a @tick
setrate 1
set c @tick
set d @tick
"""
        res_dyn = run_with_mindustry(mlog_dynamic)
        self.assertTrue(res_dyn.success, f"Micro dynamic rate failed: {res_dyn.message}")
        self.assertEqual(res_dyn.vars.get("a"), 0.0)
        self.assertEqual(res_dyn.vars.get("c"), 1.0)
        self.assertEqual(res_dyn.vars.get("d"), 2.0)
        self.assertEqual(res_dyn.ticks, 3)

    def test_wait_tick_yield_and_negative_duration(self):
        """Verify wait <= 0 triggers yield without decrementing counter, yielding exactly 1 tick."""
        mlog = """
set t0 @tick
wait 0
set t1 @tick
wait -5
set t2 @tick
wait null
set t3 @tick
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Wait yield failed: {res.message}")
        self.assertEqual(res.vars.get("t0"), 0.0)
        self.assertEqual(res.vars.get("t1"), 1.0)
        self.assertEqual(res.vars.get("t2"), 2.0)
        self.assertEqual(res.vars.get("t3"), 3.0)
        self.assertEqual(res.ticks, 4)

    def test_wait_exact_duration_and_virtual_time_progress(self):
        """Verify wait advances virtual time by ceil(duration * 60) ticks and updates GlobalVars."""
        # 1. Wait durations: 0.05s (3 ticks), 0.1s (6 ticks), 0.5s (30 ticks)
        mlog = """
set start_tick @tick
wait 0.05
set tick_after_005 @tick
wait 0.1
set tick_after_01 @tick
set cur_time @time
set cur_sec @second
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"Wait duration failed: {res.message}")
        self.assertEqual(res.vars.get("start_tick"), 0.0)
        self.assertEqual(res.vars.get("tick_after_005"), 3.0)
        self.assertEqual(res.vars.get("tick_after_01"), 9.0)
        # @time = tick / 60.0 * 1000.0 -> 9 / 60 * 1000 = 150.0 ms
        self.assertEqual(res.vars.get("cur_time"), 150.0)
        # @second = tick / 60.0 -> 9 / 60 = 0.15 s
        self.assertAlmostEqual(res.vars.get("cur_sec"), 0.15, places=5)

        # 2. Object wait duration: @copper has num() == 1.0, so wait @copper pauses for 1.0s.
        # Due to 32-bit float accumulation in WaitI (curTime += 1/60f), tick 60 reaches
        # 0.9999997f < 1.0f, triggering completion on tick 61 (61.0 ticks total).
        mlog_obj = """
set t0 @tick
wait @copper
set t1 @tick
"""
        res_obj = run_with_mindustry(mlog_obj)
        self.assertTrue(res_obj.success, f"Wait object failed: {res_obj.message}")
        self.assertEqual(res_obj.vars.get("t0"), 0.0)
        self.assertEqual(res_obj.vars.get("t1"), 61.0)

    def test_wait_independence_from_ipt_and_loop_lifecycle(self):
        """Verify wait duration is independent of IPT and resets curTime properly across iterations."""
        # 1. Independence from processor rate: wait 0.1 takes 6 ticks at IPT=1 and at IPT=8
        mlog_rate1 = """
setrate 1
set t0 @tick
wait 0.1
set t1 @tick
op sub elapsed t1 t0
"""
        res_rate1 = run_with_mindustry(mlog_rate1)
        self.assertTrue(res_rate1.success, f"Wait at rate 1 failed: {res_rate1.message}")
        self.assertEqual(res_rate1.vars.get("elapsed"), 6.0)

        mlog_rate8 = """
setrate 8
set t0 @tick
wait 0.1
set t1 @tick
op sub elapsed t1 t0
"""
        res_rate8 = run_with_mindustry(mlog_rate8)
        self.assertTrue(res_rate8.success, f"Wait at rate 8 failed: {res_rate8.message}")
        self.assertEqual(res_rate8.vars.get("elapsed"), 6.0)

        # 2. Consecutive wait instructions
        mlog_consec = """
set t0 @tick
wait 0.05
set t1 @tick
wait 0.05
set t2 @tick
"""
        res_consec = run_with_mindustry(mlog_consec)
        self.assertTrue(res_consec.success, f"Consecutive wait failed: {res_consec.message}")
        self.assertEqual(res_consec.vars.get("t1") - res_consec.vars.get("t0"), 3.0)
        self.assertEqual(res_consec.vars.get("t2") - res_consec.vars.get("t1"), 3.0)

        # 3. Looped wait instruction: resets curTime on completion, taking 3 * 3 = 9 ticks
        mlog_loop = """
set i 0
set t0 @tick
loop:
wait 0.05
op add i i 1
jump 2 lessThan i 3
set t_end @tick
op sub total_ticks t_end t0
"""
        res_loop = run_with_mindustry(mlog_loop)
        self.assertTrue(res_loop.success, f"Looped wait failed: {res_loop.message}")
        self.assertEqual(res_loop.vars.get("i"), 3.0)
        self.assertEqual(res_loop.vars.get("total_ticks"), 9.0)

    def test_compiled_dsl_timing_and_rate_roundtrip(self):
        """Verify compiled Python DSL using setrate and wait executes accurately and roundtrips."""
        dsl_code = """from mlog import Vars, setrate, wait

setrate(4)
wait(0.1)
wait()
"""
        compile_res = compile_py(dsl_code)
        self.assertIn("setrate 4", compile_res.mlog)
        self.assertIn("wait 0.1", compile_res.mlog)
        self.assertIn("wait 0.5", compile_res.mlog)

        # Execute compiled code on real Mindustry engine
        res = run_with_mindustry(compile_res.mlog)
        self.assertTrue(res.success, f"Compiled timing execution failed: {res.message}")
        self.assertEqual(res.ipt, 4)
        # 6 ticks (wait 0.1) + 30 ticks (wait 0.5) + 1 final tick = 37 ticks
        self.assertEqual(res.ticks, 37)

        # Decompile back and verify roundtrip stability
        decompiled = decompile(compile_res.mlog)
        self.assertIn("setrate(4)", decompiled)
        self.assertIn("wait(0.1)", decompiled)
        self.assertIn("wait(0.5)", decompiled)

    # -----------------------------------------------------------------------
    # Group D: World State & Sensors (sensor, getlink, getblock)
    # -----------------------------------------------------------------------

    def test_getlink_boundary_and_null_semantics(self):
        """Verify getlink bounds checking, negative and overflow null return, and @links count."""
        # 1. Linked buildings: index 0 -> cell, index 1 -> duo
        mlog_links = """
#link: cell1, duo1
getlink l0 0
getlink l1 1
getlink l_neg -1
getlink l_neg_large -99
getlink l_at_len 2
getlink l_overflow 100
getlink l_float 1.9
set total_links @links
"""
        res = run_with_mindustry(mlog_links)
        self.assertTrue(res.success, f"getlink execution failed: {res.message}")
        self.assertEqual(res.vars.get("l0"), "memory-cell")
        self.assertEqual(res.vars.get("l1"), "duo")
        # In Mindustry GetLinkI: address >= 0 && address < exec.links.length ? links[address] : null
        self.assertEqual(res.vars.get("l_neg"), "null")
        self.assertEqual(res.vars.get("l_neg_large"), "null")
        self.assertEqual(res.vars.get("l_at_len"), "null")
        self.assertEqual(res.vars.get("l_overflow"), "null")
        # index.numi() truncates 1.9 -> 1, reading index 1
        self.assertEqual(res.vars.get("l_float"), "duo")
        self.assertEqual(res.vars.get("total_links"), 2.0)

        # 2. Processor without links: exec.links has length 0, all lookups yield null
        mlog_empty = """
getlink l0 0
getlink l1 1
set total_links @links
"""
        res_empty = run_with_mindustry(mlog_empty)
        self.assertTrue(res_empty.success, f"getlink on empty links failed: {res_empty.message}")
        self.assertEqual(res_empty.vars.get("l0"), "null")
        self.assertEqual(res_empty.vars.get("l1"), "null")
        self.assertEqual(res_empty.vars.get("total_links"), 0.0)

    def test_sensor_numeric_and_object_properties(self):
        """Verify sensor retrieves numeric values and object references from buildings and units."""
        mlog = """
#link: cell1, enemy_duo1, bank1
sensor hp cell1 @health
sensor mhp cell1 @maxHealth
sensor sz_cell cell1 @size
sensor sz_duo enemy_duo1 @size
sensor sz_bank bank1 @size
sensor t_cell cell1 @type
sensor t_duo enemy_duo1 @type
sensor t_bank bank1 @type
sensor tm_sharded cell1 @team
sensor tm_crux enemy_duo1 @team
sensor x_cell cell1 @x
sensor y_cell cell1 @y
sensor u_hp friendly_unit @health
sensor u_type friendly_unit @type
sensor str_size "Hello Mindustry" @size
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"sensor execution failed: {res.message}")
        self.assertEqual(res.vars.get("hp"), 1.0)
        self.assertEqual(res.vars.get("mhp"), 1.0)
        # Block footprint sizes: cell1 is 1x1, duo1 is 1x1, bank1 is 2x2
        self.assertEqual(res.vars.get("sz_cell"), 1.0)
        self.assertEqual(res.vars.get("sz_duo"), 1.0)
        self.assertEqual(res.vars.get("sz_bank"), 2.0)
        self.assertEqual(res.vars.get("t_cell"), "memory-cell")
        self.assertEqual(res.vars.get("t_duo"), "duo")
        self.assertEqual(res.vars.get("t_bank"), "memory-bank")
        # Teams: Team.sharded.id = 1, Team.crux.id = 2
        self.assertEqual(res.vars.get("tm_sharded"), 1.0)
        self.assertEqual(res.vars.get("tm_crux"), 2.0)
        # Unit sensing
        self.assertEqual(res.vars.get("u_type"), "flare")
        # CharSequence length sensing: LAccess.size on CharSequence
        self.assertEqual(res.vars.get("str_size"), 15.0)

    def test_sensor_null_and_invalid_target_semantics(self):
        """Verify sensor edge cases: target == null && sense == @dead returns 1, others return null."""
        mlog = """
#link: cell1, dead_cell2
sensor dead_null null @dead
sensor hp_null null @health
sensor type_null null @type
sensor x_null null @x
sensor dead_live cell1 @dead
sensor dead_dead dead_cell2 @dead
sensor hp_num 42 @health
sensor cop_cell cell1 @copper
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"sensor null edge cases failed: {res.message}")
        # In Mindustry SenseI: if (target == null && sense == LAccess.dead) return 1;
        self.assertEqual(res.vars.get("dead_null"), 1.0)
        # Sensed other properties on null target return null
        self.assertEqual(res.vars.get("hp_null"), "null")
        self.assertEqual(res.vars.get("type_null"), "null")
        self.assertEqual(res.vars.get("x_null"), "null")
        # Live vs dead buildings
        self.assertEqual(res.vars.get("dead_live"), 0.0)
        self.assertEqual(res.vars.get("dead_dead"), 1.0)
        # Non-senseable literal (number 42) returns null
        self.assertEqual(res.vars.get("hp_num"), "null")
        # Sensing an item on a block with no item inventory returns null (Double.NaN coerced to null)
        self.assertEqual(res.vars.get("cop_cell"), "null")

    def test_sensor_privileged_property_access_control(self):
        """Verify privileged sensor properties (@cameraX, @cameraY) are masked on non-privileged processors."""
        # 1. Standard processor: privileged LAccess properties return null
        mlog_std = """
#processor: logic
#link: cell1
sensor cam_x cell1 @cameraX
sensor cam_y cell1 @cameraY
"""
        res_std = run_with_mindustry(mlog_std)
        self.assertTrue(res_std.success, f"Standard sensor privileged failed: {res_std.message}")
        self.assertEqual(res_std.vars.get("cam_x"), "null")
        self.assertEqual(res_std.vars.get("cam_y"), "null")

        # 2. World processor: privileged LAccess properties are accessible and return numeric values
        mlog_world = """
#processor: world
#link: cell1
sensor cam_x cell1 @cameraX
sensor cam_y cell1 @cameraY
"""
        res_world = run_with_mindustry(mlog_world)
        self.assertTrue(res_world.success, f"World processor sensor privileged failed: {res_world.message}")
        self.assertEqual(res_world.vars.get("cam_x"), 0.0)
        self.assertEqual(res_world.vars.get("cam_y"), 0.0)

    def test_getblock_world_processor_execution(self):
        """Verify getblock reads floor, ore, block, and building layers accurately on world processors."""
        mlog = """
#processor: world
#link: cell1
getblock floor f_ore 25 25
getblock ore o_ore 25 25
getblock block b_proc 50 50
getblock building bld_proc 50 50
getblock block b_cell 51 50
getblock building bld_cell 51 50
getblock floor f_oob -10 -10
getblock ore o_round 24.8 25.2
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"getblock execution failed: {res.message}")
        self.assertEqual(res.vars.get("f_ore"), "stone")
        self.assertEqual(res.vars.get("o_ore"), "ore-copper")
        self.assertEqual(res.vars.get("b_proc"), "world-processor")
        self.assertEqual(res.vars.get("bld_proc"), "world-processor")
        self.assertEqual(res.vars.get("b_cell"), "memory-cell")
        self.assertEqual(res.vars.get("bld_cell"), "memory-cell")
        # Out-of-bounds tile returns null
        self.assertEqual(res.vars.get("f_oob"), "null")
        # Floating point coordinates round to nearest tile (24.8 -> 25, 25.2 -> 25)
        self.assertEqual(res.vars.get("o_round"), "ore-copper")

    def test_getblock_standard_processor_rejection(self):
        """Verify getblock is rejected by Mindustry LParser as InvalidStatement on non-privileged processors."""
        mlog = """
#processor: logic
getblock floor f_ore 25 25
"""
        res = run_with_mindustry(mlog)
        self.assertFalse(res.success, "Standard processor should reject privileged getblock opcode")
        self.assertIn("rejected statement as InvalidStatement", res.message)

    def test_compiled_dsl_sensors_and_links_roundtrip(self):
        """Verify Python DSL getlink and sensor compile, execute on engine, and roundtrip cleanly."""
        dsl_code = """from mlog import SensorProperty, getlink, sensor

cell = getlink(0)
hp = sensor(cell, SensorProperty.HEALTH)
sensor(mhp, cell, "@maxHealth")
"""
        compile_res = compile_py(dsl_code)
        self.assertIn("getlink cell 0", compile_res.mlog)
        self.assertIn("sensor hp cell @health", compile_res.mlog)
        self.assertIn("sensor mhp cell @maxHealth", compile_res.mlog)

        # Inject link pragma for execution against real engine
        exec_mlog = "#link: cell1\n" + compile_res.mlog
        res = run_with_mindustry(exec_mlog)
        self.assertTrue(res.success, f"Compiled sensor/getlink execution failed: {res.message}")
        self.assertEqual(res.vars.get("hp"), 1.0)
        self.assertEqual(res.vars.get("mhp"), 1.0)

        # Decompile back and verify roundtrip stability
        decompiled = decompile(compile_res.mlog)
        self.assertIn("cell = getlink(0)", decompiled)
        self.assertIn("sensor(cell, '@health')", decompiled)
        self.assertIn("sensor(cell, '@maxHealth')", decompiled)

    # -----------------------------------------------------------------------
    # Group E: Display Graphics & Building Control (draw, drawflush, control)
    # -----------------------------------------------------------------------

    def test_draw_commands_and_buffer_cap_256(self):
        """Verify draw subcommands accumulate in graphicsBuffer and cap strictly at maxGraphicsBuffer = 256."""
        # 1. Verify standard draw shapes and transformations accumulate in graphicsBuffer
        mlog_shapes = """
draw clear 10 20 30 0 0 0
draw color 255 128 64 255 0 0
draw stroke 2 0 0 0 0 0
draw line 0 0 40 40 0 0
draw rect 5 5 20 30 0 0
draw lineRect 10 10 30 40 0 0
draw poly 20 20 6 15 45 0
draw linePoly 30 30 8 10 0 0
draw triangle 0 0 10 20 20 0
draw translate 5 5 0 0 0 0
draw scale 2 2 0 0 0 0
draw rotate 90 0 0 0 0 0
draw reset 0 0 0 0 0 0
"""
        res_shapes = run_with_mindustry(mlog_shapes)
        self.assertTrue(res_shapes.success, f"draw shapes execution failed: {res_shapes.message}")
        self.assertEqual(res_shapes.graphics_buffer_size, 13)

        # 2. Verify buffer capacity caps at exactly 256 items and silently drops overflow
        mlog_cap = "draw clear 0 0 0 0 0 0\n" * 300
        res_cap = run_with_mindustry(mlog_cap)
        self.assertTrue(res_cap.success, f"draw cap execution failed: {res_cap.message}")
        self.assertEqual(res_cap.graphics_buffer_size, 256)

    def test_draw_col_colorpack_unpacking(self):
        """Verify draw col unpacks packed double bits into RGBA color command."""
        mlog = """
#links: display1
packcolor packed_col 1 0 0 1
draw col packed_col 0 0 0 0 0
drawflush display1
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"draw col execution failed: {res.message}")
        self.assertEqual(res.displays.get("display1", {}).get("commands"), 1)
        self.assertEqual(res.displays.get("display1", {}).get("operations"), 1)
        self.assertEqual(res.graphics_buffer_size, 0)

    def test_draw_print_text_buffer_integration(self):
        """Verify draw print reads textBuffer, generates per-glyph display commands, and clears textBuffer."""
        mlog = """
#links: display1
print "HI"
draw print 10 20 @center 0 0 0
drawflush display1
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"draw print execution failed: {res.message}")
        # textBuffer was consumed and reset
        self.assertEqual(res.text_buffer, "")
        # "HI" has 2 glyphs, flushed into display1
        self.assertEqual(res.displays.get("display1", {}).get("commands"), 2)
        self.assertEqual(res.displays.get("display1", {}).get("operations"), 1)
        self.assertEqual(res.graphics_buffer_size, 0)

    def test_drawflush_clears_buffer_unconditionally(self):
        """Verify drawflush always clears graphicsBuffer, even on null, non-display, or enemy display targets."""
        # 1. Flush to null clears graphicsBuffer
        mlog_null = """
draw clear 0 0 0 0 0 0
draw color 255 0 0 255 0 0
drawflush null
"""
        res_null = run_with_mindustry(mlog_null)
        self.assertTrue(res_null.success, f"drawflush null failed: {res_null.message}")
        self.assertEqual(res_null.graphics_buffer_size, 0)

        # 2. Flush to non-display block (cell1) clears graphicsBuffer without error
        mlog_cell = """
#links: cell1
draw clear 0 0 0 0 0 0
draw color 0 255 0 255 0 0
drawflush cell1
"""
        res_cell = run_with_mindustry(mlog_cell)
        self.assertTrue(res_cell.success, f"drawflush cell1 failed: {res_cell.message}")
        self.assertEqual(res_cell.graphics_buffer_size, 0)

        # 3. Standard processor flushing to enemy display: rejected by d.drawable(exec) but buffer cleared
        mlog_enemy_std = """
#processor: logic
#links: enemy_display1
draw clear 0 0 0 0 0 0
draw color 0 0 255 255 0 0
drawflush enemy_display1
"""
        res_enemy_std = run_with_mindustry(mlog_enemy_std)
        self.assertTrue(res_enemy_std.success, f"drawflush enemy_display1 failed: {res_enemy_std.message}")
        self.assertEqual(res_enemy_std.graphics_buffer_size, 0)
        self.assertEqual(res_enemy_std.displays.get("enemy_display1", {}).get("commands", 0), 0)
        self.assertEqual(res_enemy_std.displays.get("enemy_display1", {}).get("operations", 0), 0)

        # 4. World processor flushing to enemy display: permitted (exec.privileged) and commands transferred
        mlog_enemy_world = """
#processor: world
#links: enemy_display1
draw clear 0 0 0 0 0 0
draw color 0 0 255 255 0 0
drawflush enemy_display1
"""
        res_enemy_world = run_with_mindustry(mlog_enemy_world)
        self.assertTrue(res_enemy_world.success, f"drawflush enemy_display1 world failed: {res_enemy_world.message}")
        self.assertEqual(res_enemy_world.graphics_buffer_size, 0)
        self.assertEqual(res_enemy_world.displays.get("enemy_display1", {}).get("commands"), 2)
        self.assertEqual(res_enemy_world.displays.get("enemy_display1", {}).get("operations"), 1)

    def test_control_switch_enabled_and_turret(self):
        """Verify control modifies enabled state on friendly SwitchBlock and handles turret safely."""
        mlog = """
#links: switch1, duo1
sensor s_init switch1 @enabled
control enabled switch1 0 0 0 0
sensor s_disabled switch1 @enabled
control enabled switch1 1 0 0 0
sensor s_re_enabled switch1 @enabled
control shoot duo1 100 200 1 0
control enabled null 0 0 0 0
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"control execution failed: {res.message}")
        self.assertEqual(res.vars.get("s_init"), 1.0)
        self.assertEqual(res.vars.get("s_disabled"), 0.0)
        self.assertEqual(res.vars.get("s_re_enabled"), 1.0)

    def test_control_team_isolation_standard_vs_privileged(self):
        """Verify standard processor cannot control enemy building while world processor can."""
        # 1. Standard processor: control on enemy building is rejected by validLink (team check)
        mlog_std = """
#processor: logic
#links: enemy_switch1
sensor s_before enemy_switch1 @enabled
control enabled enemy_switch1 0 0 0 0
sensor s_after enemy_switch1 @enabled
"""
        res_std = run_with_mindustry(mlog_std)
        self.assertTrue(res_std.success, f"standard control test failed: {res_std.message}")
        self.assertEqual(res_std.vars.get("s_before"), 1.0)
        self.assertEqual(res_std.vars.get("s_after"), 1.0)

        # 2. World processor: control bypasses team check
        mlog_world = """
#processor: world
#links: enemy_switch1
sensor s_before enemy_switch1 @enabled
control enabled enemy_switch1 0 0 0 0
sensor s_after enemy_switch1 @enabled
"""
        res_world = run_with_mindustry(mlog_world)
        self.assertTrue(res_world.success, f"world control test failed: {res_world.message}")
        self.assertEqual(res_world.vars.get("s_before"), 1.0)
        self.assertEqual(res_world.vars.get("s_after"), 0.0)

    def test_compiled_dsl_group_e_roundtrip(self):
        """Verify Python DSL draw, drawflush, control compile to bytecode and roundtrip cleanly."""
        dsl_code = """from mlog import ControlProperty, control, draw, drawflush

draw.clear(0, 0, 0)
draw.color(255, 255, 255, 128)
draw.stroke(2)
draw.line(0, 0, 80, 80)
draw.rect(10, 10, 20, 20)
drawflush(display1)
control(ControlProperty.ENABLED, switch1, 0)
"""
        compile_res = compile_py(dsl_code)
        self.assertIn("draw clear 0 0 0 0 0 0", compile_res.mlog)
        self.assertIn("draw color 255 255 255 128 0 0", compile_res.mlog)
        self.assertIn("draw stroke 2 0 0 0 0 0", compile_res.mlog)
        self.assertIn("draw line 0 0 80 80 0 0", compile_res.mlog)
        self.assertIn("draw rect 10 10 20 20 0 0", compile_res.mlog)
        self.assertIn("drawflush display1", compile_res.mlog)
        self.assertIn("control enabled switch1 0 0 0 0", compile_res.mlog)

        # Inject links and execute on real Mindustry engine
        exec_mlog = "#links: display1, switch1\n" + compile_res.mlog
        res = run_with_mindustry(exec_mlog)
        self.assertTrue(res.success, f"Compiled Group E execution failed: {res.message}")
        self.assertEqual(res.displays.get("display1", {}).get("commands"), 5)
        self.assertEqual(res.displays.get("display1", {}).get("operations"), 1)
        self.assertEqual(res.graphics_buffer_size, 0)

        # Roundtrip back via decompiler
        decompiled = decompile(compile_res.mlog)
        self.assertIn('draw("clear", 0, 0, 0, 0, 0, 0)', decompiled)
        self.assertIn('draw("color", 255, 255, 255, 128, 0, 0)', decompiled)
        self.assertIn('drawflush("display1")', decompiled)
        self.assertIn('control("enabled", "switch1", 0, 0, 0, 0)', decompiled)

    # -----------------------------------------------------------------------
    # Group F: Unit Binding & Radar/Locate (ubind, uradar, ulocate)
    # -----------------------------------------------------------------------

    def test_ubind_cycling_and_state(self):
        """Verify ubind binds unit types in round-robin order and updates @unit state."""
        mlog = """
ubind @flare
sensor u1 @unit @type
sensor x1 @unit @x
ubind @flare
sensor u2 @unit @type
sensor x2 @unit @x
ubind @flare
sensor u3 @unit @type
sensor x3 @unit @x
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"ubind cycling failed: {res.message}")
        self.assertEqual(res.vars.get("u1"), "flare")
        self.assertEqual(res.vars.get("u2"), "flare")
        self.assertEqual(res.vars.get("u3"), "flare")
        # Round-robin between unit 1 (51.25) and unit 2 (52.5)
        self.assertEqual(res.vars.get("x1"), 51.25)
        self.assertEqual(res.vars.get("x2"), 52.5)
        self.assertEqual(res.vars.get("x3"), 51.25)
        self.assertEqual(res.bound_unit, "flare")

    def test_ubind_invalid_and_privileged_access(self):
        """Verify ubind resets @unit on invalid/empty types and enforces team isolation on direct unit bind."""
        # 1. Non-existent unit type and non-unit values reset @unit to null
        mlog_invalid = """
ubind @flare
sensor u_init @unit @type
ubind @mega
sensor u_empty @unit @type
ubind 0
sensor u_num @unit @type
ubind @copper
sensor u_item @unit @type
"""
        res_inv = run_with_mindustry(mlog_invalid)
        self.assertTrue(res_inv.success, f"invalid ubind test failed: {res_inv.message}")
        self.assertEqual(res_inv.vars.get("u_init"), "flare")
        self.assertEqual(res_inv.vars.get("u_empty"), "null")
        self.assertEqual(res_inv.vars.get("u_num"), "null")
        self.assertEqual(res_inv.vars.get("u_item"), "null")
        self.assertIsNone(res_inv.bound_unit)

        # 2. Standard processor cannot directly bind enemy unit object
        mlog_enemy_std = """
# near_enemy_unit
ubind enemy_unit
sensor u_std @unit @type
"""
        res_std = run_with_mindustry(mlog_enemy_std)
        self.assertTrue(res_std.success, f"standard enemy ubind failed: {res_std.message}")
        self.assertEqual(res_std.vars.get("u_std"), "null")
        self.assertIsNone(res_std.bound_unit)

        # 3. World processor can directly bind enemy unit object
        mlog_enemy_world = """
#processor: world
# near_enemy_unit
ubind enemy_unit
sensor u_world @unit @type
"""
        res_world = run_with_mindustry(mlog_enemy_world)
        self.assertTrue(res_world.success, f"world enemy ubind failed: {res_world.message}")
        self.assertEqual(res_world.vars.get("u_world"), "flare")
        self.assertEqual(res_world.bound_unit, "flare")

    def test_uradar_filters_and_empty_target(self):
        """Verify uradar filtering by target criteria and null safety when unbound or out of range."""
        # 1. Target filters: flying matches enemy flare, ground does not
        mlog_filter = """
ubind @flare
uradar enemy ground any distance 0 1 out_ground
uradar enemy flying any distance 0 1 out_flying
sensor t_team out_flying @team
"""
        res_filter = run_with_mindustry(mlog_filter)
        self.assertTrue(res_filter.success, f"uradar filter failed: {res_filter.message}")
        self.assertEqual(res_filter.vars.get("out_ground"), "null")
        self.assertEqual(res_filter.vars.get("out_flying"), "flare")
        self.assertEqual(res_filter.vars.get("t_team"), 2.0)  # Team.crux

        # 2. Calling uradar with no bound unit returns null
        mlog_unbound = """
ubind @mega
uradar enemy any any distance 0 1 out_unbound
"""
        res_unbound = run_with_mindustry(mlog_unbound)
        self.assertTrue(res_unbound.success, f"uradar unbound failed: {res_unbound.message}")
        self.assertEqual(res_unbound.vars.get("out_unbound"), "null")

        # 3. Enemy out of weapon range (far_enemy_unit at +500 tiles) returns null
        mlog_out_of_range = """
# far_enemy_unit
ubind @flare
uradar enemy any any distance 0 1 out_far
"""
        res_oor = run_with_mindustry(mlog_out_of_range)
        self.assertTrue(res_oor.success, f"uradar out of range failed: {res_oor.message}")
        self.assertEqual(res_oor.vars.get("out_far"), "null")

    def test_uradar_sorting_and_tie_breaking(self):
        """Verify uradar sorting by distance and health across sort directions and tie-breaking."""
        # 1. Distance and health sorting with two distinct enemy units in range
        mlog_sort = """
# near_enemy_unit, mid_enemy_unit, damaged_enemy
ubind @flare
uradar enemy any any distance 0 1 closest
sensor d_closest closest @x
uradar enemy any any distance 0 0 farthest
sensor d_farthest farthest @x
uradar enemy any any health 0 1 max_hp
sensor hp_max max_hp @health
uradar enemy any any health 0 0 min_hp
sensor hp_min min_hp @health
"""
        res_sort = run_with_mindustry(mlog_sort)
        self.assertTrue(res_sort.success, f"uradar sort test failed: {res_sort.message}")
        self.assertEqual(res_sort.vars.get("d_closest"), 51.875)
        self.assertEqual(res_sort.vars.get("d_farthest"), 53.75)
        self.assertEqual(res_sort.vars.get("hp_max"), 70.0)
        self.assertEqual(res_sort.vars.get("hp_min"), 35.0)

        # 2. Tie-breaking: when health is identical, first iterated unit is preserved
        mlog_tie = """
# near_enemy_unit, mid_enemy_unit
ubind @flare
uradar enemy any any health 0 1 tie_hp
sensor x_tie tie_hp @x
"""
        res_tie = run_with_mindustry(mlog_tie)
        self.assertTrue(res_tie.success, f"uradar tie test failed: {res_tie.message}")
        self.assertEqual(res_tie.vars.get("x_tie"), 51.875)

    def test_ulocate_all_modes_and_building_resolution(self):
        """Verify ulocate modes (ore, building, spawn, damaged) and output resolution."""
        # 1. Standard modes: ore, friendly core, enemy core (none), spawn, damaged (none)
        mlog_std = """
ubind @flare
ulocate ore core true @copper o_x o_y o_found o_bld
ulocate building core false @copper c_x c_y c_found c_bld
ulocate building core true @copper e_x e_y e_found e_bld
ulocate spawn core true @copper s_x s_y s_found s_bld
ulocate damaged core false @copper d_x d_y d_found d_bld
"""
        res_std = run_with_mindustry(mlog_std)
        self.assertTrue(res_std.success, f"ulocate std test failed: {res_std.message}")
        # Ore copper located at (25, 25)
        self.assertEqual(res_std.vars.get("o_found"), 1.0)
        self.assertEqual(res_std.vars.get("o_x"), 25.0)
        self.assertEqual(res_std.vars.get("o_y"), 25.0)
        self.assertEqual(res_std.vars.get("o_bld"), "null")
        # Friendly core located at (40, 40)
        self.assertEqual(res_std.vars.get("c_found"), 1.0)
        self.assertEqual(res_std.vars.get("c_x"), 40.0)
        self.assertEqual(res_std.vars.get("c_y"), 40.0)
        self.assertEqual(res_std.vars.get("c_bld"), "core-shard")
        # Enemy core not found
        self.assertEqual(res_std.vars.get("e_found"), 0.0)
        self.assertEqual(res_std.vars.get("e_bld"), "null")
        # Spawn tile located at (10, 10)
        self.assertEqual(res_std.vars.get("s_found"), 1.0)
        self.assertEqual(res_std.vars.get("s_x"), 10.0)
        self.assertEqual(res_std.vars.get("s_y"), 10.0)
        # Damaged tile when everything is healthy -> not found
        self.assertEqual(res_std.vars.get("d_found"), 0.0)

        # 2. Damaged building mode when core is damaged
        mlog_dmg = """
# damaged_core
ubind @flare
ulocate damaged core false @copper d_x d_y d_found d_bld
"""
        res_dmg = run_with_mindustry(mlog_dmg)
        self.assertTrue(res_dmg.success, f"ulocate damaged test failed: {res_dmg.message}")
        self.assertEqual(res_dmg.vars.get("d_found"), 1.0)
        self.assertEqual(res_dmg.vars.get("d_x"), 40.0)
        self.assertEqual(res_dmg.vars.get("d_y"), 40.0)
        self.assertEqual(res_dmg.vars.get("d_bld"), "core-shard")

        # 3. Unbound unit calling ulocate returns found = 0
        mlog_unbound = """
ubind @mega
ulocate ore core true @copper o_x o_y o_found o_bld
"""
        res_unbound = run_with_mindustry(mlog_unbound)
        self.assertTrue(res_unbound.success, f"ulocate unbound failed: {res_unbound.message}")
        self.assertEqual(res_unbound.vars.get("o_found"), 0.0)

    def test_compiled_dsl_group_f_roundtrip(self):
        """Verify Python DSL ubind, uradar, ulocate compile, execute on engine, and roundtrip cleanly."""
        dsl_code = """from mlog import RadarSort, RadarTarget, Units, ubind, ulocate, uradar

ubind(Units.FLARE)
enemy = uradar(RadarTarget.ENEMY, RadarTarget.ANY, RadarTarget.ANY, RadarSort.DISTANCE, 1)
ox, oy, ofound = ulocate.ore("@copper")
bx, by, bfound, bbuild = ulocate.building("core", False)
"""
        compile_res = compile_py(dsl_code)
        self.assertIn("ubind @flare", compile_res.mlog)
        self.assertIn("uradar enemy any any distance 0 1 enemy", compile_res.mlog)
        self.assertIn("ulocate ore core true @copper ox oy ofound", compile_res.mlog)
        self.assertIn("ulocate building core false @copper bx by bfound bbuild", compile_res.mlog)

        # Execute on real Mindustry engine
        res = run_with_mindustry(compile_res.mlog)
        self.assertTrue(res.success, f"Compiled Group F execution failed: {res.message}")
        self.assertEqual(res.vars.get("enemy"), "flare")
        self.assertEqual(res.vars.get("ox"), 25.0)
        self.assertEqual(res.vars.get("oy"), 25.0)
        self.assertEqual(res.vars.get("ofound"), 1.0)
        self.assertEqual(res.vars.get("bx"), 40.0)
        self.assertEqual(res.vars.get("by"), 40.0)
        self.assertEqual(res.vars.get("bfound"), 1.0)
        self.assertEqual(res.vars.get("bbuild"), "core-shard")

        # Decompile back and verify roundtrip fidelity
        decompiled = decompile(compile_res.mlog)
        self.assertIn('ubind("@flare")', decompiled)
        self.assertIn('enemy = uradar("enemy", "any", "any", "distance", 1)', decompiled)
        self.assertIn('ox, oy, ofound = ulocate.ore("@copper")', decompiled)
        self.assertIn('bx, by, bfound, bbuild = ulocate.building("core", False)', decompiled)

    # -----------------------------------------------------------------------
    # Group G: Unit Direct Control & Turret Radar (ucontrol, radar)
    # -----------------------------------------------------------------------

    def test_radar_turret_target_filters_and_sorting(self):
        """Verify block radar with turret scans nearby units, filters by type, and sorts properly."""
        # 1. Target filtering: flying matches enemy flare, ground returns null
        mlog_filter = """
#links: duo1
# near_enemy_unit
radar enemy ground any distance duo1 1 out_ground
radar enemy flying any distance duo1 1 out_flying
sensor t_team out_flying @team
"""
        res_filter = run_with_mindustry(mlog_filter)
        self.assertTrue(res_filter.success, f"turret radar filter failed: {res_filter.message}")
        self.assertEqual(res_filter.vars.get("out_ground"), "null")
        self.assertEqual(res_filter.vars.get("out_flying"), "flare")
        self.assertEqual(res_filter.vars.get("t_team"), 2.0)

        # 2. Sorting by distance and health
        mlog_sort = """
#links: duo1
# near_enemy_unit, mid_enemy_unit, damaged_enemy
radar enemy any any distance duo1 1 closest
sensor x_closest closest @x
radar enemy any any distance duo1 0 farthest
sensor x_farthest farthest @x
radar enemy any any health duo1 1 max_hp
sensor hp_max max_hp @health
radar enemy any any health duo1 0 min_hp
sensor hp_min min_hp @health
"""
        res_sort = run_with_mindustry(mlog_sort)
        self.assertTrue(res_sort.success, f"turret radar sort failed: {res_sort.message}")
        self.assertEqual(res_sort.vars.get("x_closest"), 51.875)
        self.assertEqual(res_sort.vars.get("x_farthest"), 53.75)
        self.assertEqual(res_sort.vars.get("hp_max"), 70.0)
        self.assertEqual(res_sort.vars.get("hp_min"), 35.0)

    def test_radar_block_access_control_and_non_ranged(self):
        """Verify radar requires Ranged block, handles null safely, and enforces team ownership on standard processors."""
        # 1. Non-ranged building (cell1) and null target return null
        mlog_non_ranged = """
#links: cell1
radar enemy any any distance cell1 1 target_cell
radar enemy any any distance null 1 target_null
"""
        res_nr = run_with_mindustry(mlog_non_ranged)
        self.assertTrue(res_nr.success, f"non-ranged radar failed: {res_nr.message}")
        self.assertEqual(res_nr.vars.get("target_cell"), "null")
        self.assertEqual(res_nr.vars.get("target_null"), "null")

        # 2. Standard processor cannot scan using enemy turret
        mlog_std = """
#links: enemy_duo1
# near_enemy_unit
radar enemy any any distance enemy_duo1 1 target_std
"""
        res_std = run_with_mindustry(mlog_std)
        self.assertTrue(res_std.success, f"standard enemy turret radar failed: {res_std.message}")
        self.assertEqual(res_std.vars.get("target_std"), "null")

        # 3. World processor can scan using enemy turret
        mlog_world = """
#processor: world
#links: enemy_duo1
# near_enemy_unit
radar enemy any any distance enemy_duo1 1 target_world
"""
        res_world = run_with_mindustry(mlog_world)
        self.assertTrue(res_world.success, f"world enemy turret radar failed: {res_world.message}")
        self.assertEqual(res_world.vars.get("target_world"), "flare")

    def test_ucontrol_controller_lifecycle_and_unbind(self):
        """Verify ucontrol attaches LogicAI, transitions @controlled to 1, and unbind restores default controller (0)."""
        mlog = """
ubind @flare
sensor c_before @unit @controlled
ucontrol move 50 50 0 0 0
sensor c_during @unit @controlled
ucontrol unbind 0 0 0 0 0
sensor c_after @unit @controlled
ubind @mega
ucontrol move 50 50 0 0 0
set safe_after_unbound 1
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"ucontrol controller lifecycle failed: {res.message}")
        self.assertEqual(res.vars.get("c_before"), 0.0)
        self.assertEqual(res.vars.get("c_during"), 1.0)
        self.assertEqual(res.vars.get("c_after"), 0.0)
        self.assertEqual(res.vars.get("safe_after_unbound"), 1.0)

    def test_ucontrol_getblock_and_within(self):
        """Verify ucontrol within evaluates proximity and getBlock queries tile layers within range."""
        mlog = """
#links: cell1
ubind @flare
ucontrol within 51.25 51.25 5 res_near 0
ucontrol within 0 0 5 res_far 0
ucontrol getBlock 51 50 b_block b_build b_floor 0
ucontrol getBlock 1 1 out_block out_build out_floor 0
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"ucontrol within/getBlock failed: {res.message}")
        self.assertEqual(res.vars.get("res_near"), 1.0)
        self.assertEqual(res.vars.get("res_far"), 0.0)
        # Tile (51, 50) is cell1 building
        self.assertEqual(res.vars.get("b_block"), "memory-cell")
        self.assertEqual(res.vars.get("b_build"), "memory-cell")
        # Tile (1, 1) is beyond flare's range (9.5 tiles) -> null
        self.assertEqual(res.vars.get("out_block"), "null")
        self.assertEqual(res.vars.get("out_build"), "null")
        self.assertEqual(res.vars.get("out_floor"), "null")

    def test_ucontrol_flag_boost_and_item_drop(self):
        """Verify ucontrol flag updates unit flag, boost toggles state, and itemDrop @air clears items."""
        mlog = """
# unit_with_items
ubind @flare
sensor amt_before @unit @totalItems
sensor item_before @unit @firstItem
ucontrol flag 88888 0 0 0 0
sensor f @unit @flag
ucontrol boost 1 0 0 0 0
ucontrol itemDrop @air 0 0 0 0
sensor amt_after @unit @totalItems
sensor item_after @unit @firstItem
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"ucontrol flag/boost/itemDrop failed: {res.message}")
        self.assertEqual(res.vars.get("amt_before"), 15.0)
        self.assertEqual(res.vars.get("item_before"), "copper")
        self.assertEqual(res.vars.get("f"), 88888.0)
        self.assertEqual(res.vars.get("amt_after"), 0.0)
        self.assertEqual(res.vars.get("item_after"), "null")

    def test_ucontrol_target_and_targetp(self):
        """Verify ucontrol target and targetp set aim control on bound unit."""
        mlog = """
# near_enemy_unit
ubind @flare
ucontrol target 100 200 1 0 0
ucontrol targetp enemy_unit 1 0 0 0
ucontrol stop 0 0 0 0 0
ucontrol idle 0 0 0 0 0
set finished 1
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"ucontrol target/targetp failed: {res.message}")
        self.assertEqual(res.vars.get("finished"), 1.0)

    def test_compiled_dsl_group_g_roundtrip(self):
        """Verify Python DSL ucontrol and radar compile, execute on engine, and roundtrip cleanly."""
        dsl_code = """from mlog import RadarSort, RadarTarget, Units, radar, ubind, ucontrol

ubind(Units.FLARE)
ucontrol.move(50, 50)
ucontrol.boost(True)
ucontrol.flag(12345)
target = radar(RadarTarget.ENEMY, RadarTarget.ANY, RadarTarget.ANY, RadarSort.DISTANCE, duo1, 1)
ucontrol.targetp(target, 1)
ucontrol.unbind()
"""
        compile_res = compile_py(dsl_code)
        self.assertIn("ubind @flare", compile_res.mlog)
        self.assertIn("ucontrol move 50 50 0 0 0", compile_res.mlog)
        self.assertIn("ucontrol boost true 0 0 0 0", compile_res.mlog)
        self.assertIn("ucontrol flag 12345 0 0 0 0", compile_res.mlog)
        self.assertIn("radar enemy any any distance duo1 1 target", compile_res.mlog)
        self.assertIn("ucontrol targetp target 1 0 0 0", compile_res.mlog)
        self.assertIn("ucontrol unbind 0 0 0 0 0", compile_res.mlog)

        # Execute on real Mindustry engine
        exec_mlog = "#links: duo1\n# near_enemy_unit\n" + compile_res.mlog
        res = run_with_mindustry(exec_mlog)
        self.assertTrue(res.success, f"Compiled Group G execution failed: {res.message}")
        self.assertEqual(res.vars.get("target"), "flare")

        # Decompile back and verify roundtrip fidelity
        decompiled = decompile(compile_res.mlog)
        self.assertIn('ubind("@flare")', decompiled)
        self.assertIn('ucontrol("move", 50, 50, 0, 0, 0)', decompiled)
        self.assertIn('ucontrol("boost", True, 0, 0, 0, 0)', decompiled)
        self.assertIn('ucontrol("flag", 12345, 0, 0, 0, 0)', decompiled)
        self.assertIn('target = radar("enemy", "any", "any", "distance", "duo1", 1)', decompiled)
        self.assertIn('ucontrol("targetp", target, 1, 0, 0, 0)', decompiled)
        self.assertIn('ucontrol("unbind", 0, 0, 0, 0, 0)', decompiled)


    def test_ucontrol_item_take_transfers_items(self):
        """Verify ucontrol itemTake transfers items from container into bound unit with range and capacity limits."""
        mlog = """# links: container1
# container
# ucontrol_items
ubind @flare
sensor before_unit @unit @copper
sensor before_cont container1 @copper
ucontrol itemTake container1 @copper 10 0 0
sensor after_unit @unit @copper
sensor after_cont container1 @copper
# Negative amount transfer should be safely ignored
ucontrol itemTake container1 @copper -5 0 0
sensor negative_unit @unit @copper
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"ucontrol itemTake execution failed: {res.message}")
        self.assertEqual(res.vars.get("before_unit"), 0.0)
        self.assertEqual(res.vars.get("before_cont"), 100.0)
        self.assertEqual(res.vars.get("after_unit"), 10.0)
        self.assertEqual(res.vars.get("after_cont"), 90.0)
        self.assertEqual(res.vars.get("negative_unit"), 10.0)

    def test_ucontrol_payload_take_and_drop(self):
        """Verify ucontrol payTake picks up nearby grounded unit and payDrop drops it back to world."""
        mlog = """# payload_units
ubind @mega
sensor before_count @unit @payloadCount
sensor before_type @unit @payloadType
# Pick up ground unit (dagger)
ucontrol payTake 1 0 0 0 0
sensor taken_count @unit @payloadCount
sensor taken_type @unit @payloadType
# Wait for LogicAI.transferDelay cooldown (60 * 1.5 = 90 ticks)
wait 1.6
# Drop payload onto world
ucontrol payDrop 0 0 0 0 0
sensor dropped_count @unit @payloadCount
sensor dropped_type @unit @payloadType
# Units without payload capability (flare) should ignore payTake/payDrop safely
ubind @flare
ucontrol payTake 1 0 0 0 0
sensor flare_count @unit @payloadCount
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"ucontrol payTake/payDrop execution failed: {res.message}")
        self.assertEqual(res.vars.get("before_count"), 0.0)
        self.assertEqual(res.vars.get("before_type"), "null")
        self.assertEqual(res.vars.get("taken_count"), 1.0)
        self.assertEqual(res.vars.get("taken_type"), "dagger")
        self.assertEqual(res.vars.get("dropped_count"), 0.0)
        self.assertEqual(res.vars.get("dropped_type"), "null")
        self.assertEqual(res.vars.get("flare_count"), 0.0)

    def test_ucontrol_payload_enter_conveyor(self):
        """Verify ucontrol payEnter transfers valid non-core-spawned ground unit into payload conveyor."""
        mlog = """# links: conv1
# payload_conveyor
# 1. Flare spawned by core is rejected from payload entry
ubind @flare
ucontrol payEnter 0 0 0 0 0
sensor flare_dead @unit @dead
# 2. Ground dagger with spawnedByCore=false on payload conveyor tile enters conveyor
ubind @dagger
sensor dagger_before_dead @unit @dead
sensor conv_before_count conv1 @payloadCount
ucontrol payEnter 0 0 0 0 0
sensor dagger_after_dead @unit @dead
sensor conv_after_count conv1 @payloadCount
sensor conv_after_type conv1 @payloadType
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"ucontrol payEnter execution failed: {res.message}")
        self.assertEqual(res.vars.get("flare_dead"), 0.0)
        self.assertEqual(res.vars.get("dagger_before_dead"), 0.0)
        self.assertEqual(res.vars.get("conv_before_count"), 0.0)
        self.assertEqual(res.vars.get("dagger_after_dead"), 1.0)
        self.assertEqual(res.vars.get("conv_after_count"), 1.0)
        self.assertEqual(res.vars.get("conv_after_type"), "dagger")

    def test_lookup_exhaustive_categories_and_boundaries(self):
        """Verify lookup opcode across item, block, unit, liquid, team categories with boundary conditions."""
        mlog = """lookup item item0 0
lookup item item1 1
lookup item item_neg -1
lookup item item_oob 99999
lookup block block0 0
lookup block block_neg -1
lookup unit unit0 0
lookup unit unit_neg -1
lookup liquid liq0 0
lookup liquid liq_neg -1
lookup team team0 0
lookup team team1 1
lookup team team2 2
lookup team team_neg -1
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"lookup opcode execution failed: {res.message}")
        self.assertEqual(res.vars.get("item0"), "copper")
        self.assertEqual(res.vars.get("item1"), "lead")
        self.assertEqual(res.vars.get("item_neg"), "null")
        self.assertEqual(res.vars.get("item_oob"), "null")
        self.assertEqual(res.vars.get("block0"), "graphite-press")
        self.assertEqual(res.vars.get("block_neg"), "null")
        self.assertEqual(res.vars.get("unit0"), "dagger")
        self.assertEqual(res.vars.get("unit_neg"), "null")
        self.assertEqual(res.vars.get("liq0"), "water")
        self.assertEqual(res.vars.get("liq_neg"), "null")
        self.assertEqual(res.vars.get("team0"), "derelict")
        self.assertEqual(res.vars.get("team1"), "sharded")
        self.assertEqual(res.vars.get("team2"), "crux")
        self.assertEqual(res.vars.get("team_neg"), "null")

    def test_select_comprehensive_comparisons_and_coercion(self):
        """Verify select opcode conditional expressions, comparison operators, and value selection."""
        mlog = """select res_eq equal 5 5 100 200
select res_neq notEqual 5 6 100 200
select res_lt lessThan 3.5 4.5 10 20
select res_gte greaterThanEq 10 10 1 0
select res_strict strictEqual null null 42 0
select res_always always 0 0 77 88
select res_false equal 10 20 11 22
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"select opcode execution failed: {res.message}")
        self.assertEqual(res.vars.get("res_eq"), 100.0)
        self.assertEqual(res.vars.get("res_neq"), 100.0)
        self.assertEqual(res.vars.get("res_lt"), 10.0)
        self.assertEqual(res.vars.get("res_gte"), 1.0)
        self.assertEqual(res.vars.get("res_strict"), 42.0)
        self.assertEqual(res.vars.get("res_always"), 77.0)
        self.assertEqual(res.vars.get("res_false"), 22.0)

    def test_flow_control_stop_terminates_execution(self):
        """Verify stop opcode completely terminates processor execution pipeline and preserves counter state."""
        mlog = """set x 10
set y 20
stop
set x 999
set y 999
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"stop execution failed: {res.message}")
        self.assertEqual(res.vars.get("x"), 10.0)
        self.assertEqual(res.vars.get("y"), 20.0)

    def test_flow_control_end_resets_counter(self):
        """Verify end opcode resets program counter to instructions.length terminating current cycle pass."""
        mlog = """set step 1
end
set step_after 2
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"end opcode execution failed: {res.message}")
        self.assertEqual(res.vars.get("step"), 1.0)
        self.assertEqual(res.vars.get("step_after"), "null")

    def test_flow_control_jump_boundaries_and_loops(self):
        """Verify jump opcode target boundary behavior, forward/backward jumps, and loop termination."""
        mlog = """set step 0
# Forward jump skipping over step 1 to line 3
jump 3 always 0 0
set step 1
set step 2
# Negative target jump cleanly terminates execution
jump -10 always 0 0
set step 3
"""
        res = run_with_mindustry(mlog)
        self.assertTrue(res.success, f"jump boundary execution failed: {res.message}")
        self.assertEqual(res.vars.get("step"), 2.0)

    def test_compiled_dsl_group_h_roundtrip(self):
        """Verify Python DSL lookup, select, stop, end, and jump compile, execute on engine, and roundtrip cleanly."""
        dsl_code = """from mlog import LookupType, end, lookup, select, stop

item_name = lookup(LookupType.ITEM, 0)
val = select("equal", 1, 1, 100, 200)
x = 10 if val == 100 else 20
if x > 5:
    stop()
end()
"""
        compile_res = compile_py(dsl_code)
        self.assertIn("lookup item item_name 0", compile_res.mlog)
        self.assertIn("select val equal 1 1 100 200", compile_res.mlog)
        self.assertIn("stop", compile_res.mlog)
        self.assertIn("end", compile_res.mlog)

        # Execute on real Mindustry engine
        res = run_with_mindustry(compile_res.mlog)
        self.assertTrue(res.success, f"Compiled Group H execution failed: {res.message}")
        self.assertEqual(res.vars.get("item_name"), "copper")
        self.assertEqual(res.vars.get("val"), 100.0)
        self.assertEqual(res.vars.get("x"), 10.0)

        # Decompile back and verify roundtrip fidelity
        decompiled = decompile(compile_res.mlog)
        self.assertIn('lookup("item", 0)', decompiled)
        self.assertIn("stop", decompiled)


if __name__ == "__main__":
    unittest.main()




