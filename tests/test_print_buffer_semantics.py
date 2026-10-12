"""Regression tests for Mindustry Logic print and printflush buffer semantics.

Verifies:
- In Mindustry Logic (LExecutor.PrintI), `print` appends text directly to the processor's
  textBuffer WITHOUT appending an automatic newline or space.
- Multiple consecutive `print()` calls concatenate into a single line in the buffer.
- To produce multiline output, `\\n` must be explicitly included in the string literal.
- `printflush()` flushes the buffer to the message block and resets it to empty.
- Neither compiler nor decompiler synthesizes artificial newlines or merges print calls,
  preserving exact 1-to-1 instruction semantics.
"""

import ast
import unittest

from src.decompiler import decompile
from src.metadata import (
    _rt_print,
    _rt_printflush,
    clear_print_buffer,
    get_print_buffer,
)
from src.mlog import compile_py


class TestPrintBufferSemantics(unittest.TestCase):
    """Verify print and printflush buffer behavior across compiler, decompiler, and runtime."""

    def setUp(self):
        clear_print_buffer()

    def tearDown(self):
        clear_print_buffer()

    def test_consecutive_prints_compile_without_newlines(self):
        """Consecutive print calls compile to consecutive flat mlog print instructions."""
        source = """from mlog import print, printflush

print("Status: ")
print("ONLINE")
printflush("message1")
"""
        res = compile_py(source, filename="test_print.py", validate=True)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], 'print "Status: "')
        self.assertEqual(lines[1], 'print "ONLINE"')
        self.assertEqual(lines[2], 'printflush message1')

    def test_consecutive_prints_decompile_without_altering_semantics(self):
        """Consecutive print instructions decompile to 1-to-1 print calls without synthesizing newlines."""
        mlog = """print "Status: "
print "ONLINE"
printflush message1
"""
        py = decompile(mlog).strip()
        ast.parse(py)
        self.assertIn('print("Status: ")', py)
        self.assertIn('print("ONLINE")', py)
        self.assertIn('printflush("message1")', py)
        # Ensure decompiler did not synthesize artificial \n
        self.assertNotIn('\\n', py)

    def test_explicit_newline_in_print_roundtrip(self):
        """Explicit \\n in string literals is preserved across compile and decompile roundtrip."""
        mlog = """print "Header:\\n"
print "Line 1\\n"
print "Line 2\\n"
printflush message1
"""
        py = decompile(mlog).strip()
        ast.parse(py)
        self.assertIn('print("Header:\\n")', py)
        self.assertIn('print("Line 1\\n")', py)
        self.assertIn('print("Line 2\\n")', py)

        recompiled = compile_py(py).mlog.strip()
        self.assertEqual(recompiled, mlog.strip())

    def test_runtime_buffer_concatenation_no_automatic_newline(self):
        """Runtime emulation confirms print calls concatenate without newlines until printflush."""
        self.assertEqual(get_print_buffer(), "")

        _rt_print("Hello, ")
        self.assertEqual(get_print_buffer(), "Hello, ")

        _rt_print("World!")
        self.assertEqual(get_print_buffer(), "Hello, World!")

        # Flushed to message block -> buffer cleared
        _rt_printflush("message1")
        self.assertEqual(get_print_buffer(), "")

    def test_runtime_buffer_with_explicit_newline(self):
        """Runtime emulation with explicit \\n produces expected multiline text."""
        _rt_print("Row 1\n")
        _rt_print("Row 2\n")
        self.assertEqual(get_print_buffer(), "Row 1\nRow 2\n")

        _rt_printflush("message1")
        self.assertEqual(get_print_buffer(), "")

    def test_runtime_buffer_numeric_and_bool_formatting(self):
        """Runtime emulation formats numbers, booleans, and null according to Mindustry rules."""
        _rt_print("Items: ")
        _rt_print(42)
        _rt_print(" Active: ")
        _rt_print(True)
        _rt_print(" Inactive: ")
        _rt_print(False)
        _rt_print(" Extra: ")
        _rt_print(None)

        self.assertEqual(get_print_buffer(), "Items: 42 Active: 1 Inactive: 0 Extra: null")
        _rt_printflush("message1")
        self.assertEqual(get_print_buffer(), "")

    def test_runtime_buffer_float_epsilon_and_integer_formatting(self):
        """Runtime emulation formats floats within 1e-5 epsilon as integers, matching Java LExecutor."""
        _rt_print(42.0)
        _rt_print(" ")
        _rt_print(10.000001)
        _rt_print(" ")
        _rt_print(-5.000002)
        _rt_print(" ")
        _rt_print(10.0001)
        _rt_print(" ")
        _rt_print(-0.0)

        self.assertEqual(get_print_buffer(), "42 10 -5 10.0001 0")
        _rt_printflush("message1")
        self.assertEqual(get_print_buffer(), "")

    def test_runtime_buffer_nan_and_infinity_format_as_null(self):
        """In Mindustry Logic (LVar.invalid), NaN and Infinity set objval=null, formatting as 'null'."""
        _rt_print(float("nan"))
        _rt_print(" ")
        _rt_print(float("inf"))
        _rt_print(" ")
        _rt_print(float("-inf"))

        self.assertEqual(get_print_buffer(), "null null null")
        _rt_printflush("message1")
        self.assertEqual(get_print_buffer(), "")

    def test_runtime_buffer_enums_and_objects(self):
        """Runtime emulation formats enums to content name and generic objects to [object]."""
        from src.mlog_registry import Items, Units

        _rt_print(Units.FLARE)
        _rt_print(" ")
        _rt_print(Items.COPPER)
        _rt_print(" ")
        _rt_print(object())

        self.assertEqual(get_print_buffer(), "flare copper [object]")
        _rt_printflush("message1")
        self.assertEqual(get_print_buffer(), "")

    def test_runtime_buffer_400_char_limit(self):
        """Runtime print buffer caps at 400 chars; subsequent prints when full are no-ops."""
        _rt_print("A" * 400)
        self.assertEqual(len(get_print_buffer()), 400)
        self.assertEqual(get_print_buffer(), "A" * 400)

        # Subsequent call when already at 400 chars is ignored
        _rt_print("EXTRA")
        self.assertEqual(len(get_print_buffer()), 400)
        self.assertEqual(get_print_buffer(), "A" * 400)

        _rt_printflush("message1")
        self.assertEqual(get_print_buffer(), "")

    def test_runtime_buffer_partial_append_overflow(self):
        """Strings exceeding remaining buffer capacity are truncated to fit maxTextBuffer (400)."""
        _rt_print("A" * 395)
        self.assertEqual(len(get_print_buffer()), 395)

        # Appending 10 chars when only 5 chars remain
        _rt_print("1234567890")
        self.assertEqual(len(get_print_buffer()), 400)
        self.assertEqual(get_print_buffer(), "A" * 395 + "12345")

        _rt_printflush("message1")
        self.assertEqual(get_print_buffer(), "")

    def test_runtime_buffer_single_large_string_clamped_to_400(self):
        """A single string exceeding 400 characters is clamped to exactly 400 characters."""
        _rt_print("X" * 600)
        self.assertEqual(len(get_print_buffer()), 400)
        self.assertEqual(get_print_buffer(), "X" * 400)

        _rt_printflush("message1")
        self.assertEqual(get_print_buffer(), "")

    def test_runtime_printflush_unconditional_clear(self):
        """printflush unconditionally clears the buffer, even with invalid or non-printable targets."""
        # Target is None
        _rt_print("Content 1")
        _rt_printflush(None)
        self.assertEqual(get_print_buffer(), "")

        # Target is integer
        _rt_print("Content 2")
        _rt_printflush(12345)
        self.assertEqual(get_print_buffer(), "")

        # Target is arbitrary string identifier
        _rt_print("Content 3")
        _rt_printflush("router1")
        self.assertEqual(get_print_buffer(), "")

    def test_runtime_printflush_printable_target_delivery(self):
        """printflush delivers accumulated text to LPrintable target object or dict before clearing."""
        class MockMessageBlock:
            def __init__(self):
                self.text = ""

            def print(self, text: str):
                self.text = text

        block = MockMessageBlock()
        _rt_print("Alert: Core under attack!")
        _rt_printflush(block)
        self.assertEqual(block.text, "Alert: Core under attack!")
        self.assertEqual(get_print_buffer(), "")

        # Target dict
        dict_target = {}
        _rt_print("Data status: OK")
        _rt_printflush(dict_target)
        self.assertEqual(dict_target["message"], "Data status: OK")
        self.assertEqual(get_print_buffer(), "")

    def test_escape_sequences_mlog_and_python_roundtrip(self):
        """String literals with escape sequences preserve exact characters across compile and decompile."""
        source = '''from mlog import print, printflush
print("Header:\\nLine 1: \\"quoted\\" and \\\\slash")
printflush("message1")
'''
        res = compile_py(source, filename="test_escape.py", validate=True)
        self.assertIn('print "Header:\\nLine 1: \\"quoted\\" and \\\\slash"', res.mlog)

        py = decompile(res.mlog)
        ast.parse(py)
        self.assertIn('print("Header:\\nLine 1: \\"quoted\\" and \\\\slash")', py)

        recompiled = compile_py(py).mlog.strip()
        self.assertEqual(recompiled, res.mlog.strip())

    def test_java_math_round_simulation_edge_cases(self):
        """Verify _java_math_round matches Java java.lang.Math.round(double a) at x.5, negative, and zero."""
        from src.metadata import _java_math_round

        # Java Math.round(a) = (long)Math.floor(a + 0.5d)
        self.assertEqual(_java_math_round(2.5), 3)
        self.assertEqual(_java_math_round(3.5), 4)
        self.assertEqual(_java_math_round(-2.5), -2)
        self.assertEqual(_java_math_round(-3.5), -3)
        self.assertEqual(_java_math_round(0.5), 1)
        self.assertEqual(_java_math_round(-0.5), 0)
        self.assertEqual(_java_math_round(-1.5), -1)
        self.assertEqual(_java_math_round(-0.0), 0)
        self.assertEqual(_java_math_round(0.0), 0)

        # In _rt_print, non-integer x.5 is not within 0.00001 of an integer, so it emits float string
        _rt_print(2.5)
        _rt_print(" ")
        _rt_print(-1.5)
        _rt_print(" ")
        _rt_print(-0.0)
        self.assertEqual(get_print_buffer(), "2.5 -1.5 0")
        _rt_printflush("message1")

    def test_utf16_code_units_buffer_limit_and_surrogate_pairs(self):
        """Verify buffer limit 400 is measured in Java UTF-16 code units, properly handling non-BMP emojis."""
        from src.metadata import _utf16_len

        rocket = "🚀"  # U+1F680: 1 Python codepoint, 2 Java UTF-16 code units (surrogate pair)
        self.assertEqual(len(rocket), 1)
        self.assertEqual(_utf16_len(rocket), 2)

        # 200 rockets = 400 UTF-16 code units -> fills buffer completely
        _rt_print(rocket * 200)
        self.assertEqual(_utf16_len(get_print_buffer()), 400)
        self.assertEqual(len(get_print_buffer()), 200)  # 200 Python codepoints

        # Subsequent print when at 400 UTF-16 code units is ignored
        _rt_print("EXTRA")
        self.assertEqual(_utf16_len(get_print_buffer()), 400)

        _rt_printflush("message1")
        self.assertEqual(get_print_buffer(), "")

        # Partial append with surrogate split at boundary: 399 code units + 1 rocket (2 code units)
        _rt_print("A" * 399)
        self.assertEqual(_utf16_len(get_print_buffer()), 399)
        _rt_print(rocket)
        # Sliced at 400: receives only high surrogate '\ud83d'
        buf = get_print_buffer()
        self.assertEqual(_utf16_len(buf), 400)
        self.assertEqual(buf[-1], "\ud83d")
        _rt_printflush("message1")

    def test_pipeline_escape_sequences_and_raw_tokens(self):
        """Test escape sequences through Python DSL -> compiler -> assembly -> decompiler."""
        # \n is escaped in assembly; \t is preserved as tab; \" is escaped; \\ is escaped
        source = '''from mlog import print, printflush
print("Line1\\nLine2\\t\\"quote\\"\\\\slash\\u0041")
printflush("message1")
'''
        res = compile_py(source, filename="test_escape_pipe.py", validate=True)
        # Verify assembly representation
        self.assertIn('print "Line1\\nLine2\t\\"quote\\"\\\\slashA"', res.mlog)

        # Verify decompiler representation
        py = decompile(res.mlog)
        ast.parse(py)
        self.assertIn('printflush("message1")', py)

    def test_printflush_destroyed_and_non_printable_targets(self):
        """Verify printflush handles valid, non-printable, null, and destroyed targets correctly."""
        class MockBuilding:
            def __init__(self, printable=True, is_valid=True):
                self._printable = printable
                self.is_valid = is_valid
                self.received = None

            def printable(self):
                return self._printable and self.is_valid

            def print(self, text):
                self.received = text

        # 1. Valid printable block receives text and buffer is cleared
        valid_block = MockBuilding(printable=True, is_valid=True)
        _rt_print("Hello Valid")
        _rt_printflush(valid_block)
        self.assertEqual(valid_block.received, "Hello Valid")
        self.assertEqual(get_print_buffer(), "")

        # 2. Destroyed block (is_valid=False) does not receive text, buffer is cleared
        dead_block = MockBuilding(printable=True, is_valid=False)
        _rt_print("Hello Dead")
        _rt_printflush(dead_block)
        self.assertIsNone(dead_block.received)
        self.assertEqual(get_print_buffer(), "")

        # 3. Non-printable block (e.g. router, printable=False) does not receive text, buffer is cleared
        router_block = MockBuilding(printable=False, is_valid=True)
        _rt_print("Hello Router")
        _rt_printflush(router_block)
        self.assertIsNone(router_block.received)
        self.assertEqual(get_print_buffer(), "")

        # 4. Null target (None) does not crash, buffer is cleared
        _rt_print("Hello Null")
        _rt_printflush(None)
        self.assertEqual(get_print_buffer(), "")

    def test_print_newline_character_output_and_mindustry_execution(self):
        """print('\\n') outputs a newline character in MLog, moving text buffer to a new line."""
        from src.mindustry_validator import is_mindustry_available, validate_with_mindustry

        source = 'from mlog import print, printflush\nprint("Line 1")\nprint("\\n")\nprint("Line 2")\nprintflush("message1")\n'
        res = compile_py(source)
        self.assertIn('print "\\n"', res.mlog)

        # 1. Runtime emulation verification
        self.assertEqual(get_print_buffer(), "")
        _rt_print("Line 1")
        _rt_print("\n")
        _rt_print("Line 2")
        self.assertEqual(get_print_buffer(), "Line 1\nLine 2")
        _rt_printflush("message1")
        self.assertEqual(get_print_buffer(), "")

        # 2. Mindustry JVM engine validation if available
        if is_mindustry_available():
            ok, msg, count = validate_with_mindustry(res.mlog)
            self.assertTrue(ok, f"Mindustry rejected print newline: {msg}")

        # 3. Decompile and roundtrip
        py = decompile(res.mlog)
        self.assertIn('print("\\n")', py)
        recompiled = compile_py(py).mlog.strip()
        self.assertEqual(recompiled, res.mlog.strip())

    def test_print_crlf_normalization_prevents_unclosed_quotes(self):
        """String literals with CRLF/CR are normalized into escaped \\n to avoid Mindustry quote syntax errors."""
        from src.mindustry_validator import is_mindustry_available, validate_with_mindustry

        source = 'from mlog import print\nprint("A\\r\\nB\\rC")\n'
        res = compile_py(source)
        # Emitted MLog must NOT contain raw \r byte (which breaks Mindustry LParser)
        self.assertNotIn("\r", res.mlog)
        self.assertIn('print "A\\nB\\nC"', res.mlog)

        if is_mindustry_available():
            ok, msg, count = validate_with_mindustry(res.mlog)
            self.assertTrue(ok, f"Mindustry rejected normalized CRLF string: {msg}")

    def test_validator_rejects_unterminated_string_literal(self):
        """MlogValidator catches unclosed string literals."""
        from src.validator import MlogValidator, ValidationError

        with self.assertRaises(ValidationError):
            MlogValidator.validate('print "unclosed string')

    def test_printchar_compilation_runtime_and_roundtrip(self):
        """printchar compiles, emulates character buffer append, and round-trips."""
        from src.metadata import _rt_printchar
        from src.mindustry_validator import is_mindustry_available, validate_with_mindustry

        # 1. Compilation
        source = "from mlog import printchar\nprintchar(65)\nprintchar(val)\n"
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(lines[0], "printchar 65")
        self.assertEqual(lines[1], "printchar val")

        # 2. Runtime emulation
        self.assertEqual(get_print_buffer(), "")
        _rt_printchar(65)
        _rt_printchar(66)
        _rt_printchar(67)
        self.assertEqual(get_print_buffer(), "ABC")
        _rt_printflush("message1")
        self.assertEqual(get_print_buffer(), "")

        # 3. Mindustry JVM engine validation if available
        if is_mindustry_available():
            ok, msg, count = validate_with_mindustry(res.mlog)
            self.assertTrue(ok, f"Mindustry rejected printchar: {msg}")

        # 4. Decompile and roundtrip
        py = decompile(res.mlog)
        self.assertIn("printchar(65)", py)
        self.assertIn("printchar(val)", py)
        recompiled = compile_py(py).mlog.strip()
        self.assertEqual(recompiled, res.mlog.strip())

    def test_format_compilation_runtime_and_roundtrip(self):
        """format compiles, emulates placeholder substitution, and round-trips."""
        from src.metadata import _rt_format
        from src.mindustry_validator import is_mindustry_available, validate_with_mindustry

        # 1. Compilation
        source = 'from mlog import print, format, printflush\nprint("val: {0}\\n")\nformat(42)\nprintflush("message1")\n'
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(lines[0], 'print "val: {0}\\n"')
        self.assertEqual(lines[1], "format 42")
        self.assertEqual(lines[2], "printflush message1")

        # 2. Runtime emulation
        self.assertEqual(get_print_buffer(), "")
        _rt_print("Item: {0}, Count: {1}\n")
        _rt_format("copper")
        _rt_format(100)
        self.assertEqual(get_print_buffer(), "Item: copper, Count: 100\n")
        _rt_printflush("message1")
        self.assertEqual(get_print_buffer(), "")

        # 3. Mindustry JVM engine validation if available
        if is_mindustry_available():
            ok, msg, count = validate_with_mindustry(res.mlog)
            self.assertTrue(ok, f"Mindustry rejected format: {msg}")

        # 4. Decompile and roundtrip
        py = decompile(res.mlog)
        self.assertTrue("format(42)" in py or 'f"val: {42}' in py)
        recompiled = compile_py(py).mlog.strip()
        self.assertEqual(recompiled, res.mlog.strip())

        # 5. Standalone format without placeholder preserves format() call
        standalone_res = compile_py('from mlog import format\nformat(42)\n')
        standalone_py = decompile(standalone_res.mlog)
        self.assertIn("format(42)", standalone_py)

    def test_setrate_compilation_and_roundtrip(self):
        """setrate compiles and survives roundtrip."""
        from src.mindustry_validator import is_mindustry_available, validate_with_mindustry

        # 1. Compilation
        source = "from mlog import setrate\nsetrate(60)\nsetrate(target_ipt)\n"
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(lines[0], "setrate 60")
        self.assertEqual(lines[1], "setrate target_ipt")

        # 2. Mindustry JVM engine validation if available
        if is_mindustry_available():
            ok, msg, count = validate_with_mindustry(res.mlog)
            self.assertTrue(ok, f"Mindustry rejected setrate: {msg}")

        # 3. Decompile and roundtrip
        py = decompile(res.mlog)
        self.assertIn("setrate(60)", py)
        self.assertIn("setrate(target_ipt)", py)
        recompiled = compile_py(py).mlog.strip()
        self.assertEqual(recompiled, res.mlog.strip())

    def test_printchar_edge_cases_and_invalid_args(self):
        """printchar rejects bad arity and emulates NaN/Inf/out-of-range correctly."""
        from src.errors import CompileError
        from src.metadata import _rt_printchar

        with self.assertRaises(CompileError):
            compile_py("from mlog import printchar\nprintchar()\n")
        with self.assertRaises(CompileError):
            compile_py("from mlog import printchar\nprintchar(1, 2)\n")

        # Runtime edge cases
        self.assertEqual(get_print_buffer(), "")
        _rt_printchar(float("nan"))
        _rt_printchar(float("inf"))
        _rt_printchar(-1)
        _rt_printchar(0x110000)  # beyond Unicode range
        self.assertEqual(get_print_buffer(), "\0\0\0\0")
        _rt_printflush("message1")
        self.assertEqual(get_print_buffer(), "")

    def test_format_edge_cases_and_invalid_args(self):
        """format rejects bad arity and handles missing/multiple placeholders."""
        from src.errors import CompileError
        from src.metadata import _rt_format

        with self.assertRaises(CompileError):
            compile_py("from mlog import format\nformat()\n")
        with self.assertRaises(CompileError):
            compile_py("from mlog import format\nformat(1, 2)\n")

        # Missing placeholder leaves buffer unchanged
        self.assertEqual(get_print_buffer(), "")
        _rt_print("No placeholder here")
        _rt_format(999)
        self.assertEqual(get_print_buffer(), "No placeholder here")
        _rt_printflush("message1")

        # First placeholder in string order is replaced
        _rt_print("{5} then {2}")
        _rt_format("FIRST")
        self.assertEqual(get_print_buffer(), "FIRST then {2}")
        _rt_format("SECOND")
        self.assertEqual(get_print_buffer(), "FIRST then SECOND")
        _rt_printflush("message1")

    def test_setrate_invalid_args(self):
        """setrate rejects invalid argument counts."""
        from src.errors import CompileError

        with self.assertRaises(CompileError):
            compile_py("from mlog import setrate\nsetrate()\n")
        with self.assertRaises(CompileError):
            compile_py("from mlog import setrate\nsetrate(1, 2)\n")

    def test_mindustry_crlf_reproduction_directly(self):
        """Verify on real Mindustry JVM engine that raw CR causes quote error and normalized CRLF passes."""
        from src.mindustry_validator import is_mindustry_available, validate_with_mindustry

        if not is_mindustry_available():
            self.skipTest("Mindustry engine classes not available")

        # 1. Raw CR byte inside string triggers Missing closing quote error in Mindustry LParser
        raw_cr_mlog = 'print "before\rafter"\n'
        ok, msg, _ = validate_with_mindustry(raw_cr_mlog)
        self.assertFalse(ok)
        self.assertIn("Missing closing quote", msg)

        # 2. Raw CRLF inside string also triggers it
        raw_crlf_mlog = 'print "before\r\nafter"\n'
        ok, msg, _ = validate_with_mindustry(raw_crlf_mlog)
        self.assertFalse(ok)
        self.assertIn("Missing closing quote", msg)

        # 3. Normalized compiler output with escaped \\n passes cleanly
        source = 'from mlog import print\nprint("before\\r\\nafter")\n'
        res = compile_py(source)
        ok, msg, _ = validate_with_mindustry(res.mlog)
        self.assertTrue(ok, f"Mindustry unexpectedly rejected normalized output: {msg}")


if __name__ == "__main__":
    unittest.main()
