"""Mlog Lexical Tokenizer and Instruction Parser.

Parses canonical Mindustry Logic (mlog) source text into a strongly-typed sequence
of MlogInstruction objects, enforcing processor limits and grammar rules.
"""

from typing import List, Optional, Tuple

from ..errors import SourceLocation
from ..validator import (
    MAX_INSTRUCTIONS,
    MAX_JUMPS,
    MAX_LINE_TOKENS,
    OPCODE_ARG_COUNTS,
    VALID_CONDITION_OPS,
)
from .errors import MlogParseError
from .instruction import MlogInstruction


def tokenize_mlog_line_with_loc(
    line: str, line_no: int, filename: str = "<stdin>"
) -> List[Tuple[str, int]]:
    """Tokenize a single mlog line honoring string literals with escape sequences.

    Returns a list of (token_string, col_offset) tuples (1-indexed col).
    Raises MlogParseError on unterminated strings.
    """
    tokens: List[Tuple[str, int]] = []
    i = 0
    n = len(line)

    while i < n:
        # Skip whitespace
        while i < n and line[i] in (" ", "\t"):
            i += 1
        if i >= n:
            break

        # Comments
        if line[i] == "#":
            break

        start_col = i + 1

        # String literal
        if line[i] == '"':
            start = i
            i += 1
            closed = False
            while i < n:
                if line[i] == "\\":
                    i += 2  # skip escaped character
                    continue
                if line[i] == '"':
                    i += 1
                    closed = True
                    break
                i += 1
            if not closed:
                loc = SourceLocation(filename=filename, line=line_no, col=start_col)
                raise MlogParseError("Unterminated string literal", loc)
            tokens.append((line[start:i], start_col))
        else:
            start = i
            while i < n and line[i] not in (" ", "\t", "#", ";"):
                i += 1
            tokens.append((line[start:i], start_col))

    return tokens


class MlogParser:
    """Parser for canonical Mindustry Logic assembly text."""

    def __init__(self, filename: str = "<stdin>"):
        self.filename = filename

    def parse(self, text: str) -> List[MlogInstruction]:
        """Parse mlog text into a sequence of MlogInstruction objects.

        Raises MlogParseError on invalid opcodes, incorrect argument counts,
        out-of-bound jumps, or processor limit violations.
        """
        # Normalize CRLF / CR line endings
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = normalized.split("\n")

        instructions: List[MlogInstruction] = []
        jump_count = 0

        for line_no, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            token_entries = tokenize_mlog_line_with_loc(line, line_no, self.filename)
            if not token_entries:
                continue

            # Token count limit per line
            if len(token_entries) > MAX_LINE_TOKENS:
                loc = SourceLocation(
                    filename=self.filename,
                    line=line_no,
                    col=token_entries[MAX_LINE_TOKENS][1] if len(token_entries) > MAX_LINE_TOKENS else 1,
                )
                raise MlogParseError(
                    f"Line exceeds maximum {MAX_LINE_TOKENS} tokens (found {len(token_entries)})",
                    loc,
                )

            tokens = [t[0] for t in token_entries]
            first_col = token_entries[0][1]
            opcode = tokens[0]
            args = tokens[1:]

            loc = SourceLocation(filename=self.filename, line=line_no, col=first_col)

            # Opcode validation
            if opcode not in OPCODE_ARG_COUNTS:
                raise MlogParseError(f"Unknown mlog opcode: '{opcode}'", loc)

            # Argument count validation
            expected_args = OPCODE_ARG_COUNTS[opcode]
            if len(args) != expected_args:
                raise MlogParseError(
                    f"Opcode '{opcode}' expects {expected_args} argument(s), got {len(args)}",
                    loc,
                )

            # Opcode-specific semantic checks
            if opcode == "jump":
                jump_count += 1
                target_str = args[0]
                try:
                    target_int = int(target_str)
                except ValueError:
                    raise MlogParseError(
                        f"Jump destination must be a numeric address, got '{target_str}'",
                        loc,
                    )
                if target_int < 0:
                    raise MlogParseError(
                        f"Jump destination cannot be negative: {target_int}",
                        loc,
                    )

                cond = args[1]
                if cond not in VALID_CONDITION_OPS:
                    raise MlogParseError(
                        f"Invalid jump condition: '{cond}'. Allowed: {', '.join(sorted(VALID_CONDITION_OPS))}",
                        loc,
                    )

            address = len(instructions)
            instr = MlogInstruction(
                address=address,
                opcode=opcode,
                args=tuple(args),
                loc=loc,
                raw_text=line,
            )
            instructions.append(instr)

            # Processor limits
            if len(instructions) > MAX_INSTRUCTIONS:
                raise MlogParseError(
                    f"Program exceeds maximum {MAX_INSTRUCTIONS} instructions",
                    loc,
                )
            if jump_count > MAX_JUMPS:
                raise MlogParseError(
                    f"Program exceeds maximum {MAX_JUMPS} jumps",
                    loc,
                )

        # Pass 2: Verify jump target addresses against program boundaries
        total_instructions = len(instructions)
        for instr in instructions:
            if instr.is_jump:
                target = instr.jump_target
                assert target is not None
                # Jumps can target 0 .. total_instructions (targeting total_instructions exits/yields)
                if target > total_instructions:
                    raise MlogParseError(
                        f"Jump at address {instr.address} targets out-of-bounds address {target} "
                        f"(program has {total_instructions} instructions)",
                        instr.loc,
                    )

        return instructions


def parse_mlog(text: str, filename: str = "<stdin>") -> List[MlogInstruction]:
    """Convenience function to parse mlog text into MlogInstruction list."""
    return MlogParser(filename=filename).parse(text)
