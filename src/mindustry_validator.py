"""Mindustry Real Assembly & Parser Validator Bridge.

Uses the compiled Mindustry engine classes and MindustryHarness via Java
to validate generated mlog directly against Mindustry's actual LParser & LAssembler.
"""

import atexit
import base64
import glob
import os
import select
import shutil
import subprocess
import threading
import time
from typing import Optional, Tuple


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


def _find_classpath() -> Optional[str]:
    """Discover classpath for Mindustry engine and MindustryHarness."""
    src_dir = os.path.dirname(os.path.abspath(__file__))
    mlog_py_root = os.path.abspath(os.path.join(src_dir, ".."))
    harness_build = os.environ.get("MINDUSTRY_HARNESS_BUILD", os.path.join(mlog_py_root, "build"))

    # Mindustry core classes
    env_core = os.environ.get("MINDUSTRY_CORE_PATH")
    if env_core:
        mindustry_core_classes = os.path.abspath(env_core)
    else:
        mindustry_core_classes = os.path.abspath(
            os.path.join(mlog_py_root, "..", "Mindustry", "core", "build", "classes", "java", "main")
        )

    # Arc dependencies from Gradle cache
    env_arc = os.environ.get("ARC_JARS_PATH")
    if env_arc and os.path.isdir(env_arc):
        arc_jars = glob.glob(os.path.join(env_arc, "**", "*.jar"), recursive=True)
    else:
        gradle_cache = os.path.expanduser("~/.gradle/caches/modules-2/files-2.1/com.github.Anuken.Arc")
        arc_jars = glob.glob(os.path.join(gradle_cache, "**", "*.jar"), recursive=True)

    if not os.path.exists(harness_build):
        return None
    if not os.path.exists(mindustry_core_classes):
        return None
    if not arc_jars:
        return None

    cp_entries = arc_jars + [mindustry_core_classes, harness_build]
    return ":".join(cp_entries)


_CACHED_CP = None
_CHECKED_CP = False


def get_classpath() -> Optional[str]:
    """Get the cached classpath if available."""
    global _CACHED_CP, _CHECKED_CP
    if not _CHECKED_CP:
        _CACHED_CP = _find_classpath()
        _CHECKED_CP = True
    return _CACHED_CP


def is_mindustry_available() -> bool:
    """Check if Java and Mindustry classes are available for real validation."""
    if not shutil.which("java"):
        return False
    return get_classpath() is not None


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

    def _ensure_started(self) -> bool:
        if os.environ.get("MLOG_DISABLE_DAEMON") == "1":
            return False

        if os.getpid() != self._pid:
            self._proc = None
            self._pid = os.getpid()
            self._failed = False
            self._leftover = b""

        if self._failed:
            return False

        if self._proc is not None and self._proc.poll() is None:
            return True

        cp = get_classpath()
        java_bin = shutil.which("java")
        if not cp or not java_bin:
            self._failed = True
            return False

        try:
            self._proc = subprocess.Popen(
                [java_bin, "-cp", cp, "mindustry.test.MindustryHarness", "--daemon"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            fd = self._proc.stdout.fileno()
            buf = b""
            # Read until READY\n arrives (can take ~5-70s on cold start)
            deadline = time.time() + 120.0
            while b"READY\n" not in buf:
                rem = deadline - time.time()
                if rem <= 0:
                    self._stop()
                    self._failed = True
                    return False
                r, _, _ = select.select([fd], [], [], max(0.001, rem))
                if not r:
                    self._stop()
                    self._failed = True
                    return False
                chunk = os.read(fd, 1024)
                if not chunk:
                    self._stop()
                    self._failed = True
                    return False
                buf += chunk
            # Discard everything up to READY\n
            idx = buf.index(b"READY\n")
            self._leftover = buf[idx + len(b"READY\n"):]
            return True
        except Exception:
            self._stop()
            self._failed = True
            return False

    def _stop(self):
        self._leftover = b""
        if self._proc:
            try:
                if self._proc.poll() is None:
                    if self._proc.stdin:
                        try:
                            self._proc.stdin.write(b"EXIT\n")
                            self._proc.stdin.flush()
                        except Exception:
                            pass
                    self._proc.terminate()
                    self._proc.wait(timeout=1.0)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            try:
                if self._proc.stdin:
                    self._proc.stdin.close()
                if self._proc.stdout:
                    self._proc.stdout.close()
                if self._proc.stderr:
                    self._proc.stderr.close()
            except Exception:
                pass
            self._proc = None

    def _read_response(self, timeout_sec: float) -> Tuple[Optional[list[str]], bool]:
        deadline = time.time() + timeout_sec
        fd = self._proc.stdout.fileno()
        sentinel = b"<<<END_RESULT>>>\n"
        buf = self._leftover
        self._leftover = b""
        while sentinel not in buf:
            remaining = deadline - time.time()
            if remaining <= 0:
                self._stop()
                return None, True
            r, _, _ = select.select([fd], [], [], max(0.001, remaining))
            if not r:
                self._stop()
                return None, True
            try:
                chunk = os.read(fd, 4096)
            except Exception:
                self._stop()
                return None, False
            if not chunk:
                self._stop()
                return None, False
            buf += chunk

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
    cp = get_classpath()
    if not cp:
        return False, "Mindustry runtime classpath not available", -1

    java_bin = shutil.which("java")
    if not java_bin:
        return False, "Java runtime not available", -1

    # Try fast persistent daemon first
    res = _DAEMON.validate(mlog_text, timeout_sec=timeout_sec)
    if res is not None:
        return res

    # Fallback to one-shot subprocess
    try:
        proc = subprocess.run(
            [java_bin, "-cp", cp, "mindustry.test.MindustryHarness"],
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
    cp = get_classpath()
    if not cp:
        return RunResult(False, {}, "Mindustry runtime classpath not available", text_buffer="", messages={})

    java_bin = shutil.which("java")
    if not java_bin:
        return RunResult(False, {}, "Java runtime not available", text_buffer="", messages={})

    # Try fast persistent daemon first
    res = _DAEMON.run(mlog_text, max_steps=max_steps, timeout_sec=timeout_sec)
    if res is not None:
        return res

    # Fallback to one-shot subprocess
    try:
        proc = subprocess.run(
            [java_bin, "-cp", cp, "mindustry.test.MindustryHarness", "--run", str(max_steps)],
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
