"""Tests for CLI automatic clipboard copying, backend detection, and stdout pipe safety."""

import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.clipboard import (
    ClipboardBackend,
    copy_to_clipboard,
    detect_clipboard_backend,
    get_clipboard_install_instructions,
    is_termux,
)
from src.mlog import main


class TestClipboardBackendDetection(unittest.TestCase):
    """Test platform and tool detection logic across diverse OS environments."""

    def test_termux_detection(self):
        """Termux environment is detected and selects termux-clipboard-set."""
        # Simulated Termux environment with termux-clipboard-set present
        environ = {"TERMUX_VERSION": "0.118.0", "PREFIX": "/data/data/com.termux/files/usr"}
        which_map = {"termux-clipboard-set": "/data/data/com.termux/files/usr/bin/termux-clipboard-set"}

        self.assertTrue(
            is_termux(
                environ=environ,
                platform="linux",
                executable="/data/data/com.termux/files/usr/bin/python",
            )
        )
        backend = detect_clipboard_backend(
            which_fn=lambda cmd: which_map.get(cmd),
            environ=environ,
            platform="linux",
            executable="/data/data/com.termux/files/usr/bin/python",
        )
        self.assertIsNotNone(backend)
        self.assertEqual(backend.name, "termux-clipboard-set")
        self.assertEqual(backend.command, ["termux-clipboard-set"])

    def test_wayland_detection(self):
        """Wayland environment prefers wl-copy."""
        environ = {"WAYLAND_DISPLAY": "wayland-0"}
        which_map = {
            "wl-copy": "/usr/bin/wl-copy",
            "xclip": "/usr/bin/xclip",
            "xsel": "/usr/bin/xsel",
        }

        backend = detect_clipboard_backend(
            which_fn=lambda cmd: which_map.get(cmd),
            environ=environ,
            platform="linux",
            executable="/usr/bin/python3",
        )
        self.assertIsNotNone(backend)
        self.assertEqual(backend.name, "wl-copy")
        self.assertEqual(backend.command, ["wl-copy"])

    def test_x11_xclip_detection(self):
        """X11 environment with xclip uses xclip with clipboard selection."""
        environ = {"DISPLAY": ":0"}
        which_map = {"xclip": "/usr/bin/xclip", "xsel": "/usr/bin/xsel"}

        backend = detect_clipboard_backend(
            which_fn=lambda cmd: which_map.get(cmd),
            environ=environ,
            platform="linux",
            executable="/usr/bin/python3",
        )
        self.assertIsNotNone(backend)
        self.assertEqual(backend.name, "xclip")
        self.assertEqual(backend.command, ["xclip", "-selection", "clipboard"])

    def test_x11_xsel_detection_when_xclip_absent(self):
        """X11 environment with only xsel available selects xsel."""
        environ = {"DISPLAY": ":0"}
        which_map = {"xsel": "/usr/bin/xsel"}

        backend = detect_clipboard_backend(
            which_fn=lambda cmd: which_map.get(cmd),
            environ=environ,
            platform="linux",
            executable="/usr/bin/python3",
        )
        self.assertIsNotNone(backend)
        self.assertEqual(backend.name, "xsel")
        self.assertEqual(backend.command, ["xsel", "--clipboard", "--input"])

    def test_macos_pbcopy_detection(self):
        """macOS platform uses pbcopy."""
        which_map = {"pbcopy": "/usr/bin/pbcopy"}

        backend = detect_clipboard_backend(
            which_fn=lambda cmd: which_map.get(cmd),
            environ={},
            platform="darwin",
            executable="/usr/local/bin/python3",
        )
        self.assertIsNotNone(backend)
        self.assertEqual(backend.name, "pbcopy")
        self.assertEqual(backend.command, ["pbcopy"])

    def test_windows_clip_detection(self):
        """Windows platform uses clip.exe."""
        which_map = {"clip.exe": "C:\\Windows\\System32\\clip.exe"}

        backend = detect_clipboard_backend(
            which_fn=lambda cmd: which_map.get(cmd),
            environ={},
            platform="win32",
            executable="C:\\Python311\\python.exe",
        )
        self.assertIsNotNone(backend)
        self.assertEqual(backend.name, "clip.exe")
        self.assertEqual(backend.command, ["clip.exe"])

    def test_no_backend_returns_none(self):
        """When no clipboard tool exists in PATH, returns None."""
        backend = detect_clipboard_backend(
            which_fn=lambda cmd: None,
            environ={},
            platform="linux",
            executable="/usr/bin/python3",
        )
        self.assertIsNone(backend)


class TestClipboardInstallInstructions(unittest.TestCase):
    """Test installation guidance messages for missing tools."""

    def test_termux_guidance(self):
        """Termux install instructions specifically mention termux-api."""
        msg = get_clipboard_install_instructions(
            environ={"TERMUX_VERSION": "0.118"},
            platform="linux",
            executable="/data/data/com.termux/files/usr/bin/python",
        )
        self.assertIn("pkg install termux-api", msg)
        self.assertIn("Termux:API", msg)

    def test_linux_guidance(self):
        """Linux install instructions list Wayland and X11 packages."""
        msg = get_clipboard_install_instructions(
            environ={},
            platform="linux",
            executable="/usr/bin/python3",
        )
        self.assertIn("wl-clipboard", msg)
        self.assertIn("xclip", msg)
        self.assertIn("xsel", msg)

    def test_macos_guidance(self):
        """macOS install instructions mention pbcopy."""
        msg = get_clipboard_install_instructions(environ={}, platform="darwin")
        self.assertIn("pbcopy", msg)

    def test_windows_guidance(self):
        """Windows install instructions mention clip.exe."""
        msg = get_clipboard_install_instructions(environ={}, platform="win32")
        self.assertIn("clip.exe", msg)


class TestCopyToClipboardExecution(unittest.TestCase):
    """Test copy_to_clipboard execution semantics with mocked subprocess."""

    @patch("src.clipboard.subprocess.run")
    def test_copy_success(self, mock_run):
        """Successful subprocess copy returns True and success message."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["wl-copy"], returncode=0, stdout=b"", stderr=b""
        )
        backend = ClipboardBackend(name="wl-copy", command=["wl-copy"], description="Wayland")

        ok, msg = copy_to_clipboard("set x 10\n", backend=backend)
        self.assertTrue(ok)
        self.assertIn("Copied compiled MLog to clipboard via wl-copy", msg)
        mock_run.assert_called_once_with(
            ["wl-copy"],
            input=b"set x 10\n",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=5.0,
            check=False,
        )

    @patch("src.clipboard.subprocess.run")
    def test_copy_subprocess_failure(self, mock_run):
        """Failing subprocess returns False and stderr diagnostics."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["xclip"], returncode=1, stdout=b"", stderr=b"Error: Can't open display"
        )
        backend = ClipboardBackend(name="xclip", command=["xclip"], description="X11")

        ok, msg = copy_to_clipboard("set x 10\n", backend=backend)
        self.assertFalse(ok)
        self.assertIn("Can't open display", msg)

    @patch("src.clipboard.subprocess.run")
    def test_copy_subprocess_timeout(self, mock_run):
        """TimeoutExpired returns False with timeout message."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["wl-copy"], timeout=5.0)
        backend = ClipboardBackend(name="wl-copy", command=["wl-copy"], description="Wayland")

        ok, msg = copy_to_clipboard("set x 10\n", backend=backend)
        self.assertFalse(ok)
        self.assertIn("timed out after 5.0s", msg)

    @patch("src.clipboard.detect_clipboard_backend", return_value=None)
    @patch("src.clipboard.sys.platform", "linux")
    def test_copy_without_backend(self, mock_detect):
        """When no backend is installed, returns False with install guide."""
        ok, msg = copy_to_clipboard("set x 10\n")
        self.assertFalse(ok)
        self.assertIn("To enable automatic clipboard copying", msg)


class TestCliClipboardIntegration(unittest.TestCase):
    """Test CLI behavior for auto-copy, compile error, missing backend, and stdout redirect."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.src_file = Path(self.temp_dir.name) / "test_input.py"
        self.out_file = Path(self.temp_dir.name) / "output.mlog"
        self.src_file.write_text("x = 10\ny = 20\nz = x + y\n", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("src.clipboard.copy_to_clipboard")
    def test_cli_compile_auto_copy_success(self, mock_copy):
        """CLI auto-copies on successful compile and reports via stderr without flag."""
        mock_copy.return_value = (True, "Copied compiled MLog to clipboard via termux-clipboard-set.")

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
            code = main(["compile", str(self.src_file)])

        self.assertEqual(code, 0)
        # Verify clipboard was called with the exact compiled MLog output
        mock_copy.assert_called_once()
        copied_text = mock_copy.call_args[0][0]
        self.assertIn("set x 10", copied_text)
        self.assertIn("set y 20", copied_text)

        # Stdout receives the compiled mlog
        self.assertIn("set x 10", stdout_buf.getvalue())
        # Stderr receives the notification
        self.assertIn("[mlog-py] Copied compiled MLog to clipboard via termux-clipboard-set.", stderr_buf.getvalue())

    @patch("src.clipboard.copy_to_clipboard")
    def test_cli_compile_stdout_redirect(self, mock_copy):
        """When stdout is redirected/piped, stdout is 100% clean mlog and clipboard still receives code."""
        mock_copy.return_value = (True, "Copied compiled MLog to clipboard via wl-copy.")

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
            # Also simulate non-TTY stream
            stdout_buf.isatty = lambda: False
            code = main(["compile", str(self.src_file)])

        self.assertEqual(code, 0)
        stdout_output = stdout_buf.getvalue()
        # Stdout must contain ONLY pure mlog instructions
        self.assertIn("set x 10", stdout_output)
        self.assertNotIn("[mlog-py]", stdout_output)
        self.assertNotIn("clipboard", stdout_output)

        # Stderr receives the clipboard status
        self.assertIn("[mlog-py] Copied compiled MLog to clipboard via wl-copy.", stderr_buf.getvalue())
        # Clipboard received the code
        mock_copy.assert_called_once()

    @patch("src.clipboard.copy_to_clipboard")
    def test_cli_compile_error_no_clipboard(self, mock_copy):
        """Compilation error exits code 1 and clipboard is NEVER called."""
        bad_file = Path(self.temp_dir.name) / "bad.py"
        bad_file.write_text("from mlog import Vars\nVars.tick = 999\n", encoding="utf-8")

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
            code = main(["compile", str(bad_file)])

        self.assertEqual(code, 1)
        # Clipboard must NEVER be called on compile error
        mock_copy.assert_not_called()
        self.assertIn("cannot assign to read-only built-in variable", stderr_buf.getvalue())

    @patch("src.clipboard.detect_clipboard_backend", return_value=None)
    @patch("src.clipboard.sys.platform", "linux")
    def test_cli_compile_missing_backend_preserves_output_and_succeeds(self, mock_detect):
        """Missing clipboard backend emits guidance to stderr, preserves stdout, and exits 0."""
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
            code = main(["compile", str(self.src_file)])

        # Compilation must not fail
        self.assertEqual(code, 0)
        # Output is NOT lost
        self.assertIn("set x 10", stdout_buf.getvalue())
        # Clear installation guidance printed on stderr
        stderr_val = stderr_buf.getvalue()
        self.assertIn("[mlog-py] Notice: Could not copy to clipboard.", stderr_val)
        self.assertIn("To enable automatic clipboard copying", stderr_val)

    @patch("src.clipboard.copy_to_clipboard")
    def test_cli_compile_no_clipboard_flag(self, mock_copy):
        """Passing --no-clipboard skips clipboard copying entirely."""
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
            code = main(["compile", str(self.src_file), "--no-clipboard"])

        self.assertEqual(code, 0)
        mock_copy.assert_not_called()
        self.assertIn("set x 10", stdout_buf.getvalue())
        self.assertNotIn("[mlog-py]", stderr_buf.getvalue())

    @patch("src.clipboard.copy_to_clipboard")
    def test_cli_compile_env_var_no_clipboard(self, mock_copy):
        """Setting MLOG_NO_CLIPBOARD=1 environment variable skips clipboard copying."""
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with patch.dict(os.environ, {"MLOG_NO_CLIPBOARD": "1"}), patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
            code = main(["compile", str(self.src_file)])

        self.assertEqual(code, 0)
        mock_copy.assert_not_called()

    @patch("src.clipboard.copy_to_clipboard")
    def test_cli_compile_with_output_file_copies_to_clipboard(self, mock_copy):
        """Compiling with -o output file writes the file AND auto-copies to clipboard."""
        mock_copy.return_value = (True, "Copied compiled MLog to clipboard via termux-clipboard-set.")

        stderr_buf = io.StringIO()
        with patch("sys.stderr", stderr_buf):
            code = main(["compile", str(self.src_file), "-o", str(self.out_file)])

        self.assertEqual(code, 0)
        self.assertTrue(self.out_file.exists())
        self.assertIn("set x 10", self.out_file.read_text(encoding="utf-8"))
        mock_copy.assert_called_once()
        self.assertIn("[mlog-py] Copied compiled MLog to clipboard via termux-clipboard-set.", stderr_buf.getvalue())

    @patch("src.clipboard.copy_to_clipboard")
    def test_cli_compile_copy_failure_preserves_output(self, mock_copy):
        """If clipboard execution fails at runtime, compile still succeeds and preserves output."""
        mock_copy.return_value = (False, "Clipboard command 'xclip' exited with code 1.")

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
            code = main(["compile", str(self.src_file)])

        self.assertEqual(code, 0)
        self.assertIn("set x 10", stdout_buf.getvalue())
        self.assertIn("Notice: Could not copy to clipboard", stderr_buf.getvalue())

    # -----------------------------------------------------------------------
    # Regression Tests: CLI Precedence & BrokenPipeError
    # -----------------------------------------------------------------------

    @patch("src.clipboard.copy_to_clipboard")
    def test_cli_compile_precedence_no_clipboard_then_clipboard(self, mock_copy):
        """When --no-clipboard is followed by --clipboard, the later --clipboard flag wins."""
        mock_copy.return_value = (True, "Copied compiled MLog to clipboard via wl-copy.")

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
            code = main(["compile", str(self.src_file), "--no-clipboard", "--clipboard"])

        self.assertEqual(code, 0)
        mock_copy.assert_called_once()
        self.assertIn("[mlog-py] Copied compiled MLog to clipboard via wl-copy.", stderr_buf.getvalue())

    @patch("src.clipboard.copy_to_clipboard")
    def test_cli_compile_precedence_clipboard_then_no_clipboard(self, mock_copy):
        """When --clipboard is followed by --no-clipboard, the later --no-clipboard flag wins."""
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
            code = main(["compile", str(self.src_file), "--clipboard", "--no-clipboard"])

        self.assertEqual(code, 0)
        mock_copy.assert_not_called()
        self.assertNotIn("[mlog-py]", stderr_buf.getvalue())

    @patch("src.clipboard.copy_to_clipboard")
    def test_cli_compile_clipboard_flag_overrides_env_var(self, mock_copy):
        """Passing --clipboard explicitly overrides MLOG_NO_CLIPBOARD=1 environment variable."""
        mock_copy.return_value = (True, "Copied compiled MLog to clipboard via wl-copy.")

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with patch.dict(os.environ, {"MLOG_NO_CLIPBOARD": "1"}), patch("sys.stdout", stdout_buf), patch("sys.stderr", stderr_buf):
            code = main(["compile", str(self.src_file), "--clipboard"])

        self.assertEqual(code, 0)
        mock_copy.assert_called_once()
        self.assertIn("[mlog-py] Copied compiled MLog to clipboard via wl-copy.", stderr_buf.getvalue())

    @patch("src.clipboard.copy_to_clipboard")
    def test_cli_compile_stdout_broken_pipe_still_copies(self, mock_copy):
        """When stdout raises BrokenPipeError (pipeline consumer closed early), clipboard copy still executes."""
        mock_copy.return_value = (True, "Copied compiled MLog to clipboard via wl-copy.")

        stderr_buf = io.StringIO()
        mock_stdout = MagicMock()
        mock_stdout.write.side_effect = BrokenPipeError("Broken pipe")

        with patch("sys.stdout", mock_stdout), patch("sys.stderr", stderr_buf):
            code = main(["compile", str(self.src_file)])

        self.assertEqual(code, 0)
        mock_copy.assert_called_once()
        self.assertIn("[mlog-py] Copied compiled MLog to clipboard via wl-copy.", stderr_buf.getvalue())

    @patch("src.clipboard.copy_to_clipboard")
    def test_cli_compile_stderr_broken_pipe_handled_cleanly(self, mock_copy):
        """When stderr raises BrokenPipeError while logging copy notice, exits cleanly with code 0."""
        mock_copy.return_value = (True, "Copied compiled MLog to clipboard via wl-copy.")

        stdout_buf = io.StringIO()
        mock_stderr = MagicMock()
        mock_stderr.write.side_effect = BrokenPipeError("Broken pipe")

        with patch("sys.stdout", stdout_buf), patch("sys.stderr", mock_stderr):
            code = main(["compile", str(self.src_file)])

        self.assertEqual(code, 0)
        mock_copy.assert_called_once()


if __name__ == "__main__":
    unittest.main()
