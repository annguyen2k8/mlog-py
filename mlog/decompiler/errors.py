"""Exceptions for the Mindustry Logic (mlog) Decompiler."""

from typing import Optional
from ..errors import SourceLocation


class DecompileError(Exception):
    """Base exception for all decompiler errors."""

    def __init__(self, message: str, loc: Optional[SourceLocation] = None):
        self.message = message
        self.loc = loc
        loc_str = f"{loc.filename}:{loc.line}:{loc.col}: " if loc else ""
        super().__init__(f"{loc_str}{message}")


class MlogParseError(DecompileError):
    """Raised when mlog text fails lexical or grammar parsing."""
    pass


class CFGError(DecompileError):
    """Raised when Control Flow Graph reconstruction encounters invalid control flow."""
    pass
