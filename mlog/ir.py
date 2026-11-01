"""Intermediate Representation (IR) for Mindustry Logic (mlog).

IR instructions are independent of Python AST and maintain source location metadata.
Labels are symbolic; jump destinations in IR refer to label names.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from .errors import SourceLocation


@dataclass
class IRNode:
    """Base class for all IR instructions."""
    loc: Optional[SourceLocation] = None

    def emit_vanilla(self) -> str:
        """Emit vanilla mlog instruction text (labels are not emitted)."""
        raise NotImplementedError


@dataclass
class IRLabel(IRNode):
    """Symbolic label for jump targets. Not emitted as a mlog instruction."""
    name: str = ""

    def __str__(self) -> str:
        return f"{self.name}:"


@dataclass
class IRSet(IRNode):
    """Assignment instruction: set <to> <from_>"""
    to: str = ""
    from_: str = ""

    def emit_vanilla(self) -> str:
        return f"set {self.to} {self.from_}"

    def __str__(self) -> str:
        return self.emit_vanilla()


@dataclass
class IROp(IRNode):
    """Arithmetic/logical operation: op <op> <dest> <a> <b>"""
    op: str = ""
    dest: str = ""
    a: str = ""
    b: str = "0"

    def emit_vanilla(self) -> str:
        return f"op {self.op} {self.dest} {self.a} {self.b}"

    def __str__(self) -> str:
        return self.emit_vanilla()


@dataclass
class IRJump(IRNode):
    """Conditional/unconditional jump instruction: jump <target> <cond> <a> <b>"""
    target: str = ""
    cond: str = "always"
    a: str = "0"
    b: str = "0"

    def emit_with_address(self, address: int) -> str:
        return f"jump {address} {self.cond} {self.a} {self.b}"

    def __str__(self) -> str:
        return f"jump {self.target} {self.cond} {self.a} {self.b}"


@dataclass
class IRRaw(IRNode):
    """Generic raw instruction: <opcode> <arg1> <arg2> ..."""
    opcode: str = ""
    args: List[str] = field(default_factory=list)

    def emit_vanilla(self) -> str:
        if self.args:
            return f"{self.opcode} {' '.join(self.args)}"
        return self.opcode

    def __str__(self) -> str:
        return self.emit_vanilla()
