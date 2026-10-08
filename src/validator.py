"""Lightweight mlog syntax validator based on Mindustry Logic specifications.

Validates that emitted mlog lines conform to vanilla Mindustry processor grammar,
opcode signatures, valid numeric addresses in jumps, and line length limits.
"""

from typing import List, Optional


class ValidationError(Exception):
    """Raised when emitted mlog text fails vanilla syntax validation."""

    def __init__(self, message: str, line_num: int, line: str):
        self.message = message
        self.line_num = line_num
        self.line = line
        super().__init__(f"Line {line_num}: {message} -> '{line}'")


# Expected argument counts for standard vanilla mlog opcodes
OPCODE_ARG_COUNTS = {
    "read": 3,
    "write": 3,
    "draw": 7,
    "drawflush": 1,
    "print": 1,
    "printflush": 1,
    "getlink": 2,
    "control": 6,
    "radar": 7,
    "sensor": 3,
    "set": 2,
    "op": 4,
    "lookup": 3,
    "packcolor": 5,
    "unpackcolor": 5,
    "wait": 1,
    "stop": 0,
    "end": 0,
    "jump": 4,
    "ubind": 1,
    "ucontrol": 6,
    "uradar": 7,
    "ulocate": 8,
}

VALID_CONDITION_OPS = {
    "equal", "notEqual", "lessThan", "lessThanEq",
    "greaterThan", "greaterThanEq", "strictEqual", "always",
}

MAX_INSTRUCTIONS = 1000
MAX_JUMPS = 500
MAX_LINE_TOKENS = 16


def tokenize_mlog_line(line: str) -> List[str]:
    """Tokenize a single mlog line honoring string literals with escape sequences."""
    tokens: List[str] = []
    i = 0
    n = len(line)

    while i < n:
        # Skip leading spaces/tabs
        while i < n and line[i] in (" ", "\t"):
            i += 1
        if i >= n:
            break

        # Comments
        if line[i] == "#":
            break

        # String literal
        if line[i] == '"':
            start = i
            i += 1
            while i < n:
                if line[i] == "\\":
                    i += 2  # skip escape
                    continue
                if line[i] == '"':
                    i += 1
                    break
                i += 1
            tokens.append(line[start:i])
        else:
            start = i
            while i < n and line[i] not in (" ", "\t", "#", ";"):
                i += 1
            tokens.append(line[start:i])

    return tokens


class MlogValidator:
    """Validates mlog source text against Mindustry vanilla logic rules."""

    @classmethod
    def validate(cls, mlog_text: str):
        lines = mlog_text.strip().splitlines()
        if len(lines) > MAX_INSTRUCTIONS:
            raise ValidationError(
                f"Instruction count {len(lines)} exceeds max processor limit {MAX_INSTRUCTIONS}",
                len(lines),
                "",
            )

        jump_count = 0
        for line_idx, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            tokens = tokenize_mlog_line(line)
            if not tokens:
                continue

            if len(tokens) > MAX_LINE_TOKENS:
                raise ValidationError(
                    f"Line contains {len(tokens)} tokens; max allowed is {MAX_LINE_TOKENS}",
                    line_idx,
                    raw_line,
                )

            opcode = tokens[0]
            args = tokens[1:]

            if opcode == "jump":
                jump_count += 1
                if jump_count > MAX_JUMPS:
                    raise ValidationError(
                        f"Jump count {jump_count} exceeds max processor limit {MAX_JUMPS}",
                        line_idx,
                        raw_line,
                    )

            if opcode not in OPCODE_ARG_COUNTS:
                raise ValidationError(
                    f"Unknown or unsupported mlog opcode '{opcode}'",
                    line_idx,
                    raw_line,
                )

            expected_count = OPCODE_ARG_COUNTS[opcode]
            if len(args) != expected_count:
                raise ValidationError(
                    f"Opcode '{opcode}' expects {expected_count} arguments, got {len(args)}",
                    line_idx,
                    raw_line,
                )


            # Specific validation for jump instructions
            if opcode == "jump":
                dest_str, cond = args[0], args[1]
                # Destination must be a non-negative integer
                try:
                    dest = int(dest_str)
                    if dest < 0:
                        raise ValueError
                except ValueError:
                    raise ValidationError(
                        f"Jump address must be a non-negative integer, got '{dest_str}'",
                        line_idx,
                        raw_line,
                    )
                if cond not in VALID_CONDITION_OPS:
                    raise ValidationError(
                        f"Invalid jump condition '{cond}'. Expected one of {sorted(VALID_CONDITION_OPS)}",
                        line_idx,
                        raw_line,
                    )
