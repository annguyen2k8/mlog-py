"""Two-pass label resolution and vanilla mlog emitter.

Pass 1: Computes instruction offsets and records label positions.
Pass 2: Resolves label references in jumps to numeric instruction indices.
"""

from typing import Dict, List, Tuple

from .errors import CompileError
from .ir import IRJump, IRLabel, IRNode, IRSet


# Mindustry processor limits (from Mindustry source specifications)
MAX_INSTRUCTIONS = 1000
MAX_JUMPS = 500


class Emitter:
    """Emits vanilla mlog from IR with 2-pass label resolution."""

    def __init__(self, ir_instructions: List[IRNode]):
        self.ir_instructions = ir_instructions
        self.label_table: Dict[str, int] = {}
        self.emitted_lines: List[str] = []

    def pass1_build_labels(self) -> Dict[str, int]:
        """Pass 1: Build the label table and verify no duplicate labels."""
        self.label_table.clear()
        address = 0
        for instr in self.ir_instructions:
            if isinstance(instr, IRLabel):
                if instr.name in self.label_table:
                    raise CompileError(
                        f"Duplicate label: '{instr.name}'", instr.loc
                    )
                self.label_table[instr.name] = address
            else:
                address += 1
        return self.label_table

    def pass2_emit(self) -> List[str]:
        """Pass 2: Resolve labels and emit canonical vanilla mlog lines."""
        self.emitted_lines.clear()
        jump_count = 0
        for instr in self.ir_instructions:
            if isinstance(instr, IRLabel):
                # Labels are not emitted in vanilla mlog
                continue
            elif isinstance(instr, IRJump):
                jump_count += 1
                if instr.target in self.label_table:
                    numeric_address = self.label_table[instr.target]
                elif instr.target.isdigit() or (
                    instr.target.startswith("-") and instr.target[1:].isdigit()
                ):
                    numeric_address = int(instr.target)
                else:
                    raise CompileError(
                        f"Undefined jump label: '{instr.target}'", instr.loc
                    )
                self.emitted_lines.append(instr.emit_with_address(numeric_address))

            elif isinstance(instr, IRSet):
                from_val = instr.from_
                if from_val in self.label_table:
                    from_val = str(self.label_table[from_val])
                self.emitted_lines.append(f"set {instr.to} {from_val}")

            else:
                self.emitted_lines.append(instr.emit_vanilla())

        # Enforce Mindustry processor limits
        if len(self.emitted_lines) > MAX_INSTRUCTIONS:
            raise CompileError(
                f"generated program contains {len(self.emitted_lines)} instructions; Mindustry limit is {MAX_INSTRUCTIONS}"
            )
        if jump_count > MAX_JUMPS:
            raise CompileError(
                f"generated program contains {jump_count} jump instructions; Mindustry limit is {MAX_JUMPS}"
            )

        return self.emitted_lines


    def emit(self) -> Tuple[str, Dict[str, int]]:
        """Run both passes and return (mlog_text, label_table)."""
        self.pass1_build_labels()
        lines = self.pass2_emit()
        mlog_text = "\n".join(lines)
        if mlog_text:
            mlog_text += "\n"
        return mlog_text, self.label_table
