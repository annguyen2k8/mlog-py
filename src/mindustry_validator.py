"""Mindustry Real Assembly & Parser Validator Bridge.

Uses the compiled Mindustry engine classes and MindustryHarness via Java
to validate generated mlog directly against Mindustry's actual LParser & LAssembler.
"""

import glob
import os
import shutil
import subprocess
from typing import Optional, Tuple


def _find_classpath() -> Optional[str]:
    """Discover classpath for Mindustry engine and MindustryHarness."""
    src_dir = os.path.dirname(os.path.abspath(__file__))
    mlog_py_root = os.path.abspath(os.path.join(src_dir, ".."))
    harness_build = os.path.join(mlog_py_root, "build")

    # Mindustry core classes
    mindustry_core_classes = os.path.abspath(
        os.path.join(mlog_py_root, "..", "Mindustry", "core", "build", "classes", "java", "main")
    )

    # Arc dependencies from Gradle cache
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
