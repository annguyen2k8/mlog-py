"""Byte-for-byte reproducibility tests for the shipped compiler examples.

Each `examples/compiler/*.py` must compile to exactly its companion `*.mlog`, and the
same result must be reachable through the `mlog-py compile` CLI. The CLI compiles with
function support enabled (see tests/test_cli_functions.py), matching the DSL spec.
"""

import glob
import io
import os
import unittest
from contextlib import redirect_stdout

from src.mlog import compile_py, main


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES_DIR = os.path.join(REPO_ROOT, "examples", "compiler")

# roundtrip_demo.py is an interactive runner, not a compilable example.
SKIPPED = {"roundtrip_demo.py"}


def _example_pairs():
    """Yield (name, python_path, mlog_path) for every paired compiler example."""
    for py_path in sorted(glob.glob(os.path.join(EXAMPLES_DIR, "*.py"))):
        name = os.path.basename(py_path)
        if name in SKIPPED:
            continue
        mlog_path = py_path[:-3] + ".mlog"
        if not os.path.exists(mlog_path):
            continue
        yield name, py_path, mlog_path


class TestCompilerExamplesByteForByte(unittest.TestCase):
    """Every shipped compiler example must stay byte-for-byte reproducible."""

    def test_at_least_one_example_is_covered(self):
        pairs = list(_example_pairs())
        self.assertGreaterEqual(len(pairs), 19, "compiler example discovery failed")

    def test_examples_match_their_mlog_byte_for_byte(self):
        for name, py_path, mlog_path in _example_pairs():
            with self.subTest(example=name):
                with open(py_path, "r", encoding="utf-8") as f:
                    source = f.read()
                with open(mlog_path, "r", encoding="utf-8") as f:
                    expected = f.read()

                result = compile_py(source, filename=py_path, allow_functions=True)
                self.assertEqual(
                    result.mlog.strip(),
                    expected.strip(),
                    f"{name} no longer compiles to its committed .mlog",
                )

    def test_cli_output_matches_committed_mlog_for_every_example(self):
        old_env = os.environ.get("MLOG_NO_CLIPBOARD")
        os.environ["MLOG_NO_CLIPBOARD"] = "1"
        try:
            for name, py_path, mlog_path in _example_pairs():
                with self.subTest(example=name):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        code = main(["compile", py_path, "--no-clipboard"])
                    with open(mlog_path, "r", encoding="utf-8") as f:
                        expected = f.read()

                    self.assertEqual(code, 0, f"{name} failed to compile through the CLI")
                    self.assertEqual(buf.getvalue().strip(), expected.strip())

                    # '-o' must write exactly the same bytes as stdout.
                    out_path = os.path.join(EXAMPLES_DIR, ".__verify_tmp.mlog")
                    try:
                        with redirect_stdout(io.StringIO()):
                            code = main(["compile", py_path, "-o", out_path, "--no-clipboard"])
                        self.assertEqual(code, 0)
                        with open(out_path, "r", encoding="utf-8") as f:
                            self.assertEqual(f.read().strip(), expected.strip())
                    finally:
                        if os.path.exists(out_path):
                            os.remove(out_path)
        finally:
            if old_env is None:
                os.environ.pop("MLOG_NO_CLIPBOARD", None)
            else:
                os.environ["MLOG_NO_CLIPBOARD"] = old_env

    def test_every_compiler_example_is_listed_in_examples_readme(self):
        readme_path = os.path.join(REPO_ROOT, "examples", "README.md")
        with open(readme_path, "r", encoding="utf-8") as f:
            readme = f.read()
        for name, _py_path, _mlog_path in _example_pairs():
            with self.subTest(example=name):
                self.assertIn(f"compiler/{name}", readme, f"{name} missing from examples/README.md")


if __name__ == "__main__":
    unittest.main()