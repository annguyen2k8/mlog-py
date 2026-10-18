"""Unit and regression tests for CLI decompile stdin and interactive copy-paste support."""

import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from src.mlog import main


class TestCliDecompileStdin(unittest.TestCase):
    """Tests for mlog-py decompile with stdin, pipe, interactive paste, and error handling."""

    def _run_cli_capture(self, argv, stdin_data="", is_tty=False):
        """Run the CLI main() with mocked stdin, capturing stdout and stderr."""
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()

        class MockStdin(io.StringIO):
            def isatty(self):
                return is_tty

        mock_in = MockStdin(stdin_data)

        old_stdin, old_stdout, old_stderr = sys.stdin, sys.stdout, sys.stderr
        try:
            sys.stdin = mock_in
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                exit_code = main(argv)
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        return exit_code, stdout_buf.getvalue(), stderr_buf.getvalue()

    def test_piped_stdin_decompile(self):
        """Piping mlog directly into 'mlog-py decompile' produces Python DSL on stdout."""
        mlog = "set a 10\nset b 20\nop add c a b\n"
        code, stdout, stderr = self._run_cli_capture(["decompile"], stdin_data=mlog, is_tty=False)
        self.assertEqual(code, 0)
        self.assertIn("a = 10", stdout)
        self.assertIn("b = 20", stdout)
        self.assertIn("c = a + b", stdout)
        self.assertEqual(stderr, "")

    def test_piped_stdin_with_dash_argument(self):
        """'mlog-py decompile -' explicitly denotes stdin and works identically."""
        mlog = "set counter 42\n"
        code, stdout, stderr = self._run_cli_capture(["decompile", "-"], stdin_data=mlog, is_tty=False)
        self.assertEqual(code, 0)
        self.assertIn("counter = 42", stdout)
        self.assertEqual(stderr, "")

    def test_interactive_mode_prompts_to_stderr_and_reads_until_stream_eof(self):
        """When stdin is a TTY, instructions are printed to stderr, not contaminating stdout."""
        mlog = "set status 1\n"
        code, stdout, stderr = self._run_cli_capture(["decompile"], stdin_data=mlog, is_tty=True)
        self.assertEqual(code, 0)
        self.assertIn("[mlog-py] Paste or enter mlog code below.", stderr)
        self.assertIn("status = 1", stdout)
        self.assertNotIn("[mlog-py]", stdout)

    def test_interactive_mode_stops_at_eof_sentinel(self):
        """Typing 'EOF' on an empty line cleanly stops input reading."""
        mlog = "set x 100\nEOF\nset x 999\n"
        code, stdout, stderr = self._run_cli_capture(["decompile"], stdin_data=mlog, is_tty=True)
        self.assertEqual(code, 0)
        self.assertIn("x = 100", stdout)
        self.assertNotIn("999", stdout)

    def test_interactive_mode_stops_at_double_underscore_eof_sentinel(self):
        """Typing '__EOF__' on an empty line cleanly stops input reading."""
        mlog = "set msg \"hello\"\n__EOF__\nignored code\n"
        code, stdout, stderr = self._run_cli_capture(["decompile"], stdin_data=mlog, is_tty=True)
        self.assertEqual(code, 0)
        self.assertIn('msg = "hello"', stdout)
        self.assertNotIn("ignored", stdout)

    def test_empty_stdin_reports_error_and_exits_code_1(self):
        """Empty input exits with code 1 and an explicit error message on stderr without hanging."""
        code, stdout, stderr = self._run_cli_capture(["decompile"], stdin_data="", is_tty=False)
        self.assertEqual(code, 1)
        self.assertIn("Decompilation error: input is empty", stderr)
        self.assertEqual(stdout, "")

    def test_whitespace_only_stdin_reports_error(self):
        """Whitespace/blank lines only input exits with code 1 and error on stderr."""
        code, stdout, stderr = self._run_cli_capture(["decompile"], stdin_data="   \n\n\t  \n", is_tty=False)
        self.assertEqual(code, 1)
        self.assertIn("Decompilation error: input is empty", stderr)

    def test_decompile_output_file_flag(self):
        """'-o <file>' flag writes python output to disk instead of stdout."""
        mlog = "set val 5\n"
        with tempfile.TemporaryDirectory() as tmp:
            out_file = os.path.join(tmp, "out.py")
            code, stdout, stderr = self._run_cli_capture(
                ["decompile", "-o", out_file],
                stdin_data=mlog,
                is_tty=False,
            )
            self.assertEqual(code, 0)
            self.assertEqual(stdout, "")
            self.assertTrue(os.path.exists(out_file))
            with open(out_file, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("val = 5", content)

    def test_backward_compatible_file_argument(self):
        """'mlog-py decompile file.mlog' still works as expected."""
        with tempfile.TemporaryDirectory() as tmp:
            mlog_file = os.path.join(tmp, "input.mlog")
            with open(mlog_file, "w", encoding="utf-8") as f:
                f.write("set alpha 99\n")
            code, stdout, stderr = self._run_cli_capture(["decompile", mlog_file], is_tty=False)
            self.assertEqual(code, 0)
            self.assertIn("alpha = 99", stdout)

    def test_nonexistent_file_argument_reports_error(self):
        """Providing a nonexistent file path exits with code 1 and error message on stderr."""
        code, stdout, stderr = self._run_cli_capture(["decompile", "non_existent_file_12345.mlog"], is_tty=False)
        self.assertEqual(code, 1)
        self.assertIn("Error reading file", stderr)

    def test_keyboard_interrupt_returns_130_with_clean_message(self):
        """KeyboardInterrupt (Ctrl+C) exits cleanly with code 130 and abort message."""
        class InterruptStdin(io.StringIO):
            def isatty(self):
                return True
            def readline(self, *args, **kwargs):
                raise KeyboardInterrupt()

        old_stdin = sys.stdin
        stderr_buf = io.StringIO()
        try:
            sys.stdin = InterruptStdin()
            with redirect_stderr(stderr_buf):
                code = main(["decompile"])
        finally:
            sys.stdin = old_stdin

        self.assertEqual(code, 130)
        self.assertIn("Decompilation aborted by user", stderr_buf.getvalue())


    def test_tty_prompt_shows_correct_platform_eof_key(self):
        """Prompt instructs Ctrl+D on Linux/Android/Termux and omits Ctrl+Z unless on Windows."""
        mlog = "set count 1\n"
        code, stdout, stderr = self._run_cli_capture(["decompile"], stdin_data=mlog, is_tty=True)
        self.assertEqual(code, 0)
        if sys.platform == "win32":
            self.assertIn("Ctrl+Z", stderr)
        else:
            self.assertIn("Ctrl+D", stderr)
            self.assertNotIn("Ctrl+Z", stderr)

    def test_interactive_save_to_file(self):
        """Providing a valid file path at the interactive save prompt writes the file and notifies user."""
        from src import mlog as mlog_module
        mlog = "set score 10\n"
        with tempfile.TemporaryDirectory() as tmp:
            target_py = os.path.join(tmp, "out_saved.py")
            mlog_module._interactive_prompt_hook = lambda prompt: target_py
            try:
                code, stdout, stderr = self._run_cli_capture(["decompile"], stdin_data=mlog, is_tty=True)
            finally:
                mlog_module._interactive_prompt_hook = None

            self.assertEqual(code, 0)
            self.assertEqual(stdout, "")
            self.assertIn(f"Saved decompiled code to '{target_py}'", stderr)
            self.assertTrue(os.path.exists(target_py))
            with open(target_py, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("score = 10", content)

    def test_interactive_save_empty_path_prints_to_stdout(self):
        """Pressing Enter (empty path) at the save prompt prints decompiled code to stdout."""
        from src import mlog as mlog_module
        mlog = "set score 20\n"
        mlog_module._interactive_prompt_hook = lambda prompt: ""
        try:
            code, stdout, stderr = self._run_cli_capture(["decompile"], stdin_data=mlog, is_tty=True)
        finally:
            mlog_module._interactive_prompt_hook = None

        self.assertEqual(code, 0)
        self.assertIn("score = 20", stdout)
        self.assertIn("Enter output file path (.py) [press Enter to print to stdout]:", stderr)

    def test_interactive_save_prompt_skipped_when_output_flag_provided(self):
        """When -o is already passed, the interactive prompt is not displayed and file is saved."""
        from src import mlog as mlog_module
        mlog = "set score 30\n"
        hook_called = []
        mlog_module._interactive_prompt_hook = lambda prompt: hook_called.append(True) or ""
        with tempfile.TemporaryDirectory() as tmp:
            target_py = os.path.join(tmp, "flag_saved.py")
            try:
                code, stdout, stderr = self._run_cli_capture(["decompile", "-o", target_py], stdin_data=mlog, is_tty=True)
            finally:
                mlog_module._interactive_prompt_hook = None

            self.assertEqual(code, 0)
            self.assertEqual(hook_called, [])
            self.assertNotIn("Enter output file path", stderr)
            self.assertTrue(os.path.exists(target_py))

    def test_interactive_save_keyboard_interrupt_returns_130(self):
        """Pressing Ctrl+C at the save prompt aborts decompilation cleanly with exit code 130."""
        from src import mlog as mlog_module
        mlog = "set score 40\n"
        def interrupt_hook(prompt):
            raise KeyboardInterrupt()
        mlog_module._interactive_prompt_hook = interrupt_hook
        try:
            code, stdout, stderr = self._run_cli_capture(["decompile"], stdin_data=mlog, is_tty=True)
        finally:
            mlog_module._interactive_prompt_hook = None

        self.assertEqual(code, 130)
        self.assertIn("Decompilation aborted by user", stderr)

    def test_interactive_save_os_error_reports_error_and_returns_1(self):
        """Invalid path or permission error at save prompt reports error and returns code 1."""
        from src import mlog as mlog_module
        mlog = "set score 50\n"
        mlog_module._interactive_prompt_hook = lambda prompt: "/root/forbidden/cannot_write_here.py"
        try:
            code, stdout, stderr = self._run_cli_capture(["decompile"], stdin_data=mlog, is_tty=True)
        finally:
            mlog_module._interactive_prompt_hook = None

        self.assertEqual(code, 1)
        self.assertIn("Error writing output file", stderr)


if __name__ == "__main__":
    unittest.main()

