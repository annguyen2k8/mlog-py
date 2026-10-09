#!/usr/bin/env python3
"""Build script for Mindustry validation harness (tools/harness/MindustryHarness.java).

Compiles MindustryHarness.java against compiled Mindustry classes and Arc jars,
outputting compiled classes into build/ directory.
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys


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

    # Discover Mindustry classes
    core_path = os.environ.get("MINDUSTRY_CORE_PATH")
    if not core_path:
        core_path = os.path.join(repo_root, "..", "Mindustry", "core", "build", "classes", "java", "main")
    core_path = os.path.abspath(core_path)

    if not os.path.isdir(core_path):
        print(f"Error: Mindustry core classes directory not found: {core_path}", file=sys.stderr)
        print("Hint: Build Mindustry core first or set MINDUSTRY_CORE_PATH.", file=sys.stderr)
        return False

    # Discover Arc jars
    arc_dir = os.environ.get("ARC_JARS_PATH")
    if arc_dir and os.path.isdir(arc_dir):
        arc_jars = glob.glob(os.path.join(arc_dir, "**", "*.jar"), recursive=True)
    else:
        gradle_cache = os.path.expanduser("~/.gradle/caches/modules-2/files-2.1/com.github.Anuken.Arc")
        arc_jars = glob.glob(os.path.join(gradle_cache, "**", "*.jar"), recursive=True)

    if not arc_jars:
        print("Error: No Arc jars found in Gradle cache or ARC_JARS_PATH", file=sys.stderr)
        return False

    classpath = ":".join(arc_jars + [core_path])
    out_path = os.path.abspath(os.path.join(repo_root, output_dir))
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
    sys.path.insert(0, repo_root)
    from src.mindustry_validator import is_mindustry_available, validate_with_mindustry

    if not is_mindustry_available():
        print("Error: Mindustry harness not detected as available", file=sys.stderr)
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
