"""Regression tests for Python f-string (ast.JoinedStr) formatting in Mindustry Logic.

Verifies:
- Compilation of print(f"...") into MLog `print` and `format` opcodes
- Support for complex expressions and multiple placeholders ({0}..{9})
- Strict preservation of left-to-right evaluation order
- Handling of escape sequences (newline, tab, quotes, backslashes, CRLF)
- Literal braces {{...}} escaping
- Rejection of unsupported format specifiers (:.2f) and conversions (!r, !s, !a)
- Rejection of > 10 placeholders (exceeding Mindustry format opcode capability)
- Rejection of variable assignment, standalone statements, and invalid contexts
- Decompiler recovery of f-strings from print + format sequences
- Full round-trip preservation (Python -> MLog -> Python -> MLog)
- Mindustry JVM engine runtime execution
"""

import unittest
from src.mlog import compile_py, CompileError
from src.decompiler import decompile
from src.mindustry_validator import is_mindustry_available, validate_with_mindustry


class TestFStringCompilation(unittest.TestCase):
    """Test compiler lowering of f-strings into MLog print and format opcodes."""

    def test_simple_fstring_compilation(self):
        """Simple f-string lowers to print template with {0} followed by format."""
        source = 'from mlog import print\nx = 10\nprint(f"Count: {x}")\n'
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(lines[0], "set x 10")
        self.assertEqual(lines[1], 'print "Count: {0}"')
        self.assertEqual(lines[2], "format x")

    def test_multiple_placeholders(self):
        """Multiple placeholders {0}, {1}, {2} are indexed sequentially."""
        source = 'from mlog import print\nprint(f"A: {a}, B: {b}, C: {c}")\n'
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(lines[0], 'print "A: {0}, B: {1}, C: {2}"')
        self.assertEqual(lines[1], "format a")
        self.assertEqual(lines[2], "format b")
        self.assertEqual(lines[3], "format c")

    def test_complex_expressions_and_evaluation_order(self):
        """Expressions are evaluated strictly left-to-right before print and format."""
        source = 'from mlog import print\nprint(f"Sum: {a + 1}, Prod: {b * 2}")\n'
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        # Left expression evaluated first
        self.assertTrue(lines[0].startswith("op add "))
        self.assertIn("a 1", lines[0])
        # Right expression evaluated second
        self.assertTrue(lines[1].startswith("op mul "))
        self.assertIn("b 2", lines[1])
        # Print template
        self.assertEqual(lines[2], 'print "Sum: {0}, Prod: {1}"')
        # Formats in order
        self.assertTrue(lines[3].startswith("format "))
        self.assertTrue(lines[4].startswith("format "))

    def test_content_symbols_and_enums(self):
        """Mindustry DSL content symbols and enums compile to unquoted @content in format."""
        source = 'from mlog import print, Items, Liquids, Units, Vars\nprint(f"Item: {Items.copper}, Liq: {Liquids.water}, Unit: {Units.flare}, T: {Vars.tick}")\n'
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(lines[0], 'print "Item: {0}, Liq: {1}, Unit: {2}, T: {3}"')
        self.assertEqual(lines[1], "format @copper")
        self.assertEqual(lines[2], "format @water")
        self.assertEqual(lines[3], "format @flare")
        self.assertEqual(lines[4], "format @tick")

    def test_constants_in_placeholders(self):
        """Numeric and string constants in placeholders compile properly."""
        source = 'from mlog import print\nprint(f"Num: {42}, Str: {\'hello\'}")\n'
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(lines[0], 'print "Num: {0}, Str: {1}"')
        self.assertEqual(lines[1], "format 42")
        self.assertEqual(lines[2], 'format "hello"')

    def test_escape_sequences_and_quotes(self):
        """Newlines, tabs, backslashes, and quotes are escaped safely for Mindustry."""
        source = 'from mlog import print\nprint(f"Line 1\\nLine 2:\t{x}\\nPath: \\\\dir\\\\ \\"quote\\"")\n'
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(lines[0], 'print "Line 1\\nLine 2:\t{0}\\nPath: \\\\dir\\\\ \\"quote\\""')
        self.assertEqual(lines[1], "format x")

    def test_crlf_normalization(self):
        """CRLF inside f-strings is normalized to \\n, preventing Mindustry parser errors."""
        source = 'from mlog import print\nprint(f"""Line1\r\nLine2: {x}""")\n'
        res = compile_py(source)
        self.assertNotIn("\r", res.mlog)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(lines[0], 'print "Line1\\nLine2: {0}"')
        self.assertEqual(lines[1], "format x")

    def test_literal_braces_escaping(self):
        """Doubled braces {{...}} in Python f-string become single braces in MLog."""
        source = 'from mlog import print\nprint(f"Literal {{hello}} and {x}")\n'
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(lines[0], 'print "Literal {hello} and {0}"')
        self.assertEqual(lines[1], "format x")

    def test_literal_braces_around_variable(self):
        """f'{{{x}}}' correctly compiles to single braces around formatted value in MLog."""
        source = 'from mlog import print\nx = 5\nprint(f"{{{x}}}")\n'
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(lines[0], "set x 5")
        self.assertEqual(lines[1], 'print "{{0}}"')
        self.assertEqual(lines[2], "format x")
        py = decompile(res.mlog)
        self.assertIn('print(f"{{{x}}}")', py)

    def test_evaluation_order_with_side_effects(self):
        """When an expression has side effects, preceding variables are snapshotted."""
        source = (
            "from mlog import print, getlink\n"
            "x = 10\n"
            "print(f'{x} {getlink(0)}')\n"
        )
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(lines[0], "set x 10")
        self.assertTrue(lines[1].startswith("set __tmp") and lines[1].endswith(" x"))
        self.assertTrue(lines[2].startswith("getlink "))
        self.assertEqual(lines[3], 'print "{0} {1}"')
        self.assertTrue(lines[4].startswith("format __tmp"))

    def test_zero_placeholders(self):
        """f-string with no placeholders compiles to a standard print statement."""
        source = 'from mlog import print\nprint(f"Hello world")\n'
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(lines[0], 'print "Hello world"')
        self.assertEqual(len(lines), 1)

    def test_up_to_10_placeholders_supported(self):
        """Exactly 10 placeholders {0} through {9} compile without error."""
        source = 'from mlog import print\nprint(f"{p0}{p1}{p2}{p3}{p4}{p5}{p6}{p7}{p8}{p9}")\n'
        res = compile_py(source)
        lines = res.mlog.strip().splitlines()
        self.assertEqual(lines[0], 'print "{0}{1}{2}{3}{4}{5}{6}{7}{8}{9}"')
        for i in range(10):
            self.assertEqual(lines[i + 1], f"format p{i}")


class TestFStringErrorHandling(unittest.TestCase):
    """Test validation errors for unsupported or invalid f-string constructs."""

    def test_format_specifier_rejected(self):
        """Format specifiers like :.2f or :>10 raise a descriptive CompileError."""
        source = 'from mlog import print\nprint(f"Val: {x:.2f}")\n'
        with self.assertRaises(CompileError) as ctx:
            compile_py(source)
        self.assertIn("format specifiers", str(ctx.exception))

    def test_conversion_flags_rejected(self):
        """Conversion flags !s, !r, !a raise a descriptive CompileError."""
        for flag in ("!s", "!r", "!a"):
            source = f'from mlog import print\nprint(f"Val: {{x{flag}}}")\n'
            with self.assertRaises(CompileError) as ctx:
                compile_py(source)
            self.assertIn("conversions", str(ctx.exception))

    def test_exceeding_10_placeholders_rejected(self):
        """More than 10 expressions (> 10 placeholders) raises CompileError."""
        source = 'from mlog import print\nprint(f"{p0}{p1}{p2}{p3}{p4}{p5}{p6}{p7}{p8}{p9}{p10}")\n'
        with self.assertRaises(CompileError) as ctx:
            compile_py(source)
        self.assertIn("at most 10 expressions", str(ctx.exception))

    def test_literal_placeholder_syntax_rejected(self):
        """Literal {0}..{9} in f-string with expressions raises CompileError."""
        source = 'from mlog import print\nprint(f"literal {{0}} and {x}")\n'
        with self.assertRaises(CompileError) as ctx:
            compile_py(source)
        self.assertIn("matching placeholder syntax", str(ctx.exception))

    def test_variable_assignment_rejected(self):
        """Assigning an f-string to a variable raises CompileError."""
        source = 'x = 10\ns = f"Count: {x}"\n'
        with self.assertRaises(CompileError) as ctx:
            compile_py(source)
        self.assertIn("cannot be assigned to variables", str(ctx.exception))

    def test_aug_assign_rejected(self):
        """Augmented assignment of an f-string raises CompileError."""
        source = 's = "abc"\ns += f"Count: {x}"\n'
        with self.assertRaises(CompileError) as ctx:
            compile_py(source)
        self.assertIn("cannot be assigned to variables", str(ctx.exception))

    def test_standalone_fstring_statement_rejected(self):
        """A bare f-string statement outside print raises CompileError."""
        source = 'x = 10\nf"Count: {x}"\n'
        with self.assertRaises(CompileError) as ctx:
            compile_py(source)
        self.assertIn("standalone statements", str(ctx.exception))

    def test_fstring_in_other_intrinsics_rejected(self):
        """f-string passed to non-print intrinsics raises CompileError."""
        source = 'from mlog import draw\ndraw("clear", f"color: {col}")\n'
        with self.assertRaises(CompileError) as ctx:
            compile_py(source)
        self.assertIn("not supported in 'draw()'", str(ctx.exception))


class TestFStringDecompilationAndRoundtrip(unittest.TestCase):
    """Test decompiler recovery of f-strings and round-trip preservation."""

    def test_decompile_simple_fstring(self):
        """MLog print template + format decompiles into Python print(f"...")."""
        mlog = 'set x 10\nprint "Count: {0}"\nformat x\n'
        py = decompile(mlog)
        self.assertIn('print(f"Count: {x}")', py)

    def test_decompile_multiple_placeholders(self):
        """MLog print with multiple placeholders decompiles into multiple f-string expressions."""
        mlog = 'print "X: {0}, Y: {1}"\nformat a\nformat b\n'
        py = decompile(mlog)
        self.assertIn('print(f"X: {a}, Y: {b}")', py)

    def test_decompile_expression_inlining_in_fstring(self):
        """Temporary arithmetic variables are inlined directly into f-string placeholders."""
        mlog = 'op add __tmp0 x 1\nop mul __tmp1 y 2\nprint "X: {0}, Y: {1}"\nformat __tmp0\nformat __tmp1\n'
        py = decompile(mlog)
        self.assertIn('print(f"X: {x + 1}, Y: {y * 2}")', py)

    def test_decompile_content_symbols_in_fstring(self):
        """Content symbols like @copper decompile to Items.copper in f-strings."""
        mlog = 'print "Cost: {0}"\nformat @copper\n'
        py = decompile(mlog)
        self.assertIn('print(f"Cost: {Items.copper}")', py)
        self.assertIn("from mlog import Items", py)

    def test_standalone_format_preserved(self):
        """format() without preceding template print remains format(x)."""
        mlog = 'format x\n'
        py = decompile(mlog)
        self.assertIn('format(x)', py)

    def test_disconnected_print_and_format_preserved(self):
        """print and format with intervening instructions are NOT merged into f-string."""
        mlog = 'print "val: {0}"\nset y 20\nformat x\n'
        py = decompile(mlog)
        self.assertIn('print("val: {0}")', py)
        self.assertIn('format(x)', py)

    def test_decompiler_dangling_placeholders_not_misidentified(self):
        """Consecutive prints with dangling placeholders do not get misidentified."""
        mlog = 'print "A: {0}"\nprint "B: {0}"\nformat x\nformat y\n'
        py = decompile(mlog)
        self.assertIn('print("A: {0}")', py)
        self.assertIn('print("B: {0}")', py)
        self.assertIn('format(x)', py)
        self.assertIn('format(y)', py)

    def test_decompiler_out_of_order_placeholders_not_merged(self):
        """Out of order placeholders {1} then {0} are not merged into f-string."""
        mlog = 'print "X: {1}, Y: {0}"\nformat a\nformat b\n'
        py = decompile(mlog)
        self.assertIn('print("X: {1}, Y: {0}")', py)
        self.assertIn('format(a)', py)
        self.assertIn('format(b)', py)

    def test_full_roundtrip_fstring(self):
        """f-string compiles, decompiles, and recompiles with 100% MLog equivalence."""
        source = 'from mlog import print\nx = 10\ny = 20\nprint(f"X: {x + 1}, Y: {y * 2}")\n'
        res = compile_py(source)
        py = decompile(res.mlog)
        recompiled = compile_py(py).mlog.strip()
        self.assertEqual(recompiled, res.mlog.strip())

    def test_mindustry_jvm_validation_if_available(self):
        """f-string compiled MLog validates in real Mindustry v160.7 JVM engine."""
        if not is_mindustry_available():
            self.skipTest("Mindustry Java runtime not available")
        source = 'from mlog import print, printflush\nx = 42\nprint(f"Result: {x}\\n")\nprintflush("message1")\n'
        res = compile_py(source)
        ok, msg, count = validate_with_mindustry(res.mlog)
        self.assertTrue(ok, f"Mindustry JVM rejected f-string MLog: {msg}")


if __name__ == "__main__":
    unittest.main()
