"""Comment-to-Print processing for Mindustry Logic Python DSL.

Provides opt-in transformation of Python comments into Mindustry 'print' instructions.
Supports:
  - Opt-in via compiler argument 'comments_to_print=True' or source pragma '# mlog: comments-to-print'.
  - Multi-line comment grouping (consecutive comment lines with same indent joined with newline).
  - Proper escaping of quotes, backslashes, newlines, and special characters.
  - Mindustry processor textBuffer capacity limit (400 characters) chunking.
  - Semicolon-separated statements for inline comments to preserve line numbering.
  - Preserves standard Python comment semantics when feature is disabled.
"""

import io
import re
import tokenize
from typing import List, Tuple


# Mindustry processor maxTextBuffer is strictly 400 characters
MAX_MINDUSTRY_TEXT_BUFFER: int = 400

PRAGMA_COMMENTS_TO_PRINT = re.compile(
    r"^[ \t]*#[ \t]*mlog[ \t]*:[ \t]*comments?[-_]to[-_]print\b",
    re.IGNORECASE,
)


def has_comments_to_print_pragma(source: str) -> bool:
    """Check if the source contains the '# mlog: comments-to-print' pragma."""
    return bool(PRAGMA_COMMENTS_TO_PRINT.search(source))


def _clean_comment_text(raw_comment: str) -> str:
    """Extract clean comment text from a raw comment string starting with '#'."""
    text = raw_comment.lstrip("#")
    if text.startswith(" "):
        text = text[1:]
    return text.rstrip("\r\n")


def _chunk_text(text: str, max_len: int = MAX_MINDUSTRY_TEXT_BUFFER) -> List[str]:
    """Chunk text into slices of at most max_len characters."""
    if not text:
        return [""]
    if len(text) <= max_len:
        return [text]
    return [text[i : i + max_len] for i in range(0, len(text), max_len)]


def transform_comments_to_print(
    source: str,
    comments_to_print: bool = False,
) -> Tuple[str, bool]:
    """Transform Python comments into 'print(...)' statements when opt-in is enabled.

    Returns:
        (transformed_source, is_active)
    """
    has_pragma = has_comments_to_print_pragma(source)
    is_active = comments_to_print or has_pragma

    if not is_active:
        return source, False

    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except Exception:
        # If tokenization fails, fallback to raw source
        return source, is_active

    # Map line number to list of comment tokens on that line: (start_col, end_col, comment_str)
    comments_by_line = {}
    for tok in tokens:
        if tok.type == tokenize.COMMENT:
            comments_by_line.setdefault(tok.start[0], []).append(
                (tok.start[1], tok.end[1], tok.string)
            )

    lines = source.splitlines(keepends=True)
    out_lines: List[str] = []

    i = 0
    while i < len(lines):
        line_num = i + 1
        line = lines[i]

        if line_num not in comments_by_line:
            out_lines.append(line)
            i += 1
            continue

        line_comments = comments_by_line[line_num]
        c_start, c_end, c_str = line_comments[0]
        prefix = line[:c_start]

        if prefix.strip() == "":
            # Standalone comment line (only whitespace precedes '#')
            if PRAGMA_COMMENTS_TO_PRINT.match(line):
                # Erase pragma comment line, keep empty line to preserve line numbers
                out_lines.append("\n")
                i += 1
                continue

            # Skip shebang and encoding cookies
            if line.startswith("#!") or "coding:" in line or "coding=" in line:
                out_lines.append(line)
                i += 1
                continue

            indent = prefix
            # Group contiguous standalone comments with the same indentation
            block_comments: List[str] = []
            cur_idx = i
            while cur_idx < len(lines):
                c_lineno = cur_idx + 1
                if c_lineno not in comments_by_line:
                    break
                c_list = comments_by_line[c_lineno]
                c_s, c_e, c_text = c_list[0]
                c_pfx = lines[cur_idx][:c_s]
                if c_pfx != indent:
                    break
                if PRAGMA_COMMENTS_TO_PRINT.match(lines[cur_idx]):
                    break
                block_comments.append(_clean_comment_text(c_text))
                cur_idx += 1

            combined_text = "\n".join(block_comments)
            chunks = _chunk_text(combined_text)

            for chunk in chunks:
                out_lines.append(f"{indent}print({repr(chunk)})\n")

            # Pad with empty lines to strictly preserve line count
            lines_consumed = len(block_comments)
            lines_emitted = len(chunks)
            if lines_consumed > lines_emitted:
                for _ in range(lines_consumed - lines_emitted):
                    out_lines.append("\n")

            i = cur_idx
        else:
            # Inline comment (code precedes '#' on this line)
            code_prefix = line[:c_start].rstrip()
            raw_text = _clean_comment_text(c_str)
            chunks = _chunk_text(raw_text)

            indent_match = re.match(r"^[ \t]*", line)
            indent = indent_match.group(0) if indent_match else ""

            # If compound statement (e.g. 'if cond:', 'while cond:', 'def foo():')
            if code_prefix.endswith(":"):
                for chunk in chunks:
                    out_lines.append(f"{indent}print({repr(chunk)})\n")
                out_lines.append(code_prefix + "\n")
            else:
                # Simple statement: place print first via semicolon to preserve line number
                # and ensure statement is also executed
                unindented_code = code_prefix[len(indent) :]
                print_stmts = "; ".join(f"print({repr(c)})" for c in chunks)
                out_lines.append(f"{indent}{print_stmts}; {unindented_code}\n")

            i += 1

    return "".join(out_lines), is_active
