"""Semantic argument recovery and classification for Mindustry Logic (mlog).

Single source of truth (SSOT) based on Mindustry opcode signatures and
`INTRINSIC_DEFINITIONS` in src.metadata.

Distinguishes between:
- MLog variable definitions (written to)
- MLog variable usages (read from)
- Named block / device / hardware link references (e.g. cell1, display1, message1)
- Special @constants (e.g. @unit, @counter, @this)
- Numeric literals (int, float)
- String literals ("...")
- Keywords / enums (e.g. "clear", "enabled", "itemDrop")
- General operands
"""

from enum import Enum
from typing import Dict, Iterable, List, Optional, Set, Tuple

from src.decompiler.parser import MlogInstruction
from src.metadata import INTRINSIC_DEFINITIONS, IntrinsicDef


class ArgumentSemanticRole(Enum):
    """Semantic role of an instruction argument."""
    VARIABLE_DEF = "variable_def"          # Destination variable defined/written
    BLOCK_OR_DEVICE = "block_or_device"    # Mindustry hardware link / device reference
    KEYWORD_OR_ENUM = "keyword_or_enum"    # Operation name / mode / enum literal
    SPECIAL_CONSTANT = "special_constant"  # Built-in @constant (@unit, @counter, etc.)
    NUMERIC_LITERAL = "numeric_literal"    # Integer or float literal
    STRING_LITERAL = "string_literal"      # Text string literal
    OPERAND = "operand"                    # General value or variable read


def is_special_constant(token: str) -> bool:
    """Check if token is an mlog special constant (starting with @)."""
    return token.startswith("@")


def is_numeric_literal(token: str) -> bool:
    """Check if token is a valid integer or float literal."""
    if token.isdigit() or (token.startswith("-") and token[1:].isdigit()):
        return True
    try:
        float(token)
        return True
    except ValueError:
        return False


def is_string_literal(token: str) -> bool:
    """Check if token is an explicit quoted string literal."""
    return len(token) >= 2 and token.startswith('"') and token.endswith('"')


def quote_string_literal(val: str) -> str:
    """Format string with canonical double quotes escaping quotes and backslashes."""
    escaped = val.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


# Fast lookup of intrinsic definition by opcode name
_INTRINSIC_BY_NAME: Dict[str, IntrinsicDef] = {idef.name: idef for idef in INTRINSIC_DEFINITIONS}

# Map parameter names from INTRINSIC_DEFINITIONS to default semantic roles
_PARAM_ROLE_MAP: Dict[str, ArgumentSemanticRole] = {
    # Destination variables
    "dest": ArgumentSemanticRole.VARIABLE_DEF,
    "output": ArgumentSemanticRole.VARIABLE_DEF,
    "to": ArgumentSemanticRole.VARIABLE_DEF,
    "outX": ArgumentSemanticRole.VARIABLE_DEF,
    "outY": ArgumentSemanticRole.VARIABLE_DEF,
    "outFound": ArgumentSemanticRole.VARIABLE_DEF,
    "outBuild": ArgumentSemanticRole.VARIABLE_DEF,

    # Block / Device references
    "display": ArgumentSemanticRole.BLOCK_OR_DEVICE,
    "message": ArgumentSemanticRole.BLOCK_OR_DEVICE,
    "cell": ArgumentSemanticRole.BLOCK_OR_DEVICE,
    "block": ArgumentSemanticRole.BLOCK_OR_DEVICE,
    "turret": ArgumentSemanticRole.BLOCK_OR_DEVICE,

    # Keywords / Enums / Modes
    "op_name": ArgumentSemanticRole.KEYWORD_OR_ENUM,
    "type": ArgumentSemanticRole.KEYWORD_OR_ENUM,
    "action": ArgumentSemanticRole.KEYWORD_OR_ENUM,
    "locate": ArgumentSemanticRole.KEYWORD_OR_ENUM,
    "target1": ArgumentSemanticRole.KEYWORD_OR_ENUM,
    "target2": ArgumentSemanticRole.KEYWORD_OR_ENUM,
    "target3": ArgumentSemanticRole.KEYWORD_OR_ENUM,
    "sort": ArgumentSemanticRole.KEYWORD_OR_ENUM,
    "unit_type": ArgumentSemanticRole.KEYWORD_OR_ENUM,
    "cond": ArgumentSemanticRole.KEYWORD_OR_ENUM,
    "prop": ArgumentSemanticRole.KEYWORD_OR_ENUM,
}


def get_argument_semantic_role(
    opcode: str,
    arg_idx: int,
    args: Optional[Tuple[str, ...]] = None,
) -> ArgumentSemanticRole:
    """Determine the semantic role of an argument given opcode and argument index."""
    # Special polymorphic opcode: ucontrol
    if opcode == "ucontrol":
        action = args[0] if (args and len(args) > 0) else ""
        if arg_idx == 0:
            return ArgumentSemanticRole.KEYWORD_OR_ENUM
        if action in ("itemDrop", "itemTake") and arg_idx == 1:
            return ArgumentSemanticRole.BLOCK_OR_DEVICE
        if action == "build" and arg_idx == 3:
            return ArgumentSemanticRole.KEYWORD_OR_ENUM
        if action == "getBlock" and arg_idx in (3, 4, 5):
            return ArgumentSemanticRole.VARIABLE_DEF
        return ArgumentSemanticRole.OPERAND

    # Lookup intrinsic definition from metadata
    idef = _INTRINSIC_BY_NAME.get(opcode)
    if idef is None:
        # Zero guessing: if opcode is unknown, treat as general operand
        return ArgumentSemanticRole.OPERAND

    # Match the signature whose parameter count is closest/matching
    target_sig = None
    if args is not None:
        for sig in idef.signatures:
            if len(sig.params) == len(args):
                target_sig = sig
                break
    if target_sig is None:
        target_sig = idef.signatures[0] if idef.signatures else None

    if target_sig is None or arg_idx >= len(target_sig.params):
        return ArgumentSemanticRole.OPERAND

    param = target_sig.params[arg_idx]
    param_name = param.name

    # Control target is a building/block
    if opcode == "control" and param_name == "target":
        return ArgumentSemanticRole.BLOCK_OR_DEVICE

    # Jump target is label/address
    if opcode == "jump" and param_name == "target":
        return ArgumentSemanticRole.OPERAND

    return _PARAM_ROLE_MAP.get(param_name, ArgumentSemanticRole.OPERAND)


def get_instruction_dest_vars(instr: MlogInstruction) -> List[str]:
    """Get list of variable names written (defined) by this instruction."""
    op = instr.opcode
    args = instr.args
    if op == "set" and len(args) >= 1:
        return [args[0]]
    if op == "op" and len(args) >= 2:
        return [args[1]]
    if op in ("read", "sensor", "packcolor", "getlink") and len(args) >= 1:
        return [args[0]]
    if op == "lookup" and len(args) >= 2:
        return [args[1]]
    if op == "radar" and len(args) >= 7:
        return [args[6]]
    if op == "uradar":
        if len(args) == 6:
            return [args[5]]
        if len(args) >= 7:
            return [args[6]]
    if op == "ulocate" and len(args) >= 8:
        return [args[4], args[5], args[6], args[7]]
    if op == "ucontrol" and len(args) >= 6 and args[0] == "getBlock":
        return [args[3], args[4], args[5]]
    return []


def collect_program_defined_variables(instructions: Iterable[MlogInstruction]) -> Set[str]:
    """Scan all instructions in a program to collect all variable names defined (written to)."""
    defined: Set[str] = set()
    for instr in instructions:
        for var in get_instruction_dest_vars(instr):
            if var.isidentifier() and not var.startswith("@") and var not in ("true", "false", "null"):
                defined.add(var)
    return defined


def get_instruction_read_vars(
    instr: MlogInstruction,
    defined_variables: Optional[Set[str]] = None,
) -> List[str]:
    """Get all variable names read by an instruction, filtering out block devices and enums."""
    op = instr.opcode
    args = instr.args
    reads: List[str] = []

    for idx, arg in enumerate(args):
        if is_special_constant(arg) or is_numeric_literal(arg) or is_string_literal(arg):
            continue
        if arg in ("true", "false", "null") or not arg.isidentifier():
            continue

        role = get_argument_semantic_role(op, idx, args)
        if role == ArgumentSemanticRole.VARIABLE_DEF:
            continue
        if role == ArgumentSemanticRole.BLOCK_OR_DEVICE:
            # Only treat as a variable read if it was defined in the program as a variable
            if defined_variables is not None and arg in defined_variables:
                reads.append(arg)
            continue
        if role == ArgumentSemanticRole.KEYWORD_OR_ENUM:
            # Operation names and enums are not variables
            continue

        # General OPERAND
        reads.append(arg)

    return reads


def format_semantic_argument(
    opcode: str,
    arg_idx: int,
    arg: str,
    defined_variables: Optional[Set[str]] = None,
    args: Optional[Tuple[str, ...]] = None,
) -> str:
    """Format an argument into its proper Python DSL representation based on semantics and SSOT."""
    # 1. String literal already
    if is_string_literal(arg):
        return arg

    # 2. Special constants (@unit, @counter, @health, @copper, @this, etc.)
    if is_special_constant(arg):
        return quote_string_literal(arg)

    # 3. Numeric literal (int or float)
    if is_numeric_literal(arg):
        return arg

    # 4. Booleans and null
    if arg == "true":
        return "True"
    if arg == "false":
        return "False"
    if arg == "null":
        return "None"

    # 5. Determine semantic role from metadata SSOT
    role = get_argument_semantic_role(opcode, arg_idx, args)

    if role == ArgumentSemanticRole.BLOCK_OR_DEVICE:
        # If the argument is defined as a variable in the program,
        # emit as unquoted identifier.
        # Otherwise, it is a named hardware link / device reference -> emit as string literal!
        if defined_variables is not None and arg in defined_variables:
            return arg
        return quote_string_literal(arg)

    if role == ArgumentSemanticRole.VARIABLE_DEF:
        if arg.isidentifier() and not arg.startswith("@"):
            return arg
        return quote_string_literal(arg)

    # For general OPERAND or KEYWORD_OR_ENUM:
    if arg.isidentifier() and not arg.startswith("@"):
        return arg

    return quote_string_literal(arg)
