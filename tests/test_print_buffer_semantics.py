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

from src.compiler import compile_source_to_ir
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

    def test_print_variable_compilation(self):
        """Printing variables emits raw variable identifiers without quotes."""
        source = """from mlog import print, printflush
count = 10
print("Count: ")
print(count)
printflush("message1")
"""
        res = compile_py(source, filename="test_var_print.py", validate=True)
        mlog = res.mlog.strip()
        self.assertIn('print "Count: "', mlog)
        self.assertIn('print count', mlog)
        self.assertIn('printflush message1', mlog)


if __name__ == "__main__":
    unittest.main()
