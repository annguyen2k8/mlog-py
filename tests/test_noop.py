"""Regression and semantic test suite for Mindustry Logic 'noop' instruction support.

Verifies:
1. Validator accepts canonical 0-argument 'noop', rejects 'noop' with arguments,
   and rejects garbage/unknown opcodes.
2. Compiler emits 'noop' from intrinsic noop(), supports official import from mlog,
   and rejects arguments passed to noop().
3. Compiler semantic contract: Python 'pass' does NOT emit 'noop' (0 instructions).
4. Decompiler parses 'noop', formats it as 'noop()', rejects malformed 'noop 1',
   and properly collects DSL symbols.
5. Round-trip preservation: 'set a 1\\nnoop\\nset a 2' and jump-offset scripts
   preserve exact instruction order and indices.
6. Mindustry JVM harness integration: verifies that the real Mindustry engine
   validates 'noop' while rejecting 'noop 1' and invalid opcodes as InvalidStatement.
"""

import functools
import unittest

from src.decompiler import decompile
from src.decompiler.errors import MlogParseError
from src.decompiler.parser import MlogParser
from src.errors import CompileError
from src.mindustry_validator import (
    get_mindustry_unavailable_reason,
    validate_with_mindustry,
)
from src.mlog import compile_py
from src.validator import MlogValidator, ValidationError
import mlog


def _requires_mindustry(test):
    """Skip with the concrete discovery error when the JVM harness is absent."""

    @functools.wraps(test)
    def wrapper(self, *args, **kwargs):
        reason = get_mindustry_unavailable_reason()
        if reason:
            self.skipTest(reason)
        return test(self, *args, **kwargs)

    return wrapper


class TestNoopSupport(unittest.TestCase):
    """Test suite for 'noop' instruction support across validator, compiler, and decompiler."""

    # -----------------------------------------------------------------------
    # 1. Validator Tests
    # -----------------------------------------------------------------------

    def test_validator_accepts_standalone_noop(self):
        """Validator accepts valid 0-argument noop instruction."""
        MlogValidator.validate("noop")

    def test_validator_accepts_interleaved_noop(self):
        """Validator accepts multiple noop instructions interleaved with code."""
        mlog_text = (
            "set a 1\n"
            "noop\n"
            "set a 2\n"
            "noop\n"
            "set a 3"
        )
        MlogValidator.validate(mlog_text)

    def test_validator_rejects_noop_with_args(self):
        """Validator strictly rejects noop when arguments are provided."""
        bad_cases = [
            "noop 1",
            "noop foo",
            "noop 0 0",
            "noop @copper",
        ]
        for case in bad_cases:
            with self.subTest(case=case):
                with self.assertRaises(ValidationError) as ctx:
                    MlogValidator.validate(case)
                self.assertIn("expects 0 arguments", str(ctx.exception))

    def test_validator_rejects_garbage_and_nonexistent_opcodes(self):
        """Validator strictly rejects non-existent or garbage opcodes."""
        garbage_cases = [
            "invalid_opcode",
            "invalid_opcode foo",
            "noop_extra",
            "foo 1 2 3",
            "bar",
        ]
        for case in garbage_cases:
            with self.subTest(case=case):
                with self.assertRaises(ValidationError) as ctx:
                    MlogValidator.validate(case)
                self.assertIn("Unknown or unsupported mlog opcode", str(ctx.exception))

    # -----------------------------------------------------------------------
    # 2. Compiler Tests
    # -----------------------------------------------------------------------

    def test_compiler_noop_intrinsic(self):
        """Compiler compiles noop() intrinsic to 'noop' instruction."""
        res = compile_py("noop()")
        self.assertEqual(res.mlog.strip(), "noop")

    def test_compiler_noop_with_import(self):
        """Compiler compiles official 'from mlog import noop' correctly."""
        source = (
            "from mlog import noop, set\n"
            "set(a, 1)\n"
            "noop()\n"
            "set(a, 2)\n"
        )
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(lines, ["set a 1", "noop", "set a 2"])

    def test_compiler_noop_rejects_arguments(self):
        """Compiler raises CompileError if arguments are passed to noop()."""
        bad_sources = [
            "noop(1)",
            "noop('arg')",
            "noop(a, b)",
        ]
        for src in bad_sources:
            with self.subTest(src=src):
                with self.assertRaises(CompileError) as ctx:
                    compile_py(src)
                self.assertIn("expected noop()", str(ctx.exception))

    def test_pass_does_not_emit_noop(self):
        """Compiler semantic guarantee: Python 'pass' must NOT emit 'noop'."""
        # 1. Standalone pass emits 0 instructions
        res_pass = compile_py("pass")
        self.assertEqual(res_pass.mlog.strip(), "")

        # 2. Pass in sequential statements emits no instructions
        res_seq = compile_py("x = 1\npass\ny = 2")
        lines = res_seq.mlog.strip().splitlines()
        self.assertEqual(lines, ["set x 1", "set y 2"])

        # 3. Pass in conditional body
        res_if = compile_py("if x == 0:\n    pass\nelse:\n    y = 1")
        self.assertNotIn("noop", res_if.mlog)

    def test_runtime_noop_callable(self):
        """Runtime module exports noop() as a no-op callable returning None."""
        self.assertTrue(hasattr(mlog, "noop"))
        result = mlog.noop()
        self.assertIsNone(result)

    # -----------------------------------------------------------------------
    # 3. Decompiler & Parser Tests
    # -----------------------------------------------------------------------

    def test_decompiler_parser_parses_noop(self):
        """MlogParser parses 'noop' instruction with 0 arguments."""
        parser = MlogParser()
        instrs = parser.parse("noop")
        self.assertEqual(len(instrs), 1)
        self.assertEqual(instrs[0].opcode, "noop")
        self.assertEqual(instrs[0].args, ())
        self.assertTrue(instrs[0].can_fallthrough)
        self.assertFalse(instrs[0].is_terminal)

    def test_decompiler_parser_rejects_noop_with_args(self):
        """MlogParser rejects 'noop 1' with MlogParseError."""
        parser = MlogParser()
        with self.assertRaises(MlogParseError) as ctx:
            parser.parse("noop 1")
        self.assertIn("expects 0 argument(s)", str(ctx.exception))

    def test_decompiler_parser_rejects_garbage_opcode(self):
        """MlogParser rejects unknown opcodes with MlogParseError."""
        parser = MlogParser()
        with self.assertRaises(MlogParseError) as ctx:
            parser.parse("garbage_op 1 2")
        self.assertIn("Unknown mlog opcode", str(ctx.exception))

    def test_decompiler_emits_noop_call(self):
        """Decompiler emits 'noop()' in Python DSL."""
        py_code = decompile("noop\n")
        self.assertIn("noop()", py_code)
        self.assertIn("from mlog import noop", py_code)

    # -----------------------------------------------------------------------
    # 4. Round-Trip Tests
    # -----------------------------------------------------------------------

    def test_roundtrip_set_noop_set(self):
        """Preserves exact instruction order for 'set a 1\\nnoop\\nset a 2'."""
        original_mlog = "set a 1\nnoop\nset a 2"
        decompiled_py = decompile(original_mlog)
        recompiled = compile_py(decompiled_py)
        self.assertEqual(recompiled.mlog.strip(), original_mlog)

    def test_roundtrip_jump_over_noop(self):
        """Preserves jump targets and instruction positions over noop."""
        # Instruction 0: set a 1
        # Instruction 1: jump 3 equal a 1
        # Instruction 2: noop
        # Instruction 3: set a 2
        original_mlog = (
            "set a 1\n"
            "jump 3 equal a 1\n"
            "noop\n"
            "set a 2"
        )
        decompiled_py = decompile(original_mlog)
        recompiled = compile_py(decompiled_py)
        self.assertEqual(recompiled.mlog.strip(), original_mlog)

    # -----------------------------------------------------------------------
    # 5. Mindustry JVM Harness Tests
    # -----------------------------------------------------------------------

    @_requires_mindustry
    def test_mindustry_harness_accepts_noop(self):
        """Real Mindustry engine accepts 'noop'."""
        valid, msg, count = validate_with_mindustry("noop")
        self.assertTrue(valid, f"Expected noop to be accepted, got error: {msg}")
        self.assertEqual(count, 1)

    @_requires_mindustry
    def test_mindustry_harness_accepts_interleaved_noop(self):
        """Real Mindustry engine accepts 'set a 1\\nnoop\\nset a 2'."""
        mlog_text = "set a 1\nnoop\nset a 2"
        valid, msg, count = validate_with_mindustry(mlog_text)
        self.assertTrue(valid, f"Expected script with noop to be accepted, got error: {msg}")
        self.assertEqual(count, 3)

    @_requires_mindustry
    def test_mindustry_harness_rejects_noop_with_args(self):
        """Real Mindustry engine rejects 'noop 1' as InvalidStatement."""
        valid, msg, count = validate_with_mindustry("noop 1")
        self.assertFalse(valid, "Expected noop with args to be rejected")
        self.assertIn("InvalidStatement", msg)

    @_requires_mindustry
    def test_mindustry_harness_rejects_invalid_opcode(self):
        """Real Mindustry engine rejects non-existent opcode as InvalidStatement."""
        valid, msg, count = validate_with_mindustry("fake_opcode foo bar")
        self.assertFalse(valid, "Expected non-existent opcode to be rejected")
        self.assertIn("InvalidStatement", msg)

    @_requires_mindustry
    def test_mindustry_harness_accepts_noop_with_semicolon_in_string(self):
        """Regression: semicolon inside string literal must not misalign statement index."""
        mlog_text = 'print "hello; world"\nnoop'
        valid, msg, count = validate_with_mindustry(mlog_text)
        self.assertTrue(valid, f"Expected script to be accepted, got error: {msg}")
        self.assertEqual(count, 2)

    @_requires_mindustry
    def test_mindustry_harness_accepts_noop_with_comment_char_in_string(self):
        """Regression: '#' inside string literal must not truncate statement or misalign index."""
        mlog_text = 'print "color #ff0000"; noop'
        valid, msg, count = validate_with_mindustry(mlog_text)
        self.assertTrue(valid, f"Expected script to be accepted, got error: {msg}")
        self.assertEqual(count, 2)

    @_requires_mindustry
    def test_mindustry_harness_accepts_noop_with_escaped_quotes(self):
        """Regression: escaped quotes with semicolon must not confuse string boundary."""
        mlog_text = 'print "a \\" ; b"\nnoop'
        valid, msg, count = validate_with_mindustry(mlog_text)
        self.assertTrue(valid, f"Expected script to be accepted, got error: {msg}")
        self.assertEqual(count, 2)

    @_requires_mindustry
    def test_mindustry_harness_accepts_noop_with_labels_and_comments(self):
        """Regression: jump labels and comments do not count as statements in LParser."""
        mlog_text = (
            "# header comment\n"
            "start:\n"
            "noop # inline comment\n"
        )
        valid, msg, count = validate_with_mindustry(mlog_text)
        self.assertTrue(valid, f"Expected script to be accepted, got error: {msg}")
        self.assertEqual(count, 1)

    @_requires_mindustry
    def test_mindustry_harness_rejects_privileged_opcode(self):
        """Real Mindustry engine rejects privileged opcodes when unprivileged."""
        valid, msg, count = validate_with_mindustry("spawnunit @flare 0 0")
        self.assertFalse(valid, "Expected privileged opcode to be rejected in non-privileged harness")
        self.assertIn("InvalidStatement", msg)

    @_requires_mindustry
    def test_mindustry_harness_prevents_index_mismatch_exploit_garbage_opcode(self):
        """Regression: index shift must never cause a garbage opcode to be accepted as noop."""
        mlog_text = 'print "a; noop ; b"\ninvalid_opcode foo'
        valid, msg, count = validate_with_mindustry(mlog_text)
        self.assertFalse(valid, "Expected garbage opcode to be rejected even with '; noop ;' in preceding string")
        self.assertIn("InvalidStatement", msg)
        self.assertIn("invalid_opcode", msg)

    @_requires_mindustry
    def test_mindustry_harness_prevents_index_mismatch_exploit_privileged_opcode(self):
        """Regression: index shift must never cause a privileged opcode to be accepted as noop."""
        mlog_text = 'print "a; noop ; b"\nspawnunit @flare 0 0'
        valid, msg, count = validate_with_mindustry(mlog_text)
        self.assertFalse(valid, "Expected privileged opcode to be rejected even with '; noop ;' in preceding string")
        self.assertIn("InvalidStatement", msg)
        self.assertIn("spawnunit", msg)


if __name__ == "__main__":
    unittest.main()
