"""Backward-compatibility shim package.

Deprecated: Import directly from `mlog` package instead of `src`.
All attributes and submodules are forwarded to `mlog`.
"""

import sys
import importlib

import mlog

# Re-export submodules
_SUBMODULES = (
    "allocator",
    "beta",
    "clipboard",
    "comments",
    "compiler",
    "constants",
    "emitter",
    "errors",
    "extract_registry",
    "ir",
    "metadata",
    "mindustry_discovery",
    "mindustry_validator",
    "mlog_registry",
    "mlog_registry_data",
    "optimizer",
    "parser",
    "validator",
    "decompiler",
)

for _mod in _SUBMODULES:
    try:
        _loaded = importlib.import_module(f"mlog.{_mod}")
        sys.modules[f"src.{_mod}"] = _loaded
        globals()[_mod] = _loaded
    except ImportError:
        pass

# Also forward all decompiler submodules so exception classes and types match identity
_DECOMP_SUBMODULES = (
    "cfg",
    "dataflow",
    "dsl_symbols",
    "errors",
    "expression",
    "function_analyzer",
    "function_ir",
    "instruction",
    "naming",
    "parser",
    "semantics",
    "sourcemap",
    "structured_ir",
    "structurer",
)

for _sub in _DECOMP_SUBMODULES:
    try:
        _loaded = importlib.import_module(f"mlog.decompiler.{_sub}")
        sys.modules[f"src.decompiler.{_sub}"] = _loaded
    except ImportError:
        pass

sys.modules["src.mlog"] = mlog

__version__ = mlog.__version__

