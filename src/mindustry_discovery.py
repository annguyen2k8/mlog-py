"""Discovery of the Mindustry JVM harness and its runtime dependencies.

The validator and ``tools/build_harness.py`` share this module so that both
use exactly the same search order:

1. Explicit environment variables (``MINDUSTRY_CORE_PATH``, ``ARC_JARS_PATH``,
   ``MINDUSTRY_HARNESS_BUILD`` and ``MINDUSTRY_ASSETS_PATH``).
2. Paths from an optional JSON config file (``MLOG_MINDUSTRY_CONFIG``,
   ``.mindustry.json`` in the repository, or the per-user config directory).
3. Common sibling checkouts/build outputs, including ``Mindustry-source`` and
   a local ``Arc`` checkout.

Every candidate is validated before it is used.  In particular a Mindustry
"core path" must contain ``mindustry/Vars.class`` (either as a directory or in
a jar), Arc must provide the classes required by the harness, and the harness
build must contain ``mindustry/test/MindustryHarness.class``.
"""

from __future__ import annotations

import json
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


_REPO_ROOT = Path(__file__).resolve().parents[1]

_CORE_CLASS = ("mindustry", "Vars.class")
_ARC_REQUIRED_CLASSES = (
    ("arc", "Core.class"),
    ("arc", "math", "geom", "Mat3D.class"),
    ("arc", "freetype", "FreeType.class"),
)
_HARNESS_CLASS = ("mindustry", "test", "MindustryHarness.class")


@dataclass(frozen=True)
class MindustryDiscovery:
    """Validated locations needed to launch the Mindustry harness."""

    core_path: Optional[str]
    arc_entries: Tuple[str, ...]
    harness_build: Optional[str]
    assets_path: Optional[str]
    error: Optional[str]

    @property
    def available(self) -> bool:
        return self.classpath is not None and self.assets_path is not None

    @property
    def classpath(self) -> Optional[str]:
        if not self.core_path or not self.arc_entries or not self.harness_build:
            return None
        entries = list(self.arc_entries)
        entries.extend((self.core_path, self.harness_build))
        return os.pathsep.join(entries)


def _expand_path(value: str, base: Optional[Path] = None) -> str:
    path = Path(os.path.expandvars(os.path.expanduser(str(value))))
    if not path.is_absolute() and base is not None:
        path = base / path
    return str(path.resolve())


def _unique_paths(paths: Iterable[Path]) -> List[Path]:
    seen = set()
    result: List[Path] = []
    for path in paths:
        key = os.path.normcase(os.path.abspath(str(path)))
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def _entry_contains(entry: str, parts: Sequence[str]) -> bool:
    """Return True when ``entry`` (a class directory or jar) has ``parts``."""
    path = Path(entry)
    if path.is_dir():
        return path.joinpath(*parts).is_file()
    if path.is_file() and path.suffix.lower() == ".jar":
        try:
            with zipfile.ZipFile(path) as archive:
                archive.getinfo("/".join(parts))
            return True
        except (KeyError, OSError, zipfile.BadZipFile):
            return False
    return False


def _is_runtime_jar(path: Path) -> bool:
    name = path.name.lower()
    if not name.endswith(".jar"):
        return False
    if name in {"android.jar", "gradle-wrapper.jar"}:
        return False
    return "-sources" not in name and "-javadoc" not in name


def _config_candidates(repo_root: Path) -> List[str]:
    candidates: List[str] = []
    explicit = os.environ.get("MLOG_MINDUSTRY_CONFIG")
    if explicit:
        candidates.append(_expand_path(explicit))

    candidates.append(str(repo_root / ".mindustry.json"))
    candidates.append(str(Path.home() / ".config" / "mlog-py" / "mindustry.json"))
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(str(Path(appdata) / "mlog-py" / "mindustry.json"))
    return list(dict.fromkeys(candidates))


def load_config(repo_root: Optional[Path] = None) -> Tuple[Dict[str, str], Optional[str]]:
    """Load the first available Mindustry discovery config file.

    Relative paths are resolved against the config file's directory.  Invalid
    JSON is reported as an error but does not prevent the normal search from
    continuing.
    """
    root = Path(repo_root or _REPO_ROOT)
    for candidate in _config_candidates(root):
        if not os.path.isfile(candidate):
            continue
        try:
            with open(candidate, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError) as exc:
            return {}, f"Invalid Mindustry discovery config {candidate}: {exc}"
        if not isinstance(data, dict):
            return {}, f"Invalid Mindustry discovery config {candidate}: expected a JSON object"

        base = Path(candidate).parent
        resolved: Dict[str, str] = {}
        for key in (
            "core_path",
            "arc_path",
            "arc_jars_path",
            "harness_build",
            "assets_path",
        ):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                resolved[key] = _expand_path(value, base)
        return resolved, None
    return {}, None


def _candidate_checkout_roots(repo_root: Path, name: str) -> List[Path]:
    """Find likely Mindustry/Arc checkouts without machine-specific paths."""
    bases = [
        repo_root,
        repo_root.parent,
        repo_root.parent.parent,
        Path.cwd(),
        Path.cwd().parent,
        Path.home(),
    ]
    for sub in ("src", "projects", "dev", "git", "repos"):
        bases.append(Path.home() / sub)

    roots: List[Path] = []
    for base in bases:
        if not base.is_dir():
            continue
        for candidate_name in (
            name,
            name.lower(),
            f"{name}-source",
            f"{name.lower()}-source",
        ):
            candidate = base / candidate_name
            if candidate.is_dir():
                roots.append(candidate)
        for pattern in (f"{name}*", f"{name.lower()}*"):
            for candidate in sorted(base.glob(pattern)):
                if candidate.is_dir():
                    roots.append(candidate)
    return _unique_paths(roots)


def _gradle_artifact_jars(group: str) -> List[Path]:
    root = Path.home() / ".gradle" / "caches" / "modules-2" / "files-2.1" / group
    if not root.is_dir():
        return []
    return [path for path in sorted(root.glob("**/*.jar")) if _is_runtime_jar(path)]


def _maven_artifact_jars(group_path: Sequence[str]) -> List[Path]:
    root = Path.home() / ".m2" / "repository"
    for part in group_path:
        root = root / part
    if not root.is_dir():
        return []
    return [path for path in sorted(root.glob("**/*.jar")) if _is_runtime_jar(path)]


def _core_candidates(root: Path) -> List[Path]:
    """Yield possible compiled-core locations below a checkout/build root."""
    candidates: List[Path] = []
    if root.is_file():
        if root.suffix.lower() == ".jar":
            candidates.append(root)
        return candidates
    if not root.is_dir():
        return candidates

    if _entry_contains(str(root), _CORE_CLASS):
        candidates.append(root)

    for relative in (
        ("core", "build", "classes", "java", "main"),
        ("build", "classes", "java", "main"),
        ("core", "build", "classes", "kotlin", "main"),
        ("build", "classes", "kotlin", "main"),
    ):
        candidate = root.joinpath(*relative)
        if candidate.is_dir():
            candidates.append(candidate)

    for pattern in ("*.jar", "core/build/libs/*.jar", "build/libs/*.jar"):
        for candidate in sorted(root.glob(pattern)):
            if _is_runtime_jar(candidate):
                candidates.append(candidate)
    return _unique_paths(candidates)


def find_mindustry_core(
    repo_root: Optional[Path] = None,
    config: Optional[Dict[str, str]] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Find compiled Mindustry core classes, validating the required class."""
    root = Path(repo_root or _REPO_ROOT)
    config = config or {}
    errors: List[str] = []

    explicit = os.environ.get("MINDUSTRY_CORE_PATH")
    if explicit:
        expanded = _expand_path(explicit)
        for candidate in _core_candidates(Path(expanded)):
            if _entry_contains(str(candidate), _CORE_CLASS):
                return str(candidate), None
        errors.append(
            "MINDUSTRY_CORE_PATH does not contain compiled Mindustry classes "
            f"(missing {'/'.join(_CORE_CLASS)}): {expanded}"
        )

    configured = config.get("core_path")
    if configured:
        for candidate in _core_candidates(Path(configured)):
            if _entry_contains(str(candidate), _CORE_CLASS):
                return str(candidate), None
        errors.append(
            "Configured core_path does not contain compiled Mindustry classes "
            f"(missing {'/'.join(_CORE_CLASS)}): {configured}"
        )

    for checkout in _candidate_checkout_roots(root, "Mindustry"):
        for candidate in _core_candidates(checkout):
            if _entry_contains(str(candidate), _CORE_CLASS):
                return str(candidate), None

    for jar in _gradle_artifact_jars("com.github.Anuken.Mindustry"):
        if _entry_contains(str(jar), _CORE_CLASS):
            return str(jar), None
    for jar in _maven_artifact_jars(("com", "github", "Anuken", "Mindustry")):
        if _entry_contains(str(jar), _CORE_CLASS):
            return str(jar), None

    hint = (
        "Mindustry core classes not found. Set MINDUSTRY_CORE_PATH to a compiled "
        "core classes directory (for example <Mindustry>/core/build/classes/java/main) "
        "or build a sibling Mindustry checkout."
    )
    errors.append(hint)
    return None, "; ".join(errors)


def _looks_like_arc_checkout(root: Path) -> bool:
    return (
        (root / "arc-core").is_dir()
        or (root / "settings.gradle").is_file()
        or (root / "settings.gradle.kts").is_file()
    )


def _arc_entries_from_root(root: Path) -> List[str]:
    if root.is_file():
        return [str(root)] if _is_runtime_jar(root) else []
    if not root.is_dir():
        return []

    # The path may point directly at a module classes directory.  Accept it
    # when it provides at least one required Arc class; the caller combines
    # pathsep-separated entries and validates the complete set.
    if any(_entry_contains(str(root), parts) for parts in _ARC_REQUIRED_CLASSES):
        return [str(root)]

    if _looks_like_arc_checkout(root):
        jars = [
            path
            for path in sorted(root.glob("**/build/libs/*.jar"))
            if _is_runtime_jar(path)
        ]
        if jars:
            return [str(path) for path in _unique_paths(jars)]

        class_dirs: List[Path] = []
        for relative in (
            ("arc-core", "build", "classes", "java", "main"),
            ("extensions", "g3d", "build", "classes", "java", "main"),
            ("extensions", "freetype", "build", "classes", "java", "main"),
        ):
            candidate = root.joinpath(*relative)
            if candidate.is_dir():
                class_dirs.append(candidate)
        for pattern in ("*/build/classes/java/main", "*/*/build/classes/java/main"):
            class_dirs.extend(path for path in sorted(root.glob(pattern)) if path.is_dir())
        return [str(path) for path in _unique_paths(class_dirs)]

    return [
        str(path)
        for path in _unique_paths(sorted(root.glob("**/*.jar")))
        if _is_runtime_jar(path)
    ]


def _missing_arc_classes(entries: Sequence[str]) -> List[str]:
    missing: List[str] = []
    for parts in _ARC_REQUIRED_CLASSES:
        if not any(_entry_contains(entry, parts) for entry in entries):
            missing.append("/".join(parts))
    return missing


def _find_arc_from_value(value: str) -> Tuple[Tuple[str, ...], List[str]]:
    entries: List[str] = []
    for part in value.split(os.pathsep):
        if not part.strip():
            continue
        entries.extend(_arc_entries_from_root(Path(_expand_path(part))))
    unique = tuple(str(path) for path in _unique_paths(Path(entry) for entry in entries))
    return unique, _missing_arc_classes(unique)


def find_arc_entries(
    repo_root: Optional[Path] = None,
    config: Optional[Dict[str, str]] = None,
) -> Tuple[Tuple[str, ...], Optional[str]]:
    """Find Arc jars/classes required by the Mindustry harness."""
    root = Path(repo_root or _REPO_ROOT)
    config = config or {}
    errors: List[str] = []

    explicit = os.environ.get("ARC_JARS_PATH")
    if explicit:
        entries, missing = _find_arc_from_value(explicit)
        if entries and not missing:
            return entries, None
        if missing:
            errors.append(
                "ARC_JARS_PATH is missing required Arc classes: " + ", ".join(missing)
            )
        else:
            errors.append(f"ARC_JARS_PATH does not contain Arc jars or classes: {explicit}")

    configured = config.get("arc_path") or config.get("arc_jars_path")
    if configured:
        entries, missing = _find_arc_from_value(configured)
        if entries and not missing:
            return entries, None
        if missing:
            errors.append(
                "Configured arc_path is missing required Arc classes: " + ", ".join(missing)
            )

    for checkout in _candidate_checkout_roots(root, "Arc"):
        entries = tuple(_arc_entries_from_root(checkout))
        if entries and not _missing_arc_classes(entries):
            return entries, None

    for jars in (
        _gradle_artifact_jars("com.github.Anuken.Arc"),
        _maven_artifact_jars(("com", "github", "Anuken", "Arc")),
    ):
        entries = tuple(str(jar) for jar in jars)
        if entries and not _missing_arc_classes(entries):
            return entries, None

    hint = (
        "Arc libraries not found. Set ARC_JARS_PATH to an Arc checkout, a build/libs "
        "directory, or pathsep-separated Arc jars/classes, or build a sibling Arc checkout."
    )
    errors.append(hint)
    return (), "; ".join(errors)


def find_harness_build(
    repo_root: Optional[Path] = None,
    config: Optional[Dict[str, str]] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Find a compiled ``MindustryHarness`` output directory."""
    root = Path(repo_root or _REPO_ROOT)
    config = config or {}
    errors: List[str] = []

    explicit = os.environ.get("MINDUSTRY_HARNESS_BUILD")
    if explicit:
        expanded = _expand_path(explicit)
        if _entry_contains(expanded, _HARNESS_CLASS):
            return expanded, None
        errors.append(
            "MINDUSTRY_HARNESS_BUILD does not contain "
            f"{'/'.join(_HARNESS_CLASS)}: {expanded}"
        )

    configured = config.get("harness_build")
    if configured:
        if _entry_contains(configured, _HARNESS_CLASS):
            return configured, None
        errors.append(
            "Configured harness_build does not contain "
            f"{'/'.join(_HARNESS_CLASS)}: {configured}"
        )

    for candidate in (
        root / "build",
        root / "build" / "harness",
        root / "tools" / "harness" / "build",
        root / ".build" / "harness",
    ):
        if _entry_contains(str(candidate), _HARNESS_CLASS):
            return str(candidate), None

    hint = "Mindustry harness is not built. Run: python tools/build_harness.py"
    errors.append(hint)
    return None, "; ".join(errors)


def _valid_assets_dir(value: str) -> Optional[str]:
    path = Path(value)
    if path.is_file() and path.name.lower() == "logicids.dat":
        path = path.parent
    data_file = path / "logicids.dat"
    if data_file.is_file() and data_file.stat().st_size > 0:
        return str(path)
    return None


def _core_checkout_root(core_path: Optional[str]) -> Optional[Path]:
    """Return the checkout owning a compiled core path, if it has a core dir."""
    if not core_path:
        return None
    parts = Path(core_path).parts
    for index, part in enumerate(parts):
        if part.lower() != "core":
            continue
        candidate = Path(*parts[:index])
        if (candidate / "core").is_dir():
            return candidate
    return None


def _assets_candidates_from_core(core_path: Optional[str]) -> List[Path]:
    if not core_path:
        return []
    path = Path(core_path)
    start = path if path.is_dir() else path.parent
    candidates: List[Path] = []
    for ancestor in (start, *start.parents):
        candidates.append(ancestor / "assets")
        candidates.append(ancestor / "core" / "assets")

    checkout = _core_checkout_root(core_path)
    if checkout is not None:
        candidates.append(checkout / "core" / "assets")
        candidates.append(checkout / "assets")
    return _unique_paths(candidates)


def find_assets(
    core_path: Optional[str] = None,
    repo_root: Optional[Path] = None,
    config: Optional[Dict[str, str]] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Find the Mindustry core assets directory containing ``logicids.dat``."""
    root = Path(repo_root or _REPO_ROOT)
    config = config or {}
    errors: List[str] = []

    explicit = os.environ.get("MINDUSTRY_ASSETS_PATH")
    if explicit:
        expanded = _expand_path(explicit)
        valid = _valid_assets_dir(expanded)
        if valid:
            return valid, None
        errors.append(
            "MINDUSTRY_ASSETS_PATH does not contain a non-empty logicids.dat: "
            f"{expanded}"
        )

    configured = config.get("assets_path")
    if configured:
        valid = _valid_assets_dir(configured)
        if valid:
            return valid, None
        errors.append(
            "Configured assets_path does not contain a non-empty logicids.dat: "
            f"{configured}"
        )

    for candidate in _assets_candidates_from_core(core_path):
        valid = _valid_assets_dir(str(candidate))
        if valid:
            return valid, None

    hint = (
        "Mindustry logicids.dat not found. Set MINDUSTRY_ASSETS_PATH to the "
        "directory containing logicids.dat (usually <Mindustry>/core/assets)."
    )

    # Do not mix assets from a different checkout when the compiled core
    # belongs to a specific checkout.  A mismatched logicids.dat silently
    # corrupts lookup indices.
    if _core_checkout_root(core_path) is not None:
        errors.append(hint)
        return None, "; ".join(errors)

    for checkout in _candidate_checkout_roots(root, "Mindustry"):
        for candidate in (checkout / "core" / "assets", checkout / "assets"):
            valid = _valid_assets_dir(str(candidate))
            if valid:
                return valid, None

    errors.append(hint)
    return None, "; ".join(errors)


def discover(repo_root: Optional[Path] = None) -> MindustryDiscovery:
    """Run the complete validated discovery process."""
    root = Path(repo_root or _REPO_ROOT)
    config, config_error = load_config(root)

    core_path, core_error = find_mindustry_core(root, config)
    arc_entries, arc_error = find_arc_entries(root, config)
    harness_build, harness_error = find_harness_build(root, config)
    assets_path, assets_error = find_assets(core_path, root, config)

    errors = [
        error
        for error in (core_error, arc_error, harness_error, assets_error, config_error)
        if error
    ]
    return MindustryDiscovery(
        core_path=core_path,
        arc_entries=arc_entries,
        harness_build=harness_build,
        assets_path=assets_path,
        error="; ".join(errors) if errors else None,
    )
