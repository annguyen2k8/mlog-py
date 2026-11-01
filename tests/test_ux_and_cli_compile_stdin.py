"""Unit and regression tests for CLI compile stdin streaming and UX diagnostic improvements."""

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

import mlog
from mlog import compile_py, main
from mlog.errors import CompileError, SourceLocation


class TestCliCompileStdin(unittest.TestCase):
    """Tests for CLI compile subcommand reading from stdin, pipes, and interactive TTY."""

    def setUp(self):
        # Disable automatic clipboard operations in CLI during test suite
        self._old_no_clip = os.environ.get("MLOG_NO_CLIPBOARD")
        os.environ["MLOG_NO_CLIPBOARD"] = "1"
        mlog._interactive_prompt_hook = None

    def tearDown(self):
        if self._old_no_clip is None:
            os.environ.pop("MLOG_NO_CLIPBOARD", None)
        else:
            os.environ["MLOG_NO_CLIPBOARD"] = self._old_no_clip
        mlog._interactive_prompt_hook = None

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

    def test_piped_stdin_compile(self):
        """Piping Python code into 'mlog compile' produces compiled MLog on stdout."""
        code = "a = 10\nb = 20\nc = a + b\n"
        exit_code, stdout, stderr = self._run_cli_capture(["compile"], stdin_data=code, is_tty=False)
        self.assertEqual(exit_code, 0)
        self.assertIn("set a 10", stdout)
        self.assertIn("set b 20", stdout)
        self.assertIn("op add c a b", stdout)
        self.assertEqual(stderr, "")

    def test_piped_stdin_compile_with_dash(self):
        """Piping Python code into 'mlog compile -' works identically."""
        code = "msg = 'hello'\n"
        exit_code, stdout, stderr = self._run_cli_capture(["compile", "-"], stdin_data=code, is_tty=False)
        self.assertEqual(exit_code, 0)
        self.assertIn('set msg "hello"', stdout)
        self.assertEqual(stderr, "")

    def test_piped_stdin_implicit_compile(self):
        """Running 'mlog' with no arguments on a non-TTY pipe defaults to compile."""
        code = "my_var = 42\n"
        exit_code, stdout, stderr = self._run_cli_capture([], stdin_data=code, is_tty=False)
        self.assertEqual(exit_code, 0)
        self.assertIn("set my_var 42", stdout)
        self.assertEqual(stderr, "")

    def test_piped_stdin_empty_reports_error(self):
        """Empty stdin exits with code 1 and an explicit error on stderr."""
        exit_code, stdout, stderr = self._run_cli_capture(["compile"], stdin_data="", is_tty=False)
        self.assertEqual(exit_code, 1)
        self.assertIn("Compilation error: input is empty", stderr)
        self.assertEqual(stdout, "")

    def test_piped_stdin_whitespace_reports_error(self):
        """Whitespace-only stdin exits with code 1 and error on stderr."""
        exit_code, stdout, stderr = self._run_cli_capture(["compile"], stdin_data="   \n\n  \t  \n", is_tty=False)
        self.assertEqual(exit_code, 1)
        self.assertIn("Compilation error: input is empty", stderr)

    def test_piped_stdin_syntax_error_reports_location_and_exits_1(self):
        """Python syntax error from stdin reports <stdin> location and exits with code 1."""
        code = "def broken(\n"
        exit_code, stdout, stderr = self._run_cli_capture(["compile"], stdin_data=code, is_tty=False)
        self.assertEqual(exit_code, 1)
        self.assertIn("<stdin>:", stderr)
        self.assertIn("syntax error:", stderr)

    def test_interactive_mode_prompts_to_stderr_and_reads_until_stream_eof(self):
        """When stdin is a TTY, interactive prompts are written to stderr, not stdout."""
        code = "x = 99\n"
        with patch("mlog._read_interactive_line", return_value=""):
            exit_code, stdout, stderr = self._run_cli_capture(["compile"], stdin_data=code, is_tty=True)
        self.assertEqual(exit_code, 0)
        self.assertIn("[mlog-py] Enter Python DSL code below.", stderr)
        self.assertIn("set x 99", stdout)
        self.assertNotIn("[mlog-py]", stdout)

    def test_interactive_mode_stops_at_eof_sentinel(self):
        """Typing 'EOF' on an empty line cleanly stops input reading."""
        code = "x = 100\nEOF\nx = 999\n"
        with patch("mlog._read_interactive_line", return_value=""):
            exit_code, stdout, stderr = self._run_cli_capture(["compile"], stdin_data=code, is_tty=True)
        self.assertEqual(exit_code, 0)
        self.assertIn("set x 100", stdout)
        self.assertNotIn("999", stdout)

    def test_interactive_mode_stops_at_double_underscore_eof_sentinel(self):
        """Typing '__EOF__' on an empty line cleanly stops input reading."""
        code = "val = 7\n__EOF__\nignored code\n"
        with patch("mlog._read_interactive_line", return_value=""):
            exit_code, stdout, stderr = self._run_cli_capture(["compile"], stdin_data=code, is_tty=True)
        self.assertEqual(exit_code, 0)
        self.assertIn("set val 7", stdout)
        self.assertNotIn("ignored", stdout)

    def test_compile_stdin_output_file(self):
        """'-o <file>' flag writes compiled mlog to disk."""
        code = "out_val = 123\n"
        with tempfile.TemporaryDirectory() as tmp:
            out_file = os.path.join(tmp, "subdir", "compiled.mlog")
            exit_code, stdout, stderr = self._run_cli_capture(
                ["compile", "-", "-o", out_file],
                stdin_data=code,
                is_tty=False,
            )
            self.assertEqual(exit_code, 0)
            self.assertTrue(os.path.isfile(out_file))
            with open(out_file, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("set out_val 123", content)

    def test_compile_interactive_save_prompt_via_hook(self):
        """Interactive mode prompts for output destination and saves via _interactive_prompt_hook."""
        code = "y = 5\n"
        with tempfile.TemporaryDirectory() as tmp:
            out_file = os.path.join(tmp, "out.mlog")
            mlog._interactive_prompt_hook = lambda prompt: out_file
            exit_code, stdout, stderr = self._run_cli_capture(["compile"], stdin_data=code, is_tty=True)
            self.assertEqual(exit_code, 0)
            self.assertTrue(os.path.isfile(out_file))
            self.assertIn(f"[mlog-py] Saved compiled bytecode to '{out_file}'.", stderr)

    def test_compile_interactive_save_prompt_keyboard_interrupt_returns_130(self):
        """KeyboardInterrupt during interactive save prompt returns exit code 130."""
        code = "y = 5\n"
        def interrupt(prompt):
            raise KeyboardInterrupt()

        mlog._interactive_prompt_hook = interrupt
        exit_code, stdout, stderr = self._run_cli_capture(["compile"], stdin_data=code, is_tty=True)
        self.assertEqual(exit_code, 130)
        self.assertIn("Compilation aborted by user.", stderr)

    def test_compile_keyboard_interrupt_during_compilation_returns_130(self):
        """KeyboardInterrupt during compile_py execution returns exit code 130."""
        code = "x = 10\n"
        with patch("mlog.compile_py", side_effect=KeyboardInterrupt):
            exit_code, stdout, stderr = self._run_cli_capture(["compile"], stdin_data=code, is_tty=False)
        self.assertEqual(exit_code, 130)
        self.assertIn("Compilation aborted by user.", stderr)


class TestCompilerDiagnosticsAndTypoSuggestions(unittest.TestCase):
    """Tests for compiler error diagnostics, typo suggestions, and actionable hints."""

    def test_typo_draw_method_suggestion(self):
        source = "from mlog import draw\ndraw.clearr(0, 0, 0)\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        err = str(ctx.exception)
        self.assertIn("unknown draw method: 'draw.clearr'", err)
        self.assertIn("Did you mean 'draw.clear'?", err)

    def test_typo_control_method_suggestion(self):
        source = "from mlog import control\ncontrol.shoott(turret, 10, 20, 1)\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        err = str(ctx.exception)
        self.assertIn("unknown control method: 'control.shoott'", err)
        self.assertIn("Did you mean 'control.shoot'?", err)

    def test_typo_ucontrol_method_suggestion(self):
        source = "from mlog import ucontrol\nucontrol.minne(10, 20)\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        err = str(ctx.exception)
        self.assertIn("unknown ucontrol method: 'ucontrol.minne'", err)
        self.assertIn("Did you mean 'ucontrol.mine'?", err)

    def test_typo_ulocate_method_suggestion(self):
        source = "from mlog import ulocate\nulocate.spawwn()\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        err = str(ctx.exception)
        self.assertIn("unknown ulocate method: 'ulocate.spawwn'", err)
        self.assertIn("Did you mean 'ulocate.spawn'?", err)

    def test_typo_op_method_suggestion(self):
        source = "from mlog import op\nx = op.flooor(3.14)\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        err = str(ctx.exception)
        self.assertIn("unknown op method: 'op.flooor'", err)
        self.assertIn("Did you mean 'op.floor'?", err)

    def test_typo_cutscene_method_suggestion(self):
        source = "from mlog import cutscene\ncutscene.paan(10, 20, 5)\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        err = str(ctx.exception)
        self.assertIn("unknown cutscene method: 'cutscene.paan'", err)
        self.assertIn("Did you mean 'cutscene.pan'?", err)

    def test_typo_sound_method_suggestion(self):
        source = "from mlog import sound\nsound.pllay('pew')\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        err = str(ctx.exception)
        self.assertIn("unknown sound method: 'sound.pllay'", err)
        self.assertIn("Did you mean 'sound.play'?", err)

    def test_typo_music_method_suggestion(self):
        source = "from mlog import music\nmusic.stopp()\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        err = str(ctx.exception)
        self.assertIn("unknown music method: 'music.stopp'", err)
        self.assertIn("Did you mean 'music.stop'?", err)

    def test_typo_marker_method_suggestion(self):
        source = "from mlog import marker\nmarker.radiuss(m, 5)\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        err = str(ctx.exception)
        self.assertIn("unknown marker method: 'marker.radiuss'", err)
        self.assertIn("Did you mean 'marker.radius'?", err)

    def test_typo_vars_variable_suggestion(self):
        source = "from mlog import Vars\nx = Vars.thiss\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        err = str(ctx.exception)
        self.assertIn("unknown Mindustry built-in variable: 'Vars.thiss'", err)
        self.assertIn("Did you mean 'Vars.this'?", err)

    def test_typo_unsupported_intrinsic_suggestion(self):
        source = "printt('hello')\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        err = str(ctx.exception)
        self.assertIn("unsupported function call: 'printt'", err)
        self.assertIn("Did you mean 'print'?", err)

    def test_typo_user_defined_function_suggestion(self):
        source = "def perform_task(x):\n    return x + 1\nperform_taskk(5)\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py", allow_functions=True)
        err = str(ctx.exception)
        self.assertIn("unsupported function call: 'perform_taskk'", err)
        self.assertIn("Did you mean 'perform_task'?", err)

    def test_typo_user_defined_int_enum_suggestion(self):
        source = "from enum import IntEnum\nclass State(IntEnum):\n    IDLE = 0\n    ACTIVE = 1\nx = State.ACTIVEE\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        err = str(ctx.exception)
        self.assertIn("enum 'State' has no member 'ACTIVEE'", err)
        self.assertIn("Did you mean 'ACTIVE'?", err)

    def test_typo_supported_namespace_call_suggestion(self):
        source = "drow.clear(0, 0, 0)\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        err = str(ctx.exception)
        self.assertIn("unknown namespace or function call: 'drow.clear()'", err)
        self.assertIn("Did you mean 'draw.clear()'", err)

    def test_typo_supported_namespace_attribute_suggestion(self):
        source = "x = Var.this\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        err = str(ctx.exception)
        self.assertIn("attribute access is only supported", err)
        self.assertIn("Did you mean 'Vars'?", err)

    def test_typo_registry_enum_attribute_in_compiler(self):
        source = "from mlog import Items\nx = Items.coall\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        err = str(ctx.exception)
        self.assertIn("unknown Items attribute 'coall'", err)
        self.assertIn("Did you mean 'Items.COAL'?", err)

    def test_typo_mlog_import_suggestion(self):
        source = "from mlog import draww\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        err = str(ctx.exception)
        self.assertIn("cannot import name 'draww' from 'mlog'", err)
        self.assertIn("Did you mean 'draw'?", err)

    def test_compile_error_backward_compatibility(self):
        source = "x = [1, 2, 3]\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="custom_file.py")
        err = ctx.exception
        self.assertIsInstance(err, CompileError)
        self.assertEqual(err.loc.filename, "custom_file.py")
        self.assertEqual(err.loc.line, 1)
        self.assertTrue(err.loc.col >= 1)
        self.assertTrue(str(err).startswith("custom_file.py:1:"))

    def test_actionable_hint_list_literal(self):
        source = "items = [1, 2, 3]\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        err = str(ctx.exception)
        self.assertIn("unsupported Python feature: list literal", err)
        self.assertIn("Array('cell1', size, dtype=...)", err)

    def test_actionable_hint_dict_literal(self):
        source = "mapping = {'key': 42}\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        err = str(ctx.exception)
        self.assertIn("unsupported Python feature: dict literal", err)
        self.assertIn("Mindustry processors have no heap memory or dynamic object collections", err)

    def test_actionable_hint_set_literal(self):
        source = "unique = {1, 2, 3}\n"
        with self.assertRaises(CompileError) as ctx:
            compile_py(source, filename="test.py")
        err = str(ctx.exception)
        self.assertIn("unsupported Python feature: set literal", err)
        self.assertIn("Mindustry processors have no heap memory or dynamic collections", err)


if __name__ == "__main__":
    unittest.main()
