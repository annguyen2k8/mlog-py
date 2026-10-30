"""Regression tests for JVM harness discovery and classpath construction.

Java requires the platform-specific classpath separator (``;`` on Windows,
``:`` elsewhere). Both the validator and the harness build script must use
``os.pathsep`` rather than a hard-coded POSIX colon.

The discovery tests build synthetic Mindustry/Arc checkouts so they do not
depend on the machine's real checkout layout.
"""

import importlib.util
import io
import json
import os
import subprocess
import tempfile
import threading
import unittest
import zipfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from src import mindustry_discovery, mindustry_validator

_TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
_SPEC = importlib.util.spec_from_file_location(
    "mlog_build_harness", _TOOLS_DIR / "build_harness.py"
)
assert _SPEC is not None and _SPEC.loader is not None
build_harness = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(build_harness)

_DISCOVERY_ENV_KEYS = (
    "MINDUSTRY_CORE_PATH",
    "ARC_JARS_PATH",
    "MINDUSTRY_HARNESS_BUILD",
    "MINDUSTRY_ASSETS_PATH",
    "MLOG_MINDUSTRY_CONFIG",
)


def _write_file(path: Path, data: bytes = b"") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _make_jar(path: Path, entries) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        for entry in entries:
            archive.writestr(entry, b"")
    return path


def _make_core(checkout: Path) -> Path:
    core = checkout / "core" / "build" / "classes" / "java" / "main"
    _write_file(core / "mindustry" / "Vars.class")
    return core


def _make_assets(checkout: Path) -> Path:
    assets = checkout / "core" / "assets"
    _write_file(assets / "logicids.dat", b"\x00\x01")
    return assets


def _make_arc(checkout: Path):
    return [
        _make_jar(
            checkout / "arc-core" / "build" / "libs" / "arc-core-1.0.jar",
            ("arc/Core.class",),
        ),
        _make_jar(
            checkout / "extensions" / "g3d" / "build" / "libs" / "g3d-1.0.jar",
            ("arc/math/geom/Mat3D.class",),
        ),
        _make_jar(
            checkout / "extensions" / "freetype" / "build" / "libs" / "freetype-1.0.jar",
            ("arc/freetype/FreeType.class",),
        ),
    ]


def _make_harness(repo: Path) -> Path:
    harness = repo / "build" / "mindustry" / "test" / "MindustryHarness.class"
    _write_file(harness)
    return harness.parents[2]


def _empty_discovery_env(**overrides) -> dict:
    env = {key: "" for key in _DISCOVERY_ENV_KEYS}
    env.update(overrides)
    return env


@contextmanager
def _isolated_discovery(tmp: str):
    """Keep discovery away from the real user/home checkouts during a test."""
    root = Path(tmp)
    repo = root / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    with patch.object(mindustry_discovery.Path, "home", return_value=root):
        with patch.object(mindustry_discovery.Path, "cwd", return_value=repo):
            yield repo


class TestHarnessClasspath(unittest.TestCase):
    """The harness classpath must use the host platform's separator."""

    def test_find_classpath_uses_os_pathsep(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkout = root / "Mindustry-source"
            core = _make_core(checkout)
            assets = _make_assets(checkout)
            arc_jars = _make_arc(root / "Arc")
            harness = _make_harness(root / "repo")

            env = _empty_discovery_env(
                MINDUSTRY_CORE_PATH=str(core),
                ARC_JARS_PATH=str(root / "Arc"),
                MINDUSTRY_HARNESS_BUILD=str(harness),
                MINDUSTRY_ASSETS_PATH=str(assets),
            )
            with patch.dict(os.environ, env, clear=False):
                # Use a sentinel so the assertion also catches a hard-coded
                # colon when the tests run on POSIX.
                with patch.object(mindustry_validator.os, "pathsep", "|"):
                    classpath = mindustry_validator._find_classpath()

        self.assertIsNotNone(classpath)
        entries = classpath.split("|")
        self.assertEqual(entries[-2:], [str(core), str(harness)])
        self.assertEqual(sorted(entries[:-2]), sorted(str(path) for path in arc_jars))

    def test_build_harness_uses_os_pathsep(self):
        # Keep the temporary output on the repository's drive: build_harness.py
        # prints a relative path, and os.path.relpath cannot cross Windows drives.
        with tempfile.TemporaryDirectory(dir=str(_TOOLS_DIR)) as tmp:
            root = Path(tmp)
            core = _make_core(root / "Mindustry-source")
            arc_jars = _make_arc(root / "Arc")
            output = root / "build"

            env = _empty_discovery_env(
                MINDUSTRY_CORE_PATH=str(core),
                ARC_JARS_PATH=str(root / "Arc"),
            )
            with patch.dict(os.environ, env, clear=False):
                with patch.object(build_harness.shutil, "which", return_value="javac"):
                    with patch.object(build_harness.subprocess, "run") as run:
                        run.return_value = subprocess.CompletedProcess(
                            args=[], returncode=0
                        )
                        with patch.object(build_harness.os, "pathsep", "|"):
                            ok = build_harness.build_harness(output_dir=str(output))

        self.assertTrue(ok)
        cmd = run.call_args.args[0]
        classpath = cmd[cmd.index("-cp") + 1]
        entries = classpath.split("|")
        self.assertEqual(entries[-1], str(core))
        self.assertEqual(sorted(entries[:-1]), sorted(str(path) for path in arc_jars))


class TestMindustryDaemonProtocol(unittest.TestCase):
    """The daemon protocol must tolerate CRLF emitted by the Windows JVM."""

    def test_daemon_accepts_crlf_ready_and_result_sentinel(self):
        client = mindustry_validator._MindustryDaemonClient()
        read_fd, write_fd = os.pipe()
        stream = os.fdopen(read_fd, "rb", buffering=0)

        class FakeProcess:
            def __init__(self):
                self.stdin = io.BytesIO()
                self.stdout = stream
                self.stderr = None

            def poll(self):
                return None

            def terminate(self):
                pass

            def wait(self, timeout=None):
                return 0

            def kill(self):
                pass

        proc = FakeProcess()

        def write_all():
            try:
                os.write(
                    write_fd,
                    b"READY\r\nRESULT:OK\r\n<<<END_RESULT>>>\r\n",
                )
            finally:
                os.close(write_fd)

        writer = threading.Thread(target=write_all, daemon=True)
        writer.start()

        with patch.object(mindustry_validator, "get_classpath", return_value="cp"):
            with patch.object(
                mindustry_validator.shutil, "which", return_value="java"
            ):
                with patch.object(
                    mindustry_validator,
                    "_java_command",
                    return_value=["java", "--daemon"],
                ):
                    with patch.object(
                        mindustry_validator.subprocess, "Popen", return_value=proc
                    ):
                        try:
                            self.assertTrue(client._ensure_started())
                            lines, timed_out = client._read_response(1.0)
                        finally:
                            client._stop()
                            writer.join(timeout=1.0)

        self.assertFalse(timed_out)
        self.assertEqual(lines, ["RESULT:OK"])


class TestMindustryDiscovery(unittest.TestCase):
    """Validated discovery from environment, config, and sibling checkouts."""

    def test_discovers_sibling_checkouts_without_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _isolated_discovery(tmp) as repo:
                checkout = Path(tmp) / "Mindustry-source"
                core = _make_core(checkout)
                assets = _make_assets(checkout)
                arc_jars = _make_arc(Path(tmp) / "Arc")
                harness = _make_harness(repo)

                with patch.dict(os.environ, _empty_discovery_env(), clear=False):
                    result = mindustry_discovery.discover(repo)

            self.assertTrue(result.available, result.error)
            self.assertEqual(result.core_path, str(core))
            self.assertEqual(result.assets_path, str(assets))
            self.assertEqual(result.harness_build, str(harness))
            self.assertEqual(
                sorted(result.arc_entries), sorted(str(path) for path in arc_jars)
            )

    def test_environment_core_checkout_derives_classes_and_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _isolated_discovery(tmp) as repo:
                checkout = Path(tmp) / "Mindustry-source"
                core = _make_core(checkout)
                assets = _make_assets(checkout)
                _make_arc(Path(tmp) / "Arc")
                harness = _make_harness(repo)

                env = _empty_discovery_env(
                    MINDUSTRY_CORE_PATH=str(checkout),
                    ARC_JARS_PATH=str(Path(tmp) / "Arc"),
                    MINDUSTRY_HARNESS_BUILD=str(harness),
                )
                with patch.dict(os.environ, env, clear=False):
                    result = mindustry_discovery.discover(repo)

            self.assertTrue(result.available, result.error)
            self.assertEqual(result.core_path, str(core))
            self.assertEqual(result.assets_path, str(assets))

    def test_config_file_relative_paths_are_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _isolated_discovery(tmp) as repo:
                checkout = Path(tmp) / "custom-mindustry"
                core = _make_core(checkout)
                assets = _make_assets(checkout)
                arc_jars = _make_arc(Path(tmp) / "custom-arc")
                harness = _make_harness(Path(tmp) / "custom-build")

                config = {
                    "core_path": os.path.relpath(core, repo),
                    "arc_path": os.path.relpath(Path(tmp) / "custom-arc", repo),
                    "harness_build": os.path.relpath(harness, repo),
                    "assets_path": os.path.relpath(assets, repo),
                }
                (repo / ".mindustry.json").write_text(
                    json.dumps(config), encoding="utf-8"
                )

                with patch.dict(os.environ, _empty_discovery_env(), clear=False):
                    result = mindustry_discovery.discover(repo)

            self.assertTrue(result.available, result.error)
            self.assertEqual(result.core_path, str(core))
            self.assertEqual(result.assets_path, str(assets))
            self.assertEqual(result.harness_build, str(harness))
            self.assertEqual(
                sorted(result.arc_entries), sorted(str(path) for path in arc_jars)
            )

    def test_environment_takes_precedence_over_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _isolated_discovery(tmp) as repo:
                env_checkout = Path(tmp) / "env-mindustry"
                env_core = _make_core(env_checkout)
                config_checkout = Path(tmp) / "config-mindustry"
                config_core = _make_core(config_checkout)
                _make_arc(Path(tmp) / "Arc")
                harness = _make_harness(repo)
                assets = _make_assets(env_checkout)

                (repo / ".mindustry.json").write_text(
                    json.dumps({"core_path": str(config_core)}), encoding="utf-8"
                )
                env = _empty_discovery_env(
                    MINDUSTRY_CORE_PATH=str(env_core),
                    ARC_JARS_PATH=str(Path(tmp) / "Arc"),
                    MINDUSTRY_HARNESS_BUILD=str(harness),
                    MINDUSTRY_ASSETS_PATH=str(assets),
                )
                with patch.dict(os.environ, env, clear=False):
                    result = mindustry_discovery.discover(repo)

            self.assertEqual(result.core_path, str(env_core))

    def test_missing_assets_reports_logicids_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _isolated_discovery(tmp) as repo:
                checkout = Path(tmp) / "Mindustry-source"
                core = _make_core(checkout)  # deliberately no assets
                # A different checkout has assets; they must not be mixed in.
                _make_assets(Path(tmp) / "Mindustry")
                _make_arc(Path(tmp) / "Arc")
                harness = _make_harness(repo)

                env = _empty_discovery_env(
                    MINDUSTRY_CORE_PATH=str(core),
                    ARC_JARS_PATH=str(Path(tmp) / "Arc"),
                    MINDUSTRY_HARNESS_BUILD=str(harness),
                )
                with patch.dict(os.environ, env, clear=False):
                    result = mindustry_discovery.discover(repo)

            self.assertFalse(result.available)
            self.assertIn("logicids.dat", result.error)

    def test_missing_harness_reports_build_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _isolated_discovery(tmp) as repo:
                checkout = Path(tmp) / "Mindustry-source"
                core = _make_core(checkout)
                assets = _make_assets(checkout)
                _make_arc(Path(tmp) / "Arc")

                env = _empty_discovery_env(
                    MINDUSTRY_CORE_PATH=str(core),
                    ARC_JARS_PATH=str(Path(tmp) / "Arc"),
                    MINDUSTRY_ASSETS_PATH=str(assets),
                )
                with patch.dict(os.environ, env, clear=False):
                    result = mindustry_discovery.discover(repo)

            self.assertFalse(result.available)
            self.assertIn("harness is not built", result.error)
            self.assertIn("tools/build_harness.py", result.error)

    def test_missing_core_reports_core_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _isolated_discovery(tmp) as repo:
                checkout = Path(tmp) / "Mindustry-source"
                assets = _make_assets(checkout)
                _make_arc(Path(tmp) / "Arc")
                harness = _make_harness(repo)

                env = _empty_discovery_env(
                    ARC_JARS_PATH=str(Path(tmp) / "Arc"),
                    MINDUSTRY_HARNESS_BUILD=str(harness),
                    MINDUSTRY_ASSETS_PATH=str(assets),
                )
                with patch.dict(os.environ, env, clear=False):
                    result = mindustry_discovery.discover(repo)

            self.assertFalse(result.available)
            self.assertIn("Mindustry core classes not found", result.error)

    def test_broken_arc_reports_missing_required_class(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _isolated_discovery(tmp) as repo:
                checkout = Path(tmp) / "Mindustry-source"
                core = _make_core(checkout)
                assets = _make_assets(checkout)
                harness = _make_harness(repo)
                broken_arc = Path(tmp) / "broken-arc"
                _make_jar(broken_arc / "arc-core-1.0.jar", ("arc/Core.class",))

                env = _empty_discovery_env(
                    MINDUSTRY_CORE_PATH=str(core),
                    ARC_JARS_PATH=str(broken_arc),
                    MINDUSTRY_HARNESS_BUILD=str(harness),
                    MINDUSTRY_ASSETS_PATH=str(assets),
                )
                with patch.dict(os.environ, env, clear=False):
                    result = mindustry_discovery.discover(repo)

            self.assertFalse(result.available)
            self.assertIn("Mat3D", result.error)
            self.assertIn("FreeType", result.error)

    def test_gradle_cache_combines_required_arc_jars(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _isolated_discovery(tmp) as repo:
                checkout = Path(tmp) / "Mindustry-source"
                core = _make_core(checkout)
                assets = _make_assets(checkout)
                harness = _make_harness(repo)

                cache = (
                    Path(tmp)
                    / ".gradle"
                    / "caches"
                    / "modules-2"
                    / "files-2.1"
                    / "com.github.Anuken.Arc"
                )
                cache_jars = [
                    _make_jar(
                        cache / "arc-core" / "1.0" / "abc" / "arc-core-1.0.jar",
                        ("arc/Core.class",),
                    ),
                    _make_jar(
                        cache / "g3d" / "1.0" / "def" / "g3d-1.0.jar",
                        ("arc/math/geom/Mat3D.class",),
                    ),
                    _make_jar(
                        cache / "freetype" / "1.0" / "ghi" / "freetype-1.0.jar",
                        ("arc/freetype/FreeType.class",),
                    ),
                ]

                env = _empty_discovery_env(
                    MINDUSTRY_CORE_PATH=str(core),
                    MINDUSTRY_HARNESS_BUILD=str(harness),
                    MINDUSTRY_ASSETS_PATH=str(assets),
                )
                with patch.dict(os.environ, env, clear=False):
                    result = mindustry_discovery.discover(repo)

            self.assertTrue(result.available, result.error)
            self.assertEqual(
                sorted(result.arc_entries), sorted(str(path) for path in cache_jars)
            )

    def test_java_command_injects_discovered_assets(self):
        discovery = mindustry_discovery.MindustryDiscovery(
            core_path="core",
            arc_entries=("arc.jar",),
            harness_build="harness",
            assets_path=os.path.join("assets", "core"),
            error=None,
        )
        with patch.object(mindustry_validator, "_get_discovery", return_value=discovery):
            command = mindustry_validator._java_command("java", "classpath", "--daemon")

        self.assertEqual(
            command,
            [
                "java",
                f"-Dmindustry.assets={os.path.join('assets', 'core')}",
                "-cp",
                "classpath",
                "mindustry.test.MindustryHarness",
                "--daemon",
            ],
        )

    def test_unavailable_reason_is_specific(self):
        with patch.object(mindustry_validator.shutil, "which", return_value=None):
            reason = mindustry_validator.get_mindustry_unavailable_reason()
        self.assertIn("Java runtime not found", reason)


if __name__ == "__main__":
    unittest.main()
