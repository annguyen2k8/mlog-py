"""Phase 2 Integration Tests: Language Semantics, Hardening, and Safety.

Tests boolean short-circuit evaluation, @counter behavior, end/stop/wait semantics,
signature validation, temporary variable collision prevention, determinism,
and processor limit enforcement (1000 instructions, 500 jumps).
"""

import unittest
from src.errors import CompileError
from src.mlog import compile_py
from src.mindustry_validator import is_mindustry_available, validate_with_mindustry


class TestPhase2Semantics(unittest.TestCase):

    def _compile_and_validate(self, code: str):
        """Helper to compile and validate against real Mindustry engine."""
        res = compile_py(code)
        if is_mindustry_available():
            ok, msg, count = validate_with_mindustry(res.mlog)
            self.assertTrue(ok, f"Mindustry validation failed: {msg}\nMLOG:\n{res.mlog}")
        return res

    # ---------------------------------------------------------
    # 1. Boolean Short-circuiting
    # ---------------------------------------------------------

    def test_short_circuit_and(self):
        """In 'if a and b:', if a is false, jump directly to else/end without evaluating b."""
        code = """
if a > 0 and b > 0:
    x = 1
"""
        res = self._compile_and_validate(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        # Expected:
        # jump 2 lessThanEq a 0  (skips to after if body if a <= 0)
        # jump 2 lessThanEq b 0  (skips to after if body if b <= 0)
        # set x 1
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], "jump 3 lessThanEq a 0")
        self.assertEqual(lines[1], "jump 3 lessThanEq b 0")
        self.assertEqual(lines[2], "set x 1")

    def test_short_circuit_or(self):
        """In 'if a or b:', if a is true, jump directly to body without evaluating b."""
        code = """
if a > 0 or b > 0:
    x = 1
"""
        res = self._compile_and_validate(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        # Expected:
        # jump 2 greaterThan a 0  (jumps directly to body if a > 0)
        # jump 3 lessThanEq b 0   (skips body if b <= 0)
        # set x 1
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], "jump 2 greaterThan a 0")
        self.assertEqual(lines[1], "jump 3 lessThanEq b 0")
        self.assertEqual(lines[2], "set x 1")

    def test_short_circuit_nested_and_or(self):
        """Test complex condition: if (a and b) or (c and d):"""
        code = """
if (a > 0 and b > 0) or (c > 0 and d > 0):
    res = 1
"""
        res = self._compile_and_validate(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        self.assertTrue(len(lines) > 0)

    def test_boolean_expression_assignment(self):
        """Test assigning boolean expressions: x = a and b, y = c or d, z = not e."""
        code = """
x = a and b
y = c or d
z = not e
cmp = a < b
"""
        res = self._compile_and_validate(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        # Verify cmp uses op lessThan
        self.assertTrue(any("op lessThan cmp a b" in line for line in lines))
        # Verify z uses op equal z e 0
        self.assertTrue(any("op equal z e 0" in line for line in lines))

    # ---------------------------------------------------------
    # 2. @counter Semantics
    # ---------------------------------------------------------

    def test_counter_read_and_write(self):
        """Test reading and writing @counter variable."""
        code = """
x = at_counter
set(at_counter, 5)
set("@counter", 10)
curr = _counter
"""
        res = self._compile_and_validate(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        self.assertIn("set x @counter", lines)
        self.assertIn("set @counter 5", lines)
        self.assertIn("set @counter 10", lines)
        self.assertIn("set curr @counter", lines)

    def test_counter_in_branching(self):
        """Test dynamic @counter manipulation inside conditional logic."""
        code = """
if flag == 1:
    set(at_counter, skip_target)
else:
    x = at_counter
"""
        res = self._compile_and_validate(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        self.assertTrue(any("set @counter skip_target" in line for line in lines))

    # ---------------------------------------------------------
    # 3. end(), stop(), wait() Semantics
    # ---------------------------------------------------------

    def test_end_stop_wait_valid(self):
        """Test valid calls to end(), stop(), wait()."""
        code = """
wait(1.5)
wait()
end()
stop()
"""
        res = self._compile_and_validate(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        self.assertEqual(lines[0], "wait 1.5")
        self.assertEqual(lines[1], "wait 0.5")
        self.assertEqual(lines[2], "end")
        self.assertEqual(lines[3], "stop")

    def test_end_stop_wait_invalid_args(self):
        """Test that invalid argument counts to end(), stop(), wait() raise CompileError."""
        with self.assertRaises(CompileError) as ctx:
            compile_py("end(1)")
        self.assertIn("invalid arguments for end", str(ctx.exception))

        with self.assertRaises(CompileError) as ctx:
            compile_py("stop(1)")
        self.assertIn("invalid arguments for stop", str(ctx.exception))

        with self.assertRaises(CompileError) as ctx:
            compile_py("wait(1, 2)")
        self.assertIn("invalid arguments for wait", str(ctx.exception))

    # ---------------------------------------------------------
    # 4. Temporary Variable Collision Prevention
    # ---------------------------------------------------------

    def test_temp_var_collision_rejected(self):
        """User variable named __tmp... must be rejected with CompileError."""
        with self.assertRaises(CompileError) as ctx:
            compile_py("__tmp0 = 123")
        self.assertIn("reserved for compiler temporaries", str(ctx.exception))

        with self.assertRaises(CompileError) as ctx:
            compile_py("x = __tmp1 + 5")
        self.assertIn("reserved for compiler temporaries", str(ctx.exception))

    # ---------------------------------------------------------
    # 5. Deterministic Output
    # ---------------------------------------------------------

    def test_deterministic_output(self):
        """Compiling the same source 10 times produces byte-for-byte identical output."""
        code = """
i = 0
total = 0
while i < 10:
    val = (i + 2) * 3
    if val > 15:
        total = total + val
    else:
        total = total - 1
    i = i + 1
"""
        first_output = compile_py(code).mlog
        for _ in range(9):
            subsequent_output = compile_py(code).mlog
            self.assertEqual(first_output, subsequent_output)

    # ---------------------------------------------------------
    # 6. Processor Limits Enforcement
    # ---------------------------------------------------------

    def test_max_instructions_limit(self):
        """More than 1000 instructions must raise CompileError."""
        # Generate code with >1000 statements
        stmts = ["x = 1\n"] * 1005
        code = "".join(stmts)
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("Mindustry limit is 1000", str(ctx.exception))

    def test_max_jumps_limit(self):
        """More than 500 jumps must raise CompileError."""
        # Generate code with >500 jumps
        stmts = ["jump(0, 'always')\n"] * 505
        code = "".join(stmts)
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("Mindustry limit is 500", str(ctx.exception))

    # ---------------------------------------------------------
    # 7. Signature Validation & Error Formatting
    # ---------------------------------------------------------

    def test_signature_validation_errors(self):
        """Test opcode signature and argument validation."""
        # Missing destination in standalone sensor
        with self.assertRaises(CompileError) as ctx:
            compile_py("sensor(block1, '@health')")
        self.assertIn("invalid arguments for sensor", str(ctx.exception))

        # Missing required args in write
        with self.assertRaises(CompileError) as ctx:
            compile_py("write(10, cell1)")
        self.assertIn("invalid arguments for write", str(ctx.exception))

        # Unknown sensor property
        with self.assertRaises(CompileError) as ctx:
            compile_py("hp = sensor(block1, '@invalidProp')")
        self.assertIn("unknown sensor property", str(ctx.exception))

        # Raw mode escape hatch accepts unlisted property
        res = compile_py("hp = sensor(block1, raw('@invalidProp'))")
        self.assertIn("sensor hp block1 @invalidProp", res.mlog)


if __name__ == "__main__":
    unittest.main()
