#!/usr/bin/env python3
"""Build script for Mindustry validation harness (tools/harness/MindustryHarness.java).

Compiles MindustryHarness.java against compiled Mindustry classes and Arc jars,
outputting compiled classes into build/ directory.
"""

import argparse
import os
import shutil
import subprocess
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from src.mindustry_discovery import find_arc_entries, find_mindustry_core


def _output_path(repo_root: str, output_dir: str) -> str:
    if os.path.isabs(output_dir):
        return os.path.abspath(output_dir)
    return os.path.abspath(os.path.join(repo_root, output_dir))


def build_harness(output_dir: str = "build") -> bool:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    java_src = os.path.join(repo_root, "tools", "harness", "MindustryHarness.java")

    if not os.path.isfile(java_src):
        print(f"Error: Harness source not found: {java_src}", file=sys.stderr)
        return False

    javac_bin = shutil.which("javac")
    if not javac_bin:
        print("Error: 'javac' compiler not found in PATH", file=sys.stderr)
        return False

    core_path, core_error = find_mindustry_core(repo_root)
    if not core_path:
        print(f"Error: {core_error}", file=sys.stderr)
        print("Hint: Build Mindustry core first or set MINDUSTRY_CORE_PATH.", file=sys.stderr)
        return False

    arc_entries, arc_error = find_arc_entries(repo_root)
    if not arc_entries:
        print(f"Error: {arc_error}", file=sys.stderr)
        return False

    classpath = os.pathsep.join(list(arc_entries) + [core_path])
    out_path = _output_path(repo_root, output_dir)
    os.makedirs(out_path, exist_ok=True)

    cmd = [javac_bin, "-cp", classpath, java_src, "-d", out_path]
    print(f"Compiling {os.path.relpath(java_src, repo_root)} -> {os.path.relpath(out_path, repo_root)}...")
    res = subprocess.run(cmd)

    if res.returncode == 0:
        print(f"Successfully compiled MindustryHarness to {out_path}")
        return True
    else:
        print(f"Compilation failed with exit code {res.returncode}", file=sys.stderr)
        return False


def test_harness(output_dir: str = "build") -> bool:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    # Make a custom -o output discoverable for the sanity check, while still
    # respecting an explicitly configured harness location.
    os.environ.setdefault("MINDUSTRY_HARNESS_BUILD", _output_path(repo_root, output_dir))

    from src.mindustry_validator import (
        get_mindustry_unavailable_reason,
        validate_with_mindustry,
    )

    reason = get_mindustry_unavailable_reason()
    if reason:
        print(f"Error: {reason}", file=sys.stderr)
        return False

    sample_mlog = "set a 10\nprint a\nprintflush message1\n"
    ok, msg, count = validate_with_mindustry(sample_mlog)
    if ok:
        print(f"Sanity test passed! Assembled {count} instructions cleanly.")
        return True
    else:
        print(f"Sanity test failed: {msg}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Compile Mindustry validation harness")
    parser.add_argument("-o", "--output", default="build", help="Output directory (default: build)")
    parser.add_argument("--test", action="store_true", help="Run sanity validation test after building")
    args = parser.parse_args()

    success = build_harness(args.output)
    if not success:
        sys.exit(1)

    if args.test:
        if not test_harness(args.output):
            sys.exit(1)


if __name__ == "__main__":
    main()
