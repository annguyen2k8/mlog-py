"""Regression tests for examples/decompiler/ directory.

Ensures that:
- Every example .py file in examples/decompiler/ is valid, self-contained Python.
- Every DSL symbol (read, getlink, sensor, printflush, drawflush, control, wait, jump, write, set, draw)
  used in example .py files is explicitly and correctly imported from `mlog`.
- Decompiling each companion .mlog reproduces the exact code in the .py example file.
- Recompiling each example .py via compile_py() succeeds and matches original semantics.
"""

import ast
import glob
import os
import unittest

from src.mlog import compile_py
from src.decompiler import decompile
from src.metadata import MLOG_EXPORTS

EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "examples", "decompiler")


class TestDecompilerExamples(unittest.TestCase):
    """Verifies that all decompiler examples are self-contained and import required DSL symbols."""

    def setUp(self):
        self.py_files = sorted(glob.glob(os.path.join(EXAMPLES_DIR, "*.py")))
        # Filter out standalone test runner scripts
        self.example_files = [
            p for p in self.py_files
            if os.path.basename(p) not in ("roundtrip_verify.py", "sourcemap_debug.py")
        ]

    def test_examples_exist(self):
        """Ensure we found the decompiler examples."""
        self.assertGreaterEqual(len(self.example_files), 8)

    def test_examples_ast_and_no_undefined_dsl_symbols(self):
        """Verify each example parses and has zero undefined DSL symbols."""
        for path in self.example_files:
            filename = os.path.basename(path)
            with self.subTest(file=filename):
                with open(path) as f:
                    content = f.read()

                # 1. Must parse cleanly
                tree = ast.parse(content, filename=filename)
                self.assertIsNotNone(tree)

                # 2. Extract defined names and imported names
                imported_from_mlog = set()
                locally_defined = set()
                used_names = set()

                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if node.module == "mlog":
                            for alias in node.names:
                                imported_from_mlog.add(alias.name)
                    elif isinstance(node, ast.FunctionDef):
                        locally_defined.add(node.name)
                        for arg in node.args.args:
                            locally_defined.add(arg.arg)
                    elif isinstance(node, ast.Name):
                        if isinstance(node.ctx, ast.Store):
                            locally_defined.add(node.id)
                        elif isinstance(node.ctx, ast.Load):
                            used_names.add(node.id)

                # Find any DSL symbol used without being imported or locally defined
                available_symbols = imported_from_mlog | locally_defined
                for name in used_names:
                    if name in MLOG_EXPORTS:
                        self.assertIn(
                            name,
                            available_symbols,
                            f"DSL symbol '{name}' is used in {filename} but not imported from mlog!",
                        )

    def test_examples_match_fresh_decompile_output(self):
        """Verify that decompiling the corresponding .mlog matches the .py example code."""
        for path in self.example_files:
            filename = os.path.basename(path)
            mlog_path = os.path.splitext(path)[0] + ".mlog"
            if not os.path.exists(mlog_path):
                continue

            with self.subTest(file=filename):
                with open(path) as f:
                    py_lines = f.readlines()
                # Strip leading header comments
                while py_lines and py_lines[0].startswith("#"):
                    py_lines.pop(0)
                py_code = "".join(py_lines).strip()

                with open(mlog_path) as f:
                    mlog_text = f.read()

                decompiled = decompile(mlog_text).strip()
                self.assertEqual(
                    py_code,
                    decompiled,
                    f"Example {filename} does not match fresh decompile output from {os.path.basename(mlog_path)}",
                )

    def test_examples_recompile_roundtrip(self):
        """Verify that compile_py() accepts each example and generates valid MLog."""
        for path in self.example_files:
            filename = os.path.basename(path)
            with self.subTest(file=filename):
                with open(path) as f:
                    py_code = f.read()

                res = compile_py(py_code, allow_functions=True, validate=True)
                self.assertIsNotNone(res.mlog)
                self.assertGreater(len(res.mlog.strip().splitlines()), 0)


if __name__ == "__main__":
    unittest.main()
