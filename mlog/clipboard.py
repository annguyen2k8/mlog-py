"""System clipboard integration for mlog-py CLI.

Supports automatic clipboard detection across:
- Termux / Android: termux-clipboard-set
- Linux (Wayland): wl-copy
- Linux (X11): xclip, xsel
- macOS: pbcopy
- Windows: clip.exe / clip
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable, List, Mapping, Optional, Tuple


@dataclass(frozen=True)
class ClipboardBackend:
    """Representation of an external clipboard tool."""

    name: str
    command: List[str]
    description: str


def is_termux(
    environ: Optional[Mapping[str, str]] = None,
    platform: Optional[str] = None,
    executable: Optional[str] = None,
) -> bool:
    """Return True if running in a Termux environment on Android."""
    plat = sys.platform if platform is None else platform
    if plat not in ("linux", "android"):
        return False

    env = os.environ if environ is None else environ
    exe = sys.executable if executable is None else executable

    return (
        "TERMUX_VERSION" in env
        or "/com.termux/" in env.get("PREFIX", "")
        or "/data/data/com.termux" in exe
    )


def detect_clipboard_backend(
    which_fn: Optional[Callable[[str], Optional[str]]] = None,
    environ: Optional[Mapping[str, str]] = None,
    platform: Optional[str] = None,
    executable: Optional[str] = None,
) -> Optional[ClipboardBackend]:
    """Detect the most appropriate clipboard backend for the current platform.

    Checks available command-line tools in prioritized order:
    1. Termux on Android -> termux-clipboard-set
    2. Wayland session -> wl-copy
    3. macOS -> pbcopy
    4. Windows -> clip.exe / clip
    5. Linux / Unix generic -> wl-copy, xclip, xsel, termux-clipboard-set
    """
    which = shutil.which if which_fn is None else which_fn
    env = os.environ if environ is None else environ
    plat = sys.platform if platform is None else platform
    exe = sys.executable if executable is None else executable

    # 1. Termux / Android check:
    # On Android Termux, termux-clipboard-set communicates with the Android system clipboard.
    if is_termux(environ=env, platform=plat, executable=exe) and which("termux-clipboard-set"):
        return ClipboardBackend(
            name="termux-clipboard-set",
            command=["termux-clipboard-set"],
            description="Termux clipboard utility (Android)",
        )

    # 2. Wayland check:
    # If WAYLAND_DISPLAY is set or session is wayland, wl-copy is the native choice.
    if (
        env.get("WAYLAND_DISPLAY")
        or env.get("XDG_SESSION_TYPE") == "wayland"
    ) and which("wl-copy"):
        return ClipboardBackend(
            name="wl-copy",
            command=["wl-copy"],
            description="Wayland clipboard utility (wl-clipboard)",
        )

    # 3. macOS check:
    if plat == "darwin" and which("pbcopy"):
        return ClipboardBackend(
            name="pbcopy",
            command=["pbcopy"],
            description="macOS pbcopy utility",
        )

    # 4. Windows check:
    if plat == "win32":
        if which("clip.exe"):
            return ClipboardBackend(
                name="clip.exe",
                command=["clip.exe"],
                description="Windows clip utility",
            )
        if which("clip"):
            return ClipboardBackend(
                name="clip",
                command=["clip"],
                description="Windows clip utility",
            )

    # 5. Linux / Unix generic discovery in priority order:
    # Check wl-copy first
    if which("wl-copy"):
        return ClipboardBackend(
            name="wl-copy",
            command=["wl-copy"],
            description="Wayland clipboard utility (wl-clipboard)",
        )

    # Check xclip
    if which("xclip"):
        return ClipboardBackend(
            name="xclip",
            command=["xclip", "-selection", "clipboard"],
            description="X11 xclip utility",
        )

    # Check xsel
    if which("xsel"):
        return ClipboardBackend(
            name="xsel",
            command=["xsel", "--clipboard", "--input"],
            description="X11 xsel utility",
        )

    # Check termux-clipboard-set if present on Linux/Android even outside standard Termux path
    if which("termux-clipboard-set"):
        return ClipboardBackend(
            name="termux-clipboard-set",
            command=["termux-clipboard-set"],
            description="Termux clipboard utility (Android)",
        )

    return None


def get_clipboard_install_instructions(
    environ: Optional[Mapping[str, str]] = None,
    platform: Optional[str] = None,
    executable: Optional[str] = None,
) -> str:
    """Return platform-specific installation instructions for missing clipboard tools."""
    env = os.environ if environ is None else environ
    plat = sys.platform if platform is None else platform
    exe = sys.executable if executable is None else executable

    if is_termux(environ=env, platform=plat, executable=exe):
        return (
            "To enable automatic clipboard copying in Termux:\n"
            "  1. Run: pkg install termux-api\n"
            "  2. Ensure the Termux:API app is installed on your Android device."
        )
    if plat.startswith("linux"):
        return (
            "To enable automatic clipboard copying, install a clipboard utility for your display server:\n"
            "  - Wayland: sudo apt install wl-clipboard (provides wl-copy)\n"
            "  - X11: sudo apt install xclip (or sudo apt install xsel)\n"
            "  - Termux (Android): pkg install termux-api"
        )
    if plat == "darwin":
        return "Ensure 'pbcopy' is installed and available in PATH."
    if plat == "win32":
        return "Ensure 'clip.exe' is installed and available in PATH."
    return "Please install wl-clipboard (wl-copy), xclip, xsel, or termux-api."


def copy_to_clipboard(
    text: str,
    backend: Optional[ClipboardBackend] = None,
    timeout: float = 5.0,
) -> Tuple[bool, str]:
    """Copy text to system clipboard using detected or provided backend.

    Args:
        text: String content to copy to clipboard.
        backend: Explicit ClipboardBackend to use, or None to auto-detect.
        timeout: Subprocess execution timeout in seconds (default 5.0).

    Returns:
        (success, message): Tuple of success flag and descriptive status/error message.
    """
    if backend is None:
        backend = detect_clipboard_backend()

    if backend is None:
        instructions = get_clipboard_install_instructions()
        return False, instructions

    try:
        proc = subprocess.run(
            backend.command,
            input=text.encode("utf-8"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        if proc.returncode == 0:
            return True, f"Copied compiled MLog to clipboard via {backend.name}."
        else:
            err = proc.stderr.decode("utf-8", errors="replace").strip()
            err_msg = f": {err}" if err else ""
            return (
                False,
                f"Clipboard command '{backend.name}' exited with code {proc.returncode}{err_msg}.",
            )
    except subprocess.TimeoutExpired:
        return False, f"Clipboard command '{backend.name}' timed out after {timeout}s."
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"Failed to execute clipboard command '{backend.name}': {e}."
