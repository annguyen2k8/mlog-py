"""Mindustry Real Assembly & Parser Validator Bridge.

Uses the compiled Mindustry engine classes and MindustryHarness via Java
to validate generated mlog directly against Mindustry's actual LParser & LAssembler.
"""

import atexit
import base64
import os
import queue
import shutil
import subprocess
import threading
import time
from typing import Optional, Tuple

try:
    from .mindustry_discovery import MindustryDiscovery, discover as _discover_mindustry
except ImportError:  # pragma: no cover - allows running this file directly
    from mindustry_discovery import MindustryDiscovery, discover as _discover_mindustry


class RunResult(tuple):
    """Execution result from real Mindustry LExecutor.

    Inherits from tuple (success, vars_dict, message) for 100% backwards compatibility
    with existing unpacking: ok, vars_dict, msg = run_with_mindustry(...)

    Attributes:
        success: bool - True if LExecutor executed cleanly without errors
        vars: dict[str, Union[float, str]] - Registers and user variables from LExecutor
        message: str - Execution status string (e.g. "RUN_OK:10")
        text_buffer: str - Content of processor's LExecutor.textBuffer
        messages: dict[str, str] - Content flushed to linked message blocks (e.g. message1)
        ticks: int - Total simulated scheduler ticks
        ipt: int - Current execution rate (instructions per tick)
    """

    def __new__(
        cls,
        success: bool,
        vars_dict: dict,
        message: str,
        text_buffer: str = "",
        messages: Optional[dict] = None,
        ticks: int = 0,
        ipt: int = 0,
        displays: Optional[dict] = None,
        graphics_buffer_size: int = 0,
        bound_unit: Optional[str] = None,
        text_buffer_len: Optional[int] = None,
        announce_text: Optional[str] = None,
        toast_text: Optional[str] = None,
        notify_text: Optional[str] = None,
        mission_text: Optional[str] = None,
        cutscene_active: Optional[bool] = None,
        cutscene_hide_hud: Optional[bool] = None,
        cutscene_zoom: Optional[float] = None,
        cutscene_speed: Optional[float] = None,
        cutscene_pan: Optional[Tuple[float, float]] = None,
        shake_intensity: Optional[float] = None,
        markers_total: Optional[int] = None,
        markers: Optional[dict] = None,
    ):
        return super().__new__(cls, (success, vars_dict, message))

    def __init__(
        self,
        success: bool,
        vars_dict: dict,
        message: str,
        text_buffer: str = "",
        messages: Optional[dict] = None,
        ticks: int = 0,
        ipt: int = 0,
        displays: Optional[dict] = None,
        graphics_buffer_size: int = 0,
        bound_unit: Optional[str] = None,
        text_buffer_len: Optional[int] = None,
        announce_text: Optional[str] = None,
        toast_text: Optional[str] = None,
        notify_text: Optional[str] = None,
        mission_text: Optional[str] = None,
        cutscene_active: Optional[bool] = None,
        cutscene_hide_hud: Optional[bool] = None,
        cutscene_zoom: Optional[float] = None,
        cutscene_speed: Optional[float] = None,
        cutscene_pan: Optional[Tuple[float, float]] = None,
        shake_intensity: Optional[float] = None,
        markers_total: Optional[int] = None,
        markers: Optional[dict] = None,
    ):
        self.success = success
        self.vars = vars_dict
        self.message = message
        self.text_buffer = text_buffer
        self.text_buffer_len = text_buffer_len if text_buffer_len is not None else len(text_buffer)
        self.messages = messages if messages is not None else {}
        self.ticks = ticks
        self.ipt = ipt
        self.displays = displays if displays is not None else {}
        self.graphics_buffer_size = graphics_buffer_size
        self.bound_unit = bound_unit
        self.announce_text = announce_text
        self.toast_text = toast_text
        self.notify_text = notify_text
        self.mission_text = mission_text
        self.cutscene_active = cutscene_active
        self.cutscene_hide_hud = cutscene_hide_hud
        self.cutscene_zoom = cutscene_zoom
        self.cutscene_speed = cutscene_speed
        self.cutscene_pan = cutscene_pan
        self.shake_intensity = shake_intensity
        self.markers_total = markers_total
        self.markers = markers if markers is not None else {}


_DISCOVERY = None
_CHECKED_DISCOVERY = False


def _get_discovery() -> MindustryDiscovery:
    """Return the cached, fully validated harness discovery result."""
    global _DISCOVERY, _CHECKED_DISCOVERY
    if not _CHECKED_DISCOVERY:
        _DISCOVERY = _discover_mindustry()
        _CHECKED_DISCOVERY = True
    return _DISCOVERY


def _reset_mindustry_discovery() -> None:
    """Clear cached discovery results (used by tests and after rebuilding)."""
    global _DISCOVERY, _CHECKED_DISCOVERY
    _DISCOVERY = None
    _CHECKED_DISCOVERY = False


def _find_classpath() -> Optional[str]:
    """Discover the classpath without using the cache."""
    return _discover_mindustry().classpath


def get_classpath() -> Optional[str]:
    """Get the cached classpath if available."""
    return _get_discovery().classpath


def get_mindustry_assets() -> Optional[str]:
    """Return the validated Mindustry assets directory, if available."""
    return _get_discovery().assets_path


def get_mindustry_unavailable_reason() -> Optional[str]:
    """Explain why the Mindustry JVM harness cannot be used, if it cannot."""
    if not shutil.which("java"):
        return "Java runtime not found in PATH (install a JRE or add java to PATH)"
    discovery = _get_discovery()
    if discovery.available:
        return None
    return discovery.error or "Mindustry runtime classpath not available"


def is_mindustry_available() -> bool:
    """Check if Java and the Mindustry harness are available for validation."""
    return get_mindustry_unavailable_reason() is None


def _java_command(java_bin: str, classpath: str, *args: str) -> list[str]:
    """Build a Java command with the discovered assets directory attached."""
    command = [java_bin]
    assets = get_mindustry_assets()
    if assets:
        command.append(f"-Dmindustry.assets={assets}")
    command.extend(["-cp", classpath, "mindustry.test.MindustryHarness"])
    command.extend(args)
    return command


def _parse_validate_output(lines: list[str]) -> Tuple[bool, str, int]:
    for line in lines:
        if line.startswith("OK:"):
            try:
                count = int(line[3:].strip())
            except ValueError:
                count = 0
            return True, "OK", count
        elif line.startswith("ERR:"):
            return False, line[4:].strip(), -1
        elif line.startswith("ERROR:"):
            return False, line[6:].strip(), -1
    err = "\n".join(lines).strip()
    return False, err or "Validation failed", -1


def _parse_run_output(lines: list[str]) -> RunResult:
    vars_dict = {}
    steps_msg = "OK"
    text_buffer = ""
    messages = {}
    ticks = 0
    ipt = 0
    displays = {}
    graphics_buffer_size = 0
    bound_unit = None
    announce_text = None
    toast_text = None
    notify_text = None
    mission_text = None
    cutscene_active = None
    cutscene_hide_hud = None
    cutscene_zoom = None
    cutscene_speed = None
    cutscene_pan_x = 0.0
    cutscene_pan_y = 0.0
    has_pan = False
    shake_intensity = None
    markers_total = None
    markers = {}
    has_run_ok = False
    for line in lines:
        if line.startswith("ERR:"):
            return RunResult(False, {}, line[4:].strip(), text_buffer="", messages={})
        elif line.startswith("ERROR:"):
            return RunResult(False, {}, line[6:].strip(), text_buffer="", messages={})
        elif line.startswith("RUN_OK:"):
            steps_msg = line.strip()
            has_run_ok = True
        elif line.startswith("TICKS:"):
            try:
                ticks = int(line[6:].strip())
            except ValueError:
                ticks = 0
        elif line.startswith("IPT:"):
            try:
                ipt = int(line[4:].strip())
            except ValueError:
                ipt = 0
        elif line.startswith("GRAPHICS_BUFFER_SIZE:"):
            try:
                graphics_buffer_size = int(line[21:].strip())
            except ValueError:
                graphics_buffer_size = 0
        elif line.startswith("DISPLAY_COMMANDS:"):
            payload = line[17:].strip()
            if "=" in payload:
                dname, count_str = payload.split("=", 1)
                try:
                    displays.setdefault(dname.strip(), {})["commands"] = int(count_str.strip())
                except ValueError:
                    pass
        elif line.startswith("DISPLAY_OPS:"):
            payload = line[12:].strip()
            if "=" in payload:
                dname, count_str = payload.split("=", 1)
                try:
                    displays.setdefault(dname.strip(), {})["operations"] = int(count_str.strip())
                except ValueError:
                    pass
        elif line.startswith("BOUND_UNIT:"):
            uval = line[11:].strip()
            bound_unit = uval if uval != "null" else None
        elif line.startswith("TEXT_BUFFER_B64:"):
            b64_str = line[16:].strip()
            try:
                text_buffer = base64.b64decode(b64_str).decode("utf-8")
            except Exception:
                text_buffer = ""
        elif line.startswith("TEXT_BUFFER_LEN:"):
            try:
                text_buffer_len = int(line[16:].strip())
            except ValueError:
                text_buffer_len = None
        elif line.startswith("ANNOUNCE_B64:"):
            try:
                announce_text = base64.b64decode(line[13:].strip()).decode("utf-8")
            except Exception:
                pass
        elif line.startswith("TOAST_B64:"):
            try:
                toast_text = base64.b64decode(line[10:].strip()).decode("utf-8")
            except Exception:
                pass
        elif line.startswith("NOTIFY_B64:"):
            try:
                notify_text = base64.b64decode(line[11:].strip()).decode("utf-8")
            except Exception:
                pass
        elif line.startswith("MISSION_B64:"):
            try:
                mission_text = base64.b64decode(line[12:].strip()).decode("utf-8")
            except Exception:
                pass
        elif line.startswith("CUTSCENE_ACTIVE:"):
            cutscene_active = line[16:].strip().lower() == "true"
        elif line.startswith("CUTSCENE_HIDE_HUD:"):
            cutscene_hide_hud = line[18:].strip().lower() == "true"
        elif line.startswith("CUTSCENE_ZOOM:"):
            try:
                cutscene_zoom = float(line[14:].strip())
            except ValueError:
                pass
        elif line.startswith("CUTSCENE_SPEED:"):
            try:
                cutscene_speed = float(line[15:].strip())
            except ValueError:
                pass
        elif line.startswith("CUTSCENE_PAN_X:"):
            try:
                cutscene_pan_x = float(line[15:].strip())
                has_pan = True
            except ValueError:
                pass
        elif line.startswith("CUTSCENE_PAN_Y:"):
            try:
                cutscene_pan_y = float(line[15:].strip())
                has_pan = True
            except ValueError:
                pass
        elif line.startswith("RENDERER_SHAKE_INTENSITY:"):
            try:
                shake_intensity = float(line[25:].strip())
            except ValueError:
                pass
        elif line.startswith("MARKERS_TOTAL:"):
            try:
                markers_total = int(line[14:].strip())
            except ValueError:
                pass
        elif line.startswith("MARKER_EXISTS:"):
            payload = line[14:].strip()
            if "=" in payload:
                mid_str, _ = payload.split("=", 1)
                try:
                    markers.setdefault(int(mid_str.strip()), {})["exists"] = True
                except ValueError:
                    pass
        elif line.startswith("MARKER_POS:"):
            payload = line[11:].strip()
            if "=" in payload:
                mid_str, coords = payload.split("=", 1)
                try:
                    mid = int(mid_str.strip())
                    if "," in coords:
                        mx_str, my_str = coords.split(",", 1)
                        markers.setdefault(mid, {})["pos"] = (float(mx_str.strip()), float(my_str.strip()))
                except ValueError:
                    pass
        elif line.startswith("MSG_FLUSH_B64:"):
            payload = line[14:].strip()
            if "=" in payload:
                mname, mb64 = payload.split("=", 1)
                try:
                    messages[mname.strip()] = base64.b64decode(mb64.strip()).decode("utf-8")
                except Exception:
                    messages[mname.strip()] = ""
        elif line.startswith("VAR:"):
            var_content = line[4:].strip()
            if "=" in var_content:
                var_name, var_val_str = var_content.split("=", 1)
                var_name = var_name.strip()
                var_val_str = var_val_str.strip()
                try:
                    vars_dict[var_name] = float(var_val_str)
                except ValueError:
                    vars_dict[var_name] = var_val_str

    if not has_run_ok:
        err = "\n".join(lines).strip()
        return RunResult(False, {}, err or "Execution failed without RUN_OK", text_buffer="", messages={})

    return RunResult(
        True,
        vars_dict,
        steps_msg,
        text_buffer=text_buffer,
        messages=messages,
        ticks=ticks,
        ipt=ipt,
        displays=displays,
        graphics_buffer_size=graphics_buffer_size,
        bound_unit=bound_unit,
        text_buffer_len=text_buffer_len,
        announce_text=announce_text,
        toast_text=toast_text,
        notify_text=notify_text,
        mission_text=mission_text,
        cutscene_active=cutscene_active,
        cutscene_hide_hud=cutscene_hide_hud,
        cutscene_zoom=cutscene_zoom,
        cutscene_speed=cutscene_speed,
        cutscene_pan=(cutscene_pan_x, cutscene_pan_y) if has_pan else None,
        shake_intensity=shake_intensity,
        markers_total=markers_total,
        markers=markers,
    )


class _MindustryDaemonClient:
    """Persistent Mindustry JVM daemon client for ultra-fast validation and execution."""

    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._pid = os.getpid()
        self._failed = False
        self._leftover = b""
        self._reader: Optional[threading.Thread] = None
        self._chunks: "queue.Queue[Optional[bytes]]" = queue.Queue()

    def _ensure_started(self) -> bool:
        if os.environ.get("MLOG_DISABLE_DAEMON") == "1":
            return False

        if os.getpid() != self._pid:
            self._proc = None
            self._pid = os.getpid()
            self._failed = False
            self._leftover = b""
            self._reader = None
            self._chunks = queue.Queue()

        if self._failed:
            return False

        if self._proc is not None:
            try:
                if self._proc.poll() is None:
                    return True
            except Exception:
                pass
            # The previous daemon exited unexpectedly.  Close its pipes before
            # replacing it so a crashed process cannot leak file descriptors.
            self._stop()

        cp = get_classpath()
        java_bin = shutil.which("java")
        if not cp or not java_bin:
            self._failed = True
            return False

        try:
            self._chunks = queue.Queue()
            # The harness emits Java warnings on stderr during startup.  A
            # PIPE that is never drained fills up and blocks the JVM before
            # it can print READY, so discard stderr for the long-lived
            # daemon.  The one-shot fallback still captures stderr.
            self._proc = subprocess.Popen(
                _java_command(java_bin, cp, "--daemon"),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            self._reader = threading.Thread(
                target=self._reader_loop,
                args=(self._proc.stdout, self._chunks),
                daemon=True,
            )
            self._reader.start()
            buf = b""
            # Read until READY\n arrives (can take ~5-70s on cold start)
            deadline = time.time() + 120.0
            while b"READY\n" not in buf:
                rem = deadline - time.time()
                if rem <= 0:
                    self._stop()
                    self._failed = True
                    return False
                try:
                    chunk = self._next_chunk(rem)
                except queue.Empty:
                    self._stop()
                    self._failed = True
                    return False
                if chunk is None:
                    self._stop()
                    self._failed = True
                    return False
                buf = (buf + chunk).replace(b"\r\n", b"\n")
            # Discard everything up to READY\n
            idx = buf.index(b"READY\n")
            self._leftover = buf[idx + len(b"READY\n"):]
            return True
        except Exception:
            self._stop()
            self._failed = True
            return False

    @staticmethod
    def _reader_loop(stream, chunks: "queue.Queue[Optional[bytes]]") -> None:
        """Read daemon stdout continuously without blocking the caller.

        ``select.select`` on a pipe is not portable to Windows (it raises
        OSError with WinError 10093), so a daemon thread feeds chunks into a
        queue instead.
        """
        try:
            fd = stream.fileno()
            while True:
                chunk = os.read(fd, 4096)
                if not chunk:
                    break
                chunks.put(chunk)
        except Exception:
            pass
        finally:
            chunks.put(None)

    def _next_chunk(self, timeout_sec: float) -> Optional[bytes]:
        """Return the next stdout chunk (None on EOF); raise on timeout."""
        return self._chunks.get(timeout=max(0.001, timeout_sec))

    @staticmethod
    def _terminate_process(proc) -> None:
        """Terminate a process, escalating to kill and always reaping it."""
        try:
            if proc.poll() is not None:
                return
        except Exception:
            pass

        try:
            proc.terminate()
            proc.wait(timeout=1.0)
            return
        except Exception:
            pass

        try:
            proc.kill()
        except Exception:
            pass
        try:
            proc.wait(timeout=1.0)
        except Exception:
            pass

    def _stop(self):
        self._leftover = b""
        self._reader = None
        self._chunks = queue.Queue()
        proc = self._proc
        if proc:
            if proc.stdin:
                try:
                    proc.stdin.write(b"EXIT\n")
                    proc.stdin.flush()
                except Exception:
                    pass
            self._terminate_process(proc)
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                if stream:
                    try:
                        stream.close()
                    except Exception:
                        pass
            self._proc = None

    def _read_response(self, timeout_sec: float) -> Tuple[Optional[list[str]], bool]:
        deadline = time.time() + timeout_sec
        sentinel = b"<<<END_RESULT>>>\n"
        buf = self._leftover
        self._leftover = b""
        while sentinel not in buf:
            remaining = deadline - time.time()
            if remaining <= 0:
                self._stop()
                return None, True
            try:
                chunk = self._next_chunk(remaining)
            except queue.Empty:
                self._stop()
                return None, True
            if chunk is None:
                self._stop()
                return None, False
            buf = (buf + chunk).replace(b"\r\n", b"\n")

        idx = buf.index(sentinel)
        result_bytes = buf[:idx]
        self._leftover = buf[idx + len(sentinel):]
        text = result_bytes.decode("utf-8", errors="replace")
        lines = [l.strip("\r") for l in text.split("\n")]
        if lines and lines[-1] == "":
            lines.pop()
        return lines, False

    def validate(self, mlog_text: str, timeout_sec: float = 30.0) -> Optional[Tuple[bool, str, int]]:
        with self._lock:
            if not self._ensure_started():
                return None
            try:
                b64 = base64.b64encode(mlog_text.encode("utf-8")).decode("ascii")
                cmd = f"VALIDATE logic {b64}\n".encode("utf-8")
                self._proc.stdin.write(cmd)
                self._proc.stdin.flush()
                lines, timed_out = self._read_response(timeout_sec)
                if timed_out:
                    return False, f"Validation timed out after {timeout_sec}s", -1
                if lines is None:
                    return None
                return _parse_validate_output(lines)
            except Exception:
                self._stop()
                return None

    def run(self, mlog_text: str, max_steps: int = 1000, timeout_sec: float = 30.0) -> Optional[RunResult]:
        with self._lock:
            if not self._ensure_started():
                return None
            try:
                b64 = base64.b64encode(mlog_text.encode("utf-8")).decode("ascii")
                cmd = f"RUN {max_steps} logic {b64}\n".encode("utf-8")
                self._proc.stdin.write(cmd)
                self._proc.stdin.flush()
                lines, timed_out = self._read_response(timeout_sec)
                if timed_out:
                    return RunResult(False, {}, f"Execution timed out after {timeout_sec}s", text_buffer="", messages={})
                if lines is None:
                    return None
                return _parse_run_output(lines)
            except Exception:
                self._stop()
                return None


_DAEMON = _MindustryDaemonClient()
atexit.register(_DAEMON._stop)


def stop_mindustry_daemon() -> None:
    """Explicitly stop the persistent Mindustry JVM daemon if running."""
    _DAEMON._stop()


def validate_with_mindustry(
    mlog_text: str, timeout_sec: float = 30.0
) -> Tuple[bool, str, int]:
    """Validate mlog text using Mindustry's actual LParser and LAssembler.

    Returns:
        (is_valid: bool, message: str, instruction_count: int)
    """
    reason = get_mindustry_unavailable_reason()
    if reason:
        return False, reason, -1

    cp = get_classpath()
    java_bin = shutil.which("java")
    if not cp or not java_bin:
        return False, "Mindustry runtime classpath not available", -1

    # Try fast persistent daemon first
    res = _DAEMON.validate(mlog_text, timeout_sec=timeout_sec)
    if res is not None:
        return res

    # Fallback to one-shot subprocess
    try:
        proc = subprocess.run(
            _java_command(java_bin, cp),
            input=mlog_text,
            text=True,
            capture_output=True,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return False, f"Validation timed out after {timeout_sec}s", -1
    except Exception as e:
        return False, f"Subprocess error: {e}", -1

    if proc.returncode == 0:
        return _parse_validate_output(proc.stdout.splitlines())
    else:
        err = proc.stderr.strip()
        if not err:
            err = proc.stdout.strip()
        return False, err or f"Exited with return code {proc.returncode}", -1


def run_with_mindustry(
    mlog_text: str, max_steps: int = 1000, timeout_sec: float = 30.0
) -> RunResult:
    """Execute mlog text using Mindustry's actual LAssembler and LExecutor.

    Returns:
        RunResult (subclass of tuple[bool, dict, str]):
            - Unpacks as (success, vars_dict, message) for backwards compatibility
            - result.text_buffer: processor textBuffer string
            - result.messages: dict of flushed message block contents (e.g. {"message1": "..."})
    """
    reason = get_mindustry_unavailable_reason()
    if reason:
        return RunResult(False, {}, reason, text_buffer="", messages={})

    cp = get_classpath()
    java_bin = shutil.which("java")
    if not cp or not java_bin:
        return RunResult(False, {}, "Mindustry runtime classpath not available", text_buffer="", messages={})

    # Try fast persistent daemon first
    res = _DAEMON.run(mlog_text, max_steps=max_steps, timeout_sec=timeout_sec)
    if res is not None:
        return res

    # Fallback to one-shot subprocess
    try:
        proc = subprocess.run(
            _java_command(java_bin, cp, "--run", str(max_steps)),
            input=mlog_text,
            text=True,
            capture_output=True,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return RunResult(False, {}, f"Execution timed out after {timeout_sec}s", text_buffer="", messages={})
    except Exception as e:
        return RunResult(False, {}, f"Subprocess error: {e}", text_buffer="", messages={})

    if proc.returncode == 0:
        return _parse_run_output(proc.stdout.splitlines())
    else:
        err = proc.stderr.strip()
        if not err:
            err = proc.stdout.strip()
        return RunResult(False, {}, err or f"Exited with return code {proc.returncode}", text_buffer="", messages={})



if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = sys.stdin.read()

    valid, msg, count = validate_with_mindustry(content)
    if valid:
        print(f"VALID: {count} instructions assembled successfully")
        sys.exit(0)
    else:
        print(f"INVALID: {msg}", file=sys.stderr)
        sys.exit(1)
