"""Regression tests for Python comment-to-print transformation and Mindustry buffer limit."""

import os
import subprocess
import sys
import unittest

from src.comments import (
    MAX_MINDUSTRY_TEXT_BUFFER,
    has_comments_to_print_pragma,
    transform_comments_to_print,
)
from src.decompiler import decompile
from src.mlog import compile_py
from src.validator import MlogValidator


class TestCommentToPrint(unittest.TestCase):
    """Test opt-in comment-to-print transformation, escaping, buffer limits, and CLI."""

    def test_default_comments_ignored(self):
        """When comments_to_print is False and no pragma exists, comments are not converted to print."""
        source = (
            "# This is a standard comment\n"
            "x = 10\n"
            "# Another comment\n"
            "y = 20\n"
        )
        res = compile_py(source, comments_to_print=False)
        self.assertNotIn("print", res.mlog)
        self.assertIn("set x 10", res.mlog)
        self.assertIn("set y 20", res.mlog)

    def test_opt_in_via_compiler_argument(self):
        """Passing comments_to_print=True converts comments to print."""
        source = (
            "# Initialization\n"
            "x = 10\n"
        )
        res = compile_py(source, comments_to_print=True)
        self.assertIn('print "Initialization"', res.mlog)
        self.assertIn("set x 10", res.mlog)

    def test_opt_in_via_pragma_hyphen(self):
        """Source with '# mlog: comments-to-print' activates comment conversion automatically."""
        source = (
            "# mlog: comments-to-print\n"
            "# System ready\n"
            "x = 1\n"
        )
        res = compile_py(source)
        self.assertIn('print "System ready"', res.mlog)
        # Pragma directive itself must not be printed
        self.assertNotIn("comments-to-print", res.mlog)

    def test_opt_in_via_pragma_underscore(self):
        """Source with '# mlog: comments_to_print' activates comment conversion automatically."""
        source = (
            "# mlog: comments_to_print\n"
            "# System online\n"
            "x = 1\n"
        )
        res = compile_py(source)
        self.assertIn('print "System online"', res.mlog)
        self.assertNotIn("comments_to_print", res.mlog)

    def test_multiline_comments_grouped_with_newline(self):
        """Consecutive standalone comment lines are grouped into a single print with newline."""
        source = (
            "# mlog: comments-to-print\n"
            "# Header: System Status\n"
            "# Section 1: Memory Check\n"
            "# Section 2: Reactor Online\n"
            "x = 100\n"
        )
        res = compile_py(source)
        expected_print = 'print "Header: System Status\\nSection 1: Memory Check\\nSection 2: Reactor Online"'
        self.assertIn(expected_print, res.mlog)
        # Must only emit 1 print instruction for the multi-line block
        self.assertEqual(res.mlog.count("print"), 1)

    def test_separated_comments_not_grouped(self):
        """Comment blocks separated by code or blank lines emit separate print instructions."""
        source = (
            "# mlog: comments-to-print\n"
            "# Block 1\n"
            "\n"
            "# Block 2\n"
            "x = 10\n"
        )
        res = compile_py(source)
        self.assertIn('print "Block 1"', res.mlog)
        self.assertIn('print "Block 2"', res.mlog)
        self.assertEqual(res.mlog.count("print"), 2)

    def test_special_characters_and_escaping(self):
        """Double quotes, single quotes, backslashes, Unicode, and emojis are preserved and escaped safely."""
        source = (
            "# mlog: comments-to-print\n"
            '# Message with "Double Quotes" and \'Single Quotes\'\n'
            r"# Path with backslash: C:\mindustry\logic" + "\n"
            "# Unicode stars: ★★★ and emoji: 🚀🔥\n"
            "x = 0\n"
        )
        res = compile_py(source)
        # Must pass MlogValidator without error
        MlogValidator.validate(res.mlog)
        expected_fragment = 'print "Message with \\"Double Quotes\\" and \'Single Quotes\'\\nPath with backslash: C:\\\\mindustry\\\\logic\\nUnicode stars: ★★★ and emoji: 🚀🔥"'
        self.assertIn(expected_fragment, res.mlog)


    def test_buffer_capacity_limit_chunking_400(self):
        """Comments exceeding Mindustry's 400-char buffer limit are chunked into <= 400 char slices."""
        long_comment_text = "A" * 950
        source = (
            "# mlog: comments-to-print\n"
            f"# {long_comment_text}\n"
            "x = 0\n"
        )
        res = compile_py(source)
        MlogValidator.validate(res.mlog)

        # 950 chars chunked into 400 + 400 + 150 = 3 print instructions
        self.assertEqual(res.mlog.count("print"), 3)
        for line in res.mlog.strip().splitlines():
            if line.startswith("print "):
                # Extract quoted content
                content = line[len('print "'):-1]
                self.assertLessEqual(len(content.replace(r'\"', '"').replace(r'\\', '\\')), MAX_MINDUSTRY_TEXT_BUFFER)

    def test_inline_comments_on_assignments(self):
        """Inline comments on assignment statements emit print and preserve assignment."""
        source = (
            "# mlog: comments-to-print\n"
            "x = 10  # init width\n"
            "y = 20  # init height\n"
        )
        res = compile_py(source)
        self.assertIn('print "init width"', res.mlog)
        self.assertIn("set x 10", res.mlog)
        self.assertIn('print "init height"', res.mlog)
        self.assertIn("set y 20", res.mlog)

    def test_inline_comments_on_compound_statements(self):
        """Inline comments on compound statements (if, while) emit print before the block."""
        source = (
            "# mlog: comments-to-print\n"
            "if x > 0:  # check positive\n"
            "    y = 1\n"
        )
        res = compile_py(source)
        self.assertIn('print "check positive"', res.mlog)
        self.assertIn("set y 1", res.mlog)

    def test_docstring_as_comment_to_print(self):
        """Standalone triple-quoted docstrings are converted to print when comments_to_print is True."""
        source = (
            '"""This is a docstring comment\n'
            'spanning multiple lines"""\n'
            "x = 10\n"
        )
        res = compile_py(source, comments_to_print=True)
        self.assertIn('print "This is a docstring comment\\nspanning multiple lines"', res.mlog)
        self.assertIn("set x 10", res.mlog)

    def test_docstring_ignored_when_disabled(self):
        """Standalone triple-quoted docstrings are ignored when comments_to_print is False."""
        source = (
            '"""This is a docstring comment\n'
            'spanning multiple lines"""\n'
            "x = 10\n"
        )
        res = compile_py(source, comments_to_print=False)
        self.assertNotIn("print", res.mlog)
        self.assertIn("set x 10", res.mlog)

    def test_roundtrip_compile_decompile_compile(self):
        """Comments compiled to print decompile to print calls and recompile to identical mlog."""
        source = (
            "# mlog: comments-to-print\n"
            "# Step 1\n"
            "# Step 2\n"
            "x = 10\n"
        )
        res1 = compile_py(source)
        py = decompile(res1.mlog)
        self.assertIn('print("Step 1\\nStep 2")', py)

        res2 = compile_py(py)
        self.assertEqual(res1.mlog.strip(), res2.mlog.strip())

    def test_cli_comments_to_print_flag(self):
        """CLI compile subcommand accepts --comments-to-print flag."""
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f_py:
            f_py.write("# CLI Comment\nx = 42\n")
            py_path = f_py.name

        with tempfile.NamedTemporaryFile("w", suffix=".mlog", delete=False, encoding="utf-8") as f_mlog:
            mlog_path = f_mlog.name

        try:
            cmd = [
                sys.executable,
                "-m",
                "src.mlog",
                "compile",
                py_path,
                "-o",
                mlog_path,
                "--comments-to-print",
                "--no-clipboard",
            ]
            run_res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(run_res.returncode, 0, msg=run_res.stderr)

            with open(mlog_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn('print "CLI Comment"', content)
            self.assertIn("set x 42", content)
        finally:
            if os.path.exists(py_path):
                os.remove(py_path)
            if os.path.exists(mlog_path):
                os.remove(mlog_path)



if __name__ == "__main__":
    unittest.main()
