"""Main API and CLI interface for Python-to-mlog compiler."""

import argparse
import builtins
import os
import sys
from dataclasses import dataclass
from enum import IntEnum
from typing import Callable, Dict, List, Optional

_cli_print = builtins.print

from .compiler import Compiler
from .emitter import Emitter
from .errors import CompileError
from .ir import IRNode
from .mlog_registry import (
    Align,
    Condition,
    ControlProperty,
    DrawType,
    Items,
    Liquids,
    LogicOp,
    LookupType,
    RadarSort,
    RadarTarget,
    SensorProperty,
    Teams,
    UnitControl,
    Units,
    TileLayer,
    QueryShape,
    QueryType,
    StatusEffects,
    FetchType,
    LogicRules,
    Weathers,
    Fx,
    MessageType,
    CutsceneAction,
    MarkerType,
    MarkerControl,
    Vars,
    BuiltinVarToken,
)
from .metadata import (
    Array,
    ColorChannels,
    LocateResult,
    MLOG_EXPORTS,
    OreLocateResult,
    _ControlCallable,
    _CutsceneCallable,
    _DrawCallable,
    _OpCallable,
    _UnitControlCallable,
    _UnitLocateCallable,
    _SoundCallable,
    _MusicCallable,
    _MarkerCallable,
    sound,
    music,
    marker,
    _rt_bullet as bullet,
    _rt_clientdata as clientdata,
    _rt_control as control,
    _rt_cutscene as cutscene,
    _rt_draw as draw,
    _rt_drawflush as drawflush,
    _rt_effect as effect,
    _rt_end as end,
    _rt_explosion as explosion,
    _rt_fetch as fetch,
    _rt_format as format,
    _rt_getblock as getblock,
    _rt_getflag as getflag,
    _rt_getlink as getlink,
    _rt_jump as jump,
    _rt_localeprint as localeprint,
    _rt_lookup as lookup,
    _rt_makemarker as makemarker,
    _rt_max as max,
    _rt_message as message,
    _rt_min as min,
    _rt_noop as noop,
    _rt_op as op,
    _rt_packcolor as packcolor,
    _rt_playmusic as playmusic,
    _rt_playsound as playsound,
    _rt_print as print,
    _rt_printchar as printchar,
    _rt_printflush as printflush,
    _rt_query as query,
    _rt_radar as radar,
    _rt_raw as raw,
    _rt_read as read,
    _rt_select as select,
    _rt_sensor as sensor,
    _rt_set as set,
    _rt_setblock as setblock,
    _rt_setflag as setflag,
    _rt_setmarker as setmarker,
    _rt_setprop as setprop,
    _rt_setrate as setrate,
    _rt_setrule as setrule,
    _rt_spawn as spawn,
    _rt_spawnwave as spawnwave,
    _rt_status as status,
    _rt_stop as stop,
    _rt_sync as sync,
    _rt_ubind as ubind,
    _rt_ucontrol as ucontrol,
    _rt_ulocate as ulocate,
    _rt_unpackcolor as unpackcolor,
    _rt_uradar as uradar,
    _rt_wait as wait,
    _rt_weathersense as weathersense,
    _rt_weatherset as weatherset,
    _rt_write as write,
)
from .optimizer import PassThroughOptimizer
from .parser import parse_and_validate
from .validator import MlogValidator, ValidationError
from .comments import transform_comments_to_print

# Null constant representing null in Mindustry Logic

null = None


def _get_version() -> str:
    """Resolve package version from pyproject.toml or packaging metadata."""
    try:
        pyproject_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pyproject.toml"))
        if os.path.exists(pyproject_path):
            with open(pyproject_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("version ="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass

    try:
        from importlib.metadata import version, PackageNotFoundError
        try:
            return version("mlog-py")
        except PackageNotFoundError:
            pass
    except ImportError:
        pass

    return "0.6.0"


__version__: str = _get_version()

__all__ = sorted(list(MLOG_EXPORTS))



@dataclass
class CompileResult:
    """Result of compilation containing final mlog text, IR, and label table."""
    mlog: str
    ir: List[IRNode]
    label_table: Dict[str, int]


def compile_py(
    source: str,
    filename: str = "<stdin>",
    optimize: bool = False,
    validate: bool = True,
    allow_functions: bool = False,
    fold_constants: bool = True,
    comments_to_print: bool = False,
) -> CompileResult:
    """Compile Python subset source code into canonical vanilla mlog.

    Args:
        source: Python code string.
        filename: Source file name for error reporting.
        optimize: Enable optimization passes (PassThrough in Phase 1).
        validate: Validate emitted mlog against Mindustry syntax rules.
        allow_functions: Allow user-defined function definitions and calls.
        fold_constants: Enable compile-time constant folding (default: True).
        comments_to_print: Convert Python comments into Mindustry 'print' instructions.

    Returns:
        CompileResult containing the emitted mlog, IR instructions, and label table.
    """
    # 0. Optional comments-to-print preprocessing
    processed_source, is_comments_to_print = transform_comments_to_print(
        source, comments_to_print=comments_to_print
    )

    # 1. Parse & validate Python AST subset
    tree = parse_and_validate(processed_source, filename, allow_functions=allow_functions)

    # 2. Lower AST to IR
    compiler = Compiler(
        filename,
        allow_functions=allow_functions,
        fold_constants=fold_constants,
        comments_to_print=is_comments_to_print,
    )
    ir = compiler.compile(tree)

    # 3. Optimize (Phase 1: PassThrough)
    optimizer = PassThroughOptimizer()
    ir = optimizer.optimize(ir)

    # 4. Two-pass emit & label resolution
    emitter = Emitter(ir)
    mlog_text, label_table = emitter.emit()

    # 5. Validate emitted mlog text
    if validate and mlog_text.strip():
        MlogValidator.validate(mlog_text)

    return CompileResult(mlog=mlog_text, ir=ir, label_table=label_table)


def _cli_compile(args: argparse.Namespace) -> int:
    """Handle compile subcommand: Python DSL -> MLog."""
    try:
        with open(args.input_file, "r", encoding="utf-8") as f:
            source = f.read()
    except OSError as e:
        _cli_print(f"Error reading file '{args.input_file}': {e}", file=sys.stderr)
        return 1

    try:
        result = compile_py(
            source=source,
            filename=args.input_file,
            validate=not args.no_validate,
            allow_functions=not args.no_functions,
            fold_constants=not getattr(args, "no_fold_constants", False),
            comments_to_print=getattr(args, "comments_to_print", False),
        )

    except (CompileError, ValidationError) as e:
        _cli_print(f"Compilation error: {e}", file=sys.stderr)
        return 1

    if args.mindustry:
        from .mindustry_validator import is_mindustry_available, validate_with_mindustry
        if not is_mindustry_available():
            _cli_print("Error: Mindustry engine or Java not available for validation", file=sys.stderr)
            return 1
        ok, msg, count = validate_with_mindustry(result.mlog)
        if not ok:
            _cli_print(f"Mindustry engine validation error: {msg}", file=sys.stderr)
            return 1

    if args.debug:
        _cli_print("=== IR INSTRUCTIONS (IR index) ===")
        for i, instr in enumerate(result.ir):
            loc_str = f" [{instr.loc.line}:{instr.loc.col}]" if instr.loc else ""
            _cli_print(f"  IR[{i:3d}]: {instr}{loc_str}")
        _cli_print("\n=== LABEL TABLE (Resolved instruction address) ===")
        for name, addr in sorted(result.label_table.items()):
            _cli_print(f"  {name} -> mlog[{addr}]")
        _cli_print("\n=== FINAL MLOG (Instruction address) ===")
        for idx, line in enumerate(result.mlog.splitlines()):
            _cli_print(f"  [{idx:3d}]: {line}")
        _cli_print()

    if args.output_file:
        try:
            with open(args.output_file, "w", encoding="utf-8") as f:
                f.write(result.mlog)
        except OSError as e:
            _cli_print(f"Error writing output file '{args.output_file}': {e}", file=sys.stderr)
            return 1
    elif not args.debug:
        try:
            sys.stdout.write(result.mlog)
            sys.stdout.flush()
        except BrokenPipeError:
            pass

    # Auto-copy clipboard: enabled by default, disabled if --no-clipboard is set or MLOG_NO_CLIPBOARD=1
    # CLI flag (--clipboard / --no-clipboard) takes precedence over MLOG_NO_CLIPBOARD env var
    if getattr(args, "copy_clipboard", None) is not None:
        should_copy = args.copy_clipboard
    elif os.environ.get("MLOG_NO_CLIPBOARD", "").lower() in ("1", "true", "yes"):
        should_copy = False
    else:
        should_copy = True

    if should_copy:
        from .clipboard import copy_to_clipboard
        ok, msg = copy_to_clipboard(result.mlog)
        try:
            if ok:
                _cli_print(f"[mlog-py] {msg}", file=sys.stderr)
            else:
                _cli_print(f"[mlog-py] Notice: Could not copy to clipboard.\n{msg}", file=sys.stderr)
        except BrokenPipeError:
            pass

    return 0


_interactive_prompt_hook: Optional[Callable[[str], str]] = None


def _read_interactive_line(prompt: str) -> str:
    """Prompt user interactively for a single line on stderr, handling TTY and test hooks."""
    _cli_print(prompt, file=sys.stderr, end="", flush=True)

    # 1. Testing hook takes priority if configured
    global _interactive_prompt_hook
    if _interactive_prompt_hook is not None:
        return _interactive_prompt_hook(prompt)

    # 2. If sys.stdin is not the real system stdin (e.g. redirected or mocked in test without hook)
    if sys.stdin is not getattr(sys, "__stdin__", sys.stdin):
        return ""

    # 3. Real interactive terminal: read from controlling terminal device
    try:
        tty_path = "CONIN$" if sys.platform == "win32" else "/dev/tty"
        with open(tty_path, "r", encoding="utf-8", errors="replace") as tty_in:
            line = tty_in.readline()
            return line.strip() if line else ""
    except (KeyboardInterrupt, EOFError):
        raise
    except Exception:
        # Fallback to sys.stdin if terminal device cannot be opened
        try:
            line = sys.stdin.readline()
            return line.strip() if line else ""
        except Exception:
            return ""


def _cli_decompile(args: argparse.Namespace) -> int:
    """Handle decompile subcommand: MLog -> Python DSL."""
    from .decompiler import decompile
    from .decompiler.errors import DecompileError

    input_source = args.input_file
    is_stdin = (input_source is None or input_source == "-")

    if is_stdin:
        filename = "<stdin>"
        is_tty = hasattr(sys.stdin, "isatty") and sys.stdin.isatty()
        if is_tty:
            eof_key = "Ctrl+Z (Enter)" if sys.platform == "win32" else "Ctrl+D"
            _cli_print(
                "[mlog-py] Paste or enter mlog code below.\n"
                f"[mlog-py] Finish input with EOF ({eof_key}) or type 'EOF' on an empty line:",
                file=sys.stderr,
            )
            lines: List[str] = []
            try:
                while True:
                    line = sys.stdin.readline()
                    if not line:  # Stream EOF
                        break
                    stripped = line.rstrip("\r\n")
                    if stripped in ("EOF", "__EOF__"):
                        break
                    lines.append(line)
                mlog_source = "".join(lines)
            except KeyboardInterrupt:
                _cli_print("\n[mlog-py] Decompilation aborted by user.", file=sys.stderr)
                return 130
        else:
            try:
                raw_input = sys.stdin.read()
                clean_lines = []
                for line in raw_input.splitlines(True):
                    if line.rstrip("\r\n") in ("EOF", "__EOF__"):
                        break
                    clean_lines.append(line)
                mlog_source = "".join(clean_lines)
            except KeyboardInterrupt:
                _cli_print("\n[mlog-py] Decompilation aborted by user.", file=sys.stderr)
                return 130
    else:
        filename = input_source
        try:
            with open(input_source, "r", encoding="utf-8") as f:
                mlog_source = f.read()
        except OSError as e:
            _cli_print(f"Error reading file '{input_source}': {e}", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            _cli_print("\n[mlog-py] Decompilation aborted by user.", file=sys.stderr)
            return 130

    if not mlog_source.strip():
        _cli_print("Decompilation error: input is empty", file=sys.stderr)
        return 1

    try:
        python_code = decompile(
            mlog_source,
            filename=filename,
            debug=args.debug,
        )
    except DecompileError as e:
        _cli_print(f"Decompilation error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        _cli_print("\n[mlog-py] Decompilation aborted by user.", file=sys.stderr)
        return 130

    output_target = args.output_file

    if not output_target and is_stdin and is_tty:
        try:
            save_path = _read_interactive_line(
                "[mlog-py] Enter output file path (.py) [press Enter to print to stdout]: "
            )
            if save_path:
                output_target = save_path
        except KeyboardInterrupt:
            _cli_print("\n[mlog-py] Decompilation aborted by user.", file=sys.stderr)
            return 130

    if output_target:
        try:
            parent_dir = os.path.dirname(output_target)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
            with open(output_target, "w", encoding="utf-8") as f:
                f.write(python_code)
            if not args.output_file:
                _cli_print(f"[mlog-py] Saved decompiled code to '{output_target}'.", file=sys.stderr)
        except OSError as e:
            _cli_print(f"Error writing output file '{output_target}': {e}", file=sys.stderr)
            return 1
    else:
        try:
            sys.stdout.write(python_code)
            sys.stdout.flush()
        except BrokenPipeError:
            pass

    return 0



def _build_cli_parser() -> argparse.ArgumentParser:
    """Build the argument parser supporting 'compile' and 'decompile' subcommands."""
    parser = argparse.ArgumentParser(
        prog="mlog-py",
        description="Compile a controlled Python subset into Mindustry Logic (mlog) or decompile mlog to Python DSL.",
    )
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(
        dest="command",
        title="subcommands",
        metavar="{compile, decompile}",
        help="Subcommands (compile, decompile)",
    )

    # Subcommand: compile (Python DSL -> MLog)
    compile_p = subparsers.add_parser(
        "compile",
        help="Compile Python DSL -> MLog",
        description="Compile Python DSL into Mindustry Logic (mlog).",
    )
    compile_p.add_argument("input_file", help="Input Python source file (.py)")
    compile_p.add_argument(
        "-o", "--output", dest="output_file", help="Output file path (.mlog)"
    )
    compile_p.add_argument(
        "--debug",
        action="store_true",
        help="Print IR instructions and label table for debugging",
    )
    compile_p.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip mlog syntax validation",
    )
    compile_p.add_argument(
        "--mindustry",
        action="store_true",
        help="Validate generated mlog using Mindustry's actual engine (requires Java)",
    )
    compile_p.add_argument(
        "--no-fold-constants",
        action="store_true",
        help="Disable compile-time constant folding",
    )
    compile_p.add_argument(
        "--no-functions",
        action="store_true",
        help="Reject 'def' function definitions and 'return' statements (disabled by default)",
    )
    compile_p.add_argument(
        "--clipboard",
        dest="copy_clipboard",
        action="store_true",
        default=None,
        help="Copy compiled mlog to system clipboard (enabled by default)",
    )
    compile_p.add_argument(
        "--no-clipboard",
        dest="copy_clipboard",
        action="store_false",
        help="Disable automatic copying of compiled mlog to system clipboard",
    )
    compile_p.add_argument(
        "--comments-to-print",
        dest="comments_to_print",
        action="store_true",
        help="Convert Python comments into Mindustry 'print' instructions",
    )


    # Subcommand: decompile (MLog -> Python DSL)
    decompile_p = subparsers.add_parser(
        "decompile",
        help="Decompile MLog -> Python DSL",
        description="Decompile Mindustry Logic (mlog) into structured Python DSL.",
    )
    decompile_p.add_argument(
        "input_file",
        nargs="?",
        default=None,
        help="Input Mindustry Logic file (.mlog) or '-' / omitted to read from stdin",
    )
    decompile_p.add_argument(
        "-o", "--output", dest="output_file", help="Output file path (.py)"
    )
    decompile_p.add_argument(
        "--debug",
        action="store_true",
        help="Include mlog instruction provenance comments (# mlog[<addr>])",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point for Python-to-mlog compiler and mlog-to-Python decompiler."""
    parser = _build_cli_parser()

    raw_args = list(sys.argv[1:] if argv is None else argv)

    # Backward compatibility:
    # If first argument is not a known subcommand ('compile', 'decompile', '-h', '--help', empty),
    # default to the 'compile' command (e.g. `mlog-py script.py -o script.mlog`).
    if raw_args and raw_args[0] not in ("compile", "decompile", "-h", "--help", "-V", "--version"):
        raw_args = ["compile"] + raw_args

    args = parser.parse_args(raw_args)

    if args.command == "compile":
        return _cli_compile(args)
    elif args.command == "decompile":
        return _cli_decompile(args)
    else:
        parser.print_help(sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
