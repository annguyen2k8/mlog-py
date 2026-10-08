"""Main API and CLI interface for Python-to-mlog compiler."""

import argparse
import builtins
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional

_cli_print = builtins.print

from .compiler import Compiler
from .emitter import Emitter
from .errors import CompileError
from .ir import IRNode
from .mlog_registry import (
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
)
from .metadata import (
    MLOG_EXPORTS,
    _rt_control as control,
    _rt_draw as draw,
    _rt_drawflush as drawflush,
    _rt_end as end,
    _rt_getlink as getlink,
    _rt_jump as jump,
    _rt_lookup as lookup,
    _rt_op as op,
    _rt_packcolor as packcolor,
    _rt_print as print,
    _rt_printflush as printflush,
    _rt_radar as radar,
    _rt_raw as raw,
    _rt_read as read,
    _rt_sensor as sensor,
    _rt_set as set,
    _rt_stop as stop,
    _rt_ubind as ubind,
    _rt_ucontrol as ucontrol,
    _rt_ulocate as ulocate,
    _rt_uradar as uradar,
    _rt_wait as wait,
    _rt_write as write,
)
from .optimizer import PassThroughOptimizer
from .parser import parse_and_validate
from .validator import MlogValidator, ValidationError

# Null constant representing null in Mindustry Logic
null = None

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
) -> CompileResult:
    """Compile Python subset source code into canonical vanilla mlog.

    Args:
        source: Python code string.
        filename: Source file name for error reporting.
        optimize: Enable optimization passes (PassThrough in Phase 1).
        validate: Validate emitted mlog against Mindustry syntax rules.
        allow_functions: Allow user-defined function definitions and calls.

    Returns:
        CompileResult containing the emitted mlog, IR instructions, and label table.
    """
    # 1. Parse & validate Python AST subset
    tree = parse_and_validate(source, filename, allow_functions=allow_functions)

    # 2. Lower AST to IR
    compiler = Compiler(filename, allow_functions=allow_functions)
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
        sys.stdout.write(result.mlog)

    return 0


def _cli_decompile(args: argparse.Namespace) -> int:
    """Handle decompile subcommand: MLog -> Python DSL."""
    from .decompiler import decompile
    from .decompiler.errors import DecompileError

    try:
        with open(args.input_file, "r", encoding="utf-8") as f:
            mlog_source = f.read()
    except OSError as e:
        _cli_print(f"Error reading file '{args.input_file}': {e}", file=sys.stderr)
        return 1

    try:
        python_code = decompile(
            mlog_source,
            filename=args.input_file,
            debug=args.debug,
        )
    except DecompileError as e:
        _cli_print(f"Decompilation error: {e}", file=sys.stderr)
        return 1

    if args.output_file:
        try:
            with open(args.output_file, "w", encoding="utf-8") as f:
                f.write(python_code)
        except OSError as e:
            _cli_print(f"Error writing output file '{args.output_file}': {e}", file=sys.stderr)
            return 1
    else:
        sys.stdout.write(python_code)

    return 0


def _build_cli_parser() -> argparse.ArgumentParser:
    """Build the argument parser supporting 'compile' and 'decompile' subcommands."""
    parser = argparse.ArgumentParser(
        prog="mlog-py",
        description="Compile a controlled Python subset into Mindustry Logic (mlog) or decompile mlog to Python DSL.",
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

    # Subcommand: decompile (MLog -> Python DSL)
    decompile_p = subparsers.add_parser(
        "decompile",
        help="Decompile MLog -> Python DSL",
        description="Decompile Mindustry Logic (mlog) into structured Python DSL.",
    )
    decompile_p.add_argument("input_file", help="Input Mindustry Logic file (.mlog)")
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
    if raw_args and raw_args[0] not in ("compile", "decompile", "-h", "--help"):
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
