"""Regression tests for P4 Semantic & Runtime Correctness Remediation:
1. CRIT-01: Identifier collision fix (counter & _counter treated as normal variables, Vars.counter for explicit @counter).
2. CRIT-02: Boolean short-circuit destination corruption fix (use temporary accumulator for BoolOp).
3. HIGH-01: Team normalization & dynamic operands in spawn.
4. MED-01: draw.clear signature aligned with Mindustry v160.7 (3 operands r, g, b).
5. INFO-01: Zero-division runtime behavior verification.
"""

import unittest
from mlog import (
    compile_py,
    Vars,
    Teams,
    Units,
)
from mlog.errors import CompileError
from mlog.validator import MlogValidator
from mlog.mindustry_validator import is_mindustry_available, validate_with_mindustry, run_with_mindustry


class TestP4Remediation(unittest.TestCase):
    """Test suite for P4 Semantic & Runtime Correctness Remediation."""

    def compile_code(self, source: str) -> str:
        """Compile DSL source and validate syntax."""
        res = compile_py(source, validate=True)
        mlog_text = res.mlog.strip()
        MlogValidator.validate(mlog_text)
        return mlog_text

    def validate_with_jvm(self, mlog_text: str):
        """Validate generated mlog against real Mindustry v160.7 engine if available."""
        if is_mindustry_available():
            world_opcodes = ("query", "message", "spawn", "fetch", "setrule", "weather", "effect", "explosion", "setmarker", "makemarker")
            if any(op in mlog_text for op in world_opcodes) and "#processor" not in mlog_text:
                test_mlog = "#processor: world\n" + mlog_text
            else:
                test_mlog = mlog_text
            valid, err, *_ = validate_with_mindustry(test_mlog)
            self.assertTrue(valid, f"JVM validation failed: {err}")

    # =========================================================================
    # 1. CRIT-01: Identifier collision (counter & _counter vs Vars.counter)
    # =========================================================================

    def test_crit01_counter_variable_as_normal_identifier(self):
        """Verify 'counter' and '_counter' are treated as normal Python variables, not @counter."""
        source = """
counter = 0
_counter = 10
counter += 1
_counter = _counter + 5
total = counter + _counter
"""
        mlog = self.compile_code(source)
        self.assertIn("set counter 0", mlog)
        self.assertIn("set _counter 10", mlog)
        self.assertIn("op add counter counter 1", mlog)
        self.assertIn("op add _counter _counter 5", mlog)
        self.assertIn("op add total counter _counter", mlog)
        # Ensure @counter is never emitted for user variables
        self.assertNotIn("@counter", mlog)
        self.validate_with_jvm(mlog)

        if is_mindustry_available():
            run_res = run_with_mindustry(mlog, max_steps=50)
            self.assertEqual(run_res.vars.get("counter"), 1.0)
            self.assertEqual(run_res.vars.get("_counter"), 15.0)
            self.assertEqual(run_res.vars.get("total"), 16.0)

    def test_crit01_counter_loop_execution(self):
        """Verify loops using 'counter' variable execute all iterations without skipping instructions."""
        source = """
counter = 0
total = 0
while counter < 5:
    total += counter
    counter += 1
"""
        mlog = self.compile_code(source)
        self.assertNotIn("@counter", mlog)
        self.validate_with_jvm(mlog)

        if is_mindustry_available():
            run_res = run_with_mindustry(mlog, max_steps=100)
            # 0 + 1 + 2 + 3 + 4 = 10
            self.assertEqual(run_res.vars.get("total"), 10.0)
            self.assertEqual(run_res.vars.get("counter"), 5.0)

    def test_crit01_explicit_vars_counter_still_targets_program_counter(self):
        """Verify Vars.counter explicitly targets @counter."""
        source = """
Vars.counter = 10
Vars.counter += 2
"""
        mlog = self.compile_code(source)
        self.assertIn("set @counter 10", mlog)
        self.assertIn("op add @counter @counter 2", mlog)
        self.validate_with_jvm(mlog)



    # =========================================================================
    # 2. CRIT-02: Boolean short-circuit destination corruption
    # =========================================================================

    def test_crit02_boolop_and_destination_not_corrupted(self):
        """Verify target_dest is not prematurely overwritten in 'and' chains."""
        source = """
x = 10
x = (x > 5) and (x + 1)
"""
        mlog = self.compile_code(source)
        self.validate_with_jvm(mlog)

        if is_mindustry_available():
            run_res = run_with_mindustry(mlog, max_steps=50)
            # In standard Python: (10 > 5) is True, (10 + 1) is 11 -> x must be 11.0
            self.assertEqual(run_res.vars.get("x"), 11.0)

    def test_crit02_boolop_or_destination_not_corrupted(self):
        """Verify target_dest is not prematurely overwritten in 'or' chains."""
        source = """
x = 10
x = False or (x + 1)
"""
        mlog = self.compile_code(source)
        self.validate_with_jvm(mlog)

        if is_mindustry_available():
            run_res = run_with_mindustry(mlog, max_steps=50)
            # In standard Python: False is falsy, (10 + 1) is 11 -> x must be 11.0
            self.assertEqual(run_res.vars.get("x"), 11.0)

    def test_crit02_boolop_short_circuit_preserved(self):
        """Verify short-circuiting skips subsequent branches when target_dest is used."""
        source = """
x = 10
x = (x < 5) and (x + 1)
"""
        mlog = self.compile_code(source)
        self.validate_with_jvm(mlog)

        if is_mindustry_available():
            run_res = run_with_mindustry(mlog, max_steps=50)
            # (10 < 5) is 0 (False) -> short-circuit occurs, x receives 0.0
            self.assertEqual(run_res.vars.get("x"), 0.0)

    def test_crit02_boolop_nested_and_or(self):
        """Verify nested and/or expressions correctly compute without target variable corruption."""
        source = """
x = 5
x = ((x == 5) and (x * 2)) or (x + 100)
"""
        mlog = self.compile_code(source)
        self.validate_with_jvm(mlog)

        if is_mindustry_available():
            run_res = run_with_mindustry(mlog, max_steps=50)
            # (5 == 5) is True -> 5 * 2 = 10. 10 is truthy -> or short-circuits -> x = 10.0
            self.assertEqual(run_res.vars.get("x"), 10.0)

    def test_crit02_boolop_multiple_operands(self):
        """Verify 3+ operand boolean chains preserve target variable across all steps."""
        source = """
a = 2
a = (a > 0) and (a < 10) and (a + 5)
"""
        mlog = self.compile_code(source)
        self.validate_with_jvm(mlog)

        if is_mindustry_available():
            run_res = run_with_mindustry(mlog, max_steps=50)
            # a > 0 is True, a < 10 is True, a + 5 is 7.0 -> a = 7.0
            self.assertEqual(run_res.vars.get("a"), 7.0)



    # =========================================================================
    # 3. HIGH-01: Team normalization & dynamic operands in spawn
    # =========================================================================

    def test_high01_fetch_team_identifier_collision(self):
        """Verify user variables named after teams (e.g. sharded) are not converted to constants."""
        source = """
sharded = Teams.CRUX
u = fetch.unit(sharded, 0)
"""
        mlog = self.compile_code(source)
        self.assertIn("set sharded @crux", mlog)
        self.assertIn("fetch unit u sharded 0 0", mlog)
        self.assertNotIn("fetch unit u @sharded 0 0", mlog)
        self.validate_with_jvm(mlog)

        if is_mindustry_available():
            test_mlog = "#processor: world\n" + mlog
            run_res = run_with_mindustry(test_mlog, max_steps=10)
            self.assertTrue(run_res.success, f"Fetch execution failed: {run_res.message}")
            self.assertEqual(run_res.vars.get("sharded"), "crux")

    def test_high01_spawn_dynamic_operands(self):
        """Verify spawn supports runtime variables for unit type and team."""
        source = """
t = Teams.SHARDED
u_type = Units.flare
res = spawn(u_type, 10, 20, 0, t)
"""
        mlog = self.compile_code(source)
        self.assertIn("set t @sharded", mlog)
        self.assertIn("set u_type @flare", mlog)
        self.assertIn("spawn u_type 10 20 0 t res 0", mlog)
        self.validate_with_jvm(mlog)

        if is_mindustry_available():
            test_mlog = "#processor: world\n" + mlog
            run_res = run_with_mindustry(test_mlog, max_steps=10)
            self.assertTrue(run_res.success, f"Spawn execution failed: {run_res.message}")
            self.assertEqual(run_res.vars.get("t"), "sharded")
            self.assertEqual(run_res.vars.get("u_type"), "flare")

    def test_high01_bullet_and_explosion_team_identifiers(self):
        """Verify bullet and explosion preserve user variable names in team operands."""
        source = """
crux = Teams.SHARDED
explosion(crux, 10, 20, 5, 50)
b_res = bullet(None, 0, 10, 20, 0, crux)
"""
        mlog = self.compile_code(source)
        self.assertIn("explosion crux 10 20 5 50 1 1 0 1", mlog)
        self.assertIn("bullet b_res null 0 10 20 0 crux null -1 1 1 -1 -1", mlog)
        self.validate_with_jvm(mlog)



    # =========================================================================
    # 4. MED-01: draw.clear signature (3 operands r, g, b)
    # =========================================================================

    def test_med01_draw_clear_signature_and_rejection(self):
        """Verify draw.clear only accepts (r, g, b) and rejects alpha (MED-01)."""
        # Valid 3-arg call
        mlog = self.compile_code("from mlog import draw\ndraw.clear(255, 128, 64)\n")
        self.assertIn("draw clear 255 128 64 0 0 0", mlog)
        self.validate_with_jvm(mlog)

        # 4 positional args rejected
        with self.assertRaises(CompileError) as ctx:
            self.compile_code("from mlog import draw\ndraw.clear(255, 128, 64, 255)\n")
        self.assertIn("at most 3 arguments", str(ctx.exception))

        # Keyword 'a' rejected
        with self.assertRaises(CompileError) as ctx:
            self.compile_code("from mlog import draw\ndraw.clear(r=10, g=20, b=30, a=40)\n")
        self.assertIn("unexpected keyword argument 'a'", str(ctx.exception))

    # =========================================================================
    # 5. INFO-01: Zero division runtime behavior on Mindustry engine
    # =========================================================================

    def test_info01_zero_division_evaluates_to_null_without_crashing(self):
        """Verify division by zero produces 'null' without throwing exception in Mindustry JVM."""
        source = """
a = 10
b = 0
div_res = a / b
idiv_res = a // b
mod_res = a % b
"""
        mlog = self.compile_code(source)
        self.assertIn("op div div_res a b", mlog)
        self.assertIn("op idiv idiv_res a b", mlog)
        self.assertIn("op emod mod_res a b", mlog)
        self.validate_with_jvm(mlog)

        if is_mindustry_available():
            run_res = run_with_mindustry(mlog, max_steps=50)
            self.assertTrue(run_res.success)
            self.assertEqual(run_res.vars.get("div_res"), "null")
            self.assertEqual(run_res.vars.get("idiv_res"), "null")
            self.assertEqual(run_res.vars.get("mod_res"), "null")


if __name__ == "__main__":
    unittest.main()
