"""Instruction Intermediate Representation (IR) for Mindustry Logic decompiler."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from ..errors import SourceLocation


class JumpType(Enum):
    """Classification of jump instructions."""
    CONDITIONAL = "conditional"
    UNCONDITIONAL = "unconditional"


@dataclass(frozen=True)
class MlogInstruction:
    """Represents a single parsed vanilla Mindustry Logic instruction."""
    address: int
    opcode: str
    args: Tuple[str, ...]
    loc: SourceLocation
    raw_text: str = ""

    @property
    def is_jump(self) -> bool:
        """True if instruction is a jump."""
        return self.opcode == "jump"

    @property
    def jump_target(self) -> Optional[int]:
        """Destination address if this is a jump instruction, else None."""
        if not self.is_jump or not self.args:
            return None
        try:
            return int(self.args[0])
        except ValueError:
            return None

    @property
    def jump_condition(self) -> Optional[str]:
        """Condition operation if this is a jump, else None."""
        if not self.is_jump or len(self.args) < 2:
            return None
        return self.args[1]

    @property
    def jump_operands(self) -> Optional[Tuple[str, str]]:
        """Operands (a, b) for comparison if this is a jump, else None."""
        if not self.is_jump or len(self.args) < 4:
            return None
        return (self.args[2], self.args[3])

    @property
    def is_unconditional_jump(self) -> bool:
        """True if jump always branches unconditionally."""
        if not self.is_jump or len(self.args) < 2:
            return False
        cond = self.args[1]
        if cond == "always":
            return True
        # Comparison with identical constant/variable operands (e.g. 0 equal 0)
        if cond in ("equal", "strictEqual") and len(self.args) >= 4:
            a, b = self.args[2], self.args[3]
            if a == b:
                return True
        return False

    @property
    def is_conditional_jump(self) -> bool:
        """True if jump branches conditionally based on operand comparison."""
        return self.is_jump and not self.is_unconditional_jump

    @property
    def jump_type(self) -> Optional[JumpType]:
        """JumpType enum if this is a jump, else None."""
        if not self.is_jump:
            return None
        return JumpType.UNCONDITIONAL if self.is_unconditional_jump else JumpType.CONDITIONAL

    @property
    def is_forward_jump(self) -> bool:
        """True if jump targets a strictly higher instruction address."""
        target = self.jump_target
        return target is not None and target > self.address

    @property
    def is_backward_jump(self) -> bool:
        """True if jump targets an address less than or equal to current address (e.g. loops)."""
        target = self.jump_target
        return target is not None and target <= self.address

    @property
    def is_self_jump(self) -> bool:
        """True if jump targets its own address (infinite loop / pause pattern)."""
        target = self.jump_target
        return target is not None and target == self.address

    @property
    def is_terminal(self) -> bool:
        """True if instruction unconditionally halts or redirects control flow with no fallthrough."""
        if self.opcode in ("stop", "end"):
            return True
        return self.is_unconditional_jump

    @property
    def can_fallthrough(self) -> bool:
        """True if execution can naturally fall through to address + 1."""
        if self.opcode in ("stop", "end"):
            return False
        if self.is_unconditional_jump:
            return False
        return True

    def __str__(self) -> str:
        args_str = " " + " ".join(self.args) if self.args else ""
        return f"[{self.address:3d}]: {self.opcode}{args_str}"
