"""Mindustry Real Assembly & Parser Validator Bridge.

Uses the compiled Mindustry engine classes and MindustryHarness via Java
to validate generated mlog directly against Mindustry's actual LParser & LAssembler.
"""

import base64
import glob
import os
import shutil
import subprocess
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
        count = 0
        for line in proc.stdout.splitlines():
            if line.startswith("OK:"):
                try:
                    count = int(line[3:].strip())
                except ValueError:
                    count = 0
        return True, "OK", count
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
        for line in proc.stdout.splitlines():
            if line.startswith("RUN_OK:"):
                steps_msg = line.strip()
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
