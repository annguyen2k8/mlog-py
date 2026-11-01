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

class _CompatLoader:
    """Wrapper around module loader to allow execution under legacy 'src.*' names."""

    def __init__(self, target_loader):
        self._target_loader = target_loader

    def get_code(self, fullname=None):
        return self._target_loader.get_code(None)

    def exec_module(self, module):
        return self._target_loader.exec_module(module)

    def __getattr__(self, name):
        return getattr(self._target_loader, name)


for _mod in _SUBMODULES:
    try:
        _loaded = importlib.import_module(f"mlog.{_mod}")
        if hasattr(_loaded, "__spec__") and _loaded.__spec__ and _loaded.__spec__.loader:
            if not isinstance(_loaded.__spec__.loader, _CompatLoader):
                _loaded.__spec__.loader = _CompatLoader(_loaded.__spec__.loader)
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

