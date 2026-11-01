"""Error definitions and source location tracking for Python-to-mlog compiler."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SourceLocation:
    filename: str = "<stdin>"
    line: int = 1
    col: int = 1
    end_line: Optional[int] = None
    end_col: Optional[int] = None

    def __str__(self) -> str:
        return f"{self.filename}:{self.line}:{self.col}"


class CompileError(Exception):
    """Exception raised for compilation errors with exact source location."""

    def __init__(self, message: str, loc: Optional[SourceLocation] = None):
        self.message = message
        self.loc = loc or SourceLocation()
        super().__init__(f"{self.loc}: {self.message}")
