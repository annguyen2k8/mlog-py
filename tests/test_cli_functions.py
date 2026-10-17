"""Regression tests for function definition support through the CLI entry points.

Root cause under test: `src.mlog._cli_compile()` never forwarded function support to
`compile_py()`, so the AST whitelist (src/parser.py) rejected every `def` statement with
"unsupported Python feature: function definition" even though the compiler fully supports
user-defined functions (`allow_functions=True`).

These tests drive the real `main()` CLI argv so the whole routing path
(CLI -> compile_py -> parse_and_validate -> Compiler) is exercised end to end.
"""

import os
import subprocess
import sys
import tempfile
import unittest

from src.errors import CompileError
from src.mlog import compile_py, main


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FUNCTION_SOURCE = """\
# Function Definition and Parameter Passing
def multiply_add(a, b, c):
    prod = a * b
    return prod + c

ans = multiply_add(5, 6, 7)
"""

EXPECTED_MLOG = """\
jump 5 always 0 0
op mul prod a b
op add __tmp0 prod c
set __retval_multiply_add __tmp0
set @counter __ret_multiply_add
set a 5
set b 6
set c 7
set __ret_multiply_add 10
jump 1 always 0 0
set ans __retval_multiply_add
"""


class TestCliFunctionSupport(unittest.TestCase):
    """CLI must accept function definitions by default, matching the API contract."""

    def _run_cli(self, argv):
        """Run the CLI in-process, capturing stdout and forcing no clipboard side effects."""
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        old_env = os.environ.get("MLOG_NO_CLIPBOARD")
        os.environ["MLOG_NO_CLIPBOARD"] = "1"
        try:
            with redirect_stdout(buf):
                code = main(argv)
        finally:
            if old_env is None:
                os.environ.pop("MLOG_NO_CLIPBOARD", None)
            else:
                os.environ["MLOG_NO_CLIPBOARD"] = old_env
        return code, buf.getvalue()

    def test_cli_compile_subcommand_accepts_function_definitions(self):
        """Regression: 'compile script.py' must not report 'unsupported Python feature'."""
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "functions.py")
            with open(src, "w", encoding="utf-8") as f:
                f.write(FUNCTION_SOURCE)

            code, out = self._run_cli(["compile", src, "--no-clipboard"])

        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), EXPECTED_MLOG.strip())

    def test_cli_default_subcommand_accepts_function_definitions(self):
        """The backward-compatible implicit 'compile' path must behave identically."""
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "functions.py")
            with open(src, "w", encoding="utf-8") as f:
                f.write(FUNCTION_SOURCE)

            code, out = self._run_cli([src, "--no-clipboard"])

        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), EXPECTED_MLOG.strip())

    def test_cli_output_file_matches_in_process_stdout(self):
        """'-o file.mlog' must produce exactly the bytes printed to stdout."""
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "functions.py")
            out_file = os.path.join(tmp, "functions.mlog")
            with open(src, "w", encoding="utf-8") as f:
                f.write(FUNCTION_SOURCE)

            code_stdout, stdout_text = self._run_cli(["compile", src, "--no-clipboard"])
            code_file, _ = self._run_cli(["compile", src, "-o", out_file, "--no-clipboard"])
            with open(out_file, "r", encoding="utf-8") as f:
                file_text = f.read()

        self.assertEqual(code_stdout, 0)
        self.assertEqual(code_file, 0)
        self.assertEqual(file_text.strip(), stdout_text.strip())
        self.assertEqual(file_text.strip(), EXPECTED_MLOG.strip())

    def test_cli_no_functions_flag_rejects_function_definitions(self):
        """'--no-functions' is the explicit opt-out back to the function-free subset."""
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "functions.py")
            with open(src, "w", encoding="utf-8") as f:
                f.write(FUNCTION_SOURCE)

            code, _ = self._run_cli(["compile", src, "--no-functions", "--no-clipboard"])

        self.assertEqual(code, 1)

    def test_cli_no_functions_flag_still_compiles_plain_programs(self):
        """'--no-functions' must not regress function-free programs."""
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "plain.py")
            with open(src, "w", encoding="utf-8") as f:
                f.write("from mlog import print\nx = 2 + 3\nprint(x)\n")

            code, out = self._run_cli(["compile", src, "--no-functions", "--no-clipboard"])

        self.assertEqual(code, 0)
        self.assertIn("set x 5", out)

    def test_api_default_still_rejects_function_definitions(self):
        """compile_py() keeps allow_functions=False by default (opt-in for API callers)."""
        with self.assertRaises(CompileError) as ctx:
            compile_py(FUNCTION_SOURCE, filename="functions.py")
        self.assertIn("unsupported Python feature: function definition", str(ctx.exception))

    def test_repository_function_example_is_reproducible_from_cli(self):
        """The shipped examples/compiler/functions.py must compile through the CLI."""
        example = os.path.join(REPO_ROOT, "examples", "compiler", "functions.py")
        expected_file = os.path.join(REPO_ROOT, "examples", "compiler", "functions.mlog")

        code, out = self._run_cli(["compile", example, "--no-clipboard"])

        self.assertEqual(code, 0)
        with open(expected_file, "r", encoding="utf-8") as f:
            self.assertEqual(out.strip(), f.read().strip())

    def test_standalone_compiler_script_accepts_function_definitions(self):
        """The repo-root compiler.py wrapper must accept function definitions too."""
        script = os.path.join(REPO_ROOT, "compiler.py")
        env = dict(os.environ)
        env["MLOG_NO_CLIPBOARD"] = "1"
        env["PYTHONPATH"] = REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")

        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "functions.py")
            with open(src, "w", encoding="utf-8") as f:
                f.write(FUNCTION_SOURCE)
            proc = subprocess.run(
                [sys.executable, script, src],
                capture_output=True,
                text=True,
                cwd=tmp,
                env=env,
                timeout=120,
            )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), EXPECTED_MLOG.strip())


if __name__ == "__main__":
    unittest.main()