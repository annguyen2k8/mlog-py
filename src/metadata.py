"""Single Source of Truth (SSOT) metadata for Mindustry Logic compiler and Python DSL.

Defines all compiler intrinsics, signatures, docstrings, argument constraints,
and runtime implementations. Generates IDE typing stubs (.pyi) for VS Code / Pylance
and keeps runtime module, IDE stubs, and compiler passes strictly synchronized.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

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
    ENUM_CLASS_TO_REGISTRY,
)


@dataclass(frozen=True)
class IntrinsicParam:
    """Parameter definition for an intrinsic signature."""
    name: str
    type_annotation: str
    default: Optional[str] = None


@dataclass(frozen=True)
class IntrinsicSignature:
    """A typed calling signature for an intrinsic (used for IDE stub generation and doc)."""
    params: List[IntrinsicParam]
    return_type: str
    docstring: str


@dataclass
class IntrinsicDef:
    """Complete metadata definition for a compiler intrinsic."""
    name: str
    summary: str
    docstring: str
    min_args: int
    max_args: int
    valid_arg_counts: Tuple[int, ...]
    signatures: List[IntrinsicSignature]
    runtime_fn: Callable[..., Any]
    has_assignment_form: bool = False


# ---------------------------------------------------------------------------
# Runtime implementations (executed when Python runs the script directly)
# ---------------------------------------------------------------------------

def _rt_jump(target: Any, cond: Any = "always", a: Any = 0, b: Any = 0) -> None:
    return None

def _rt_set(to: Any, from_: Any) -> Any:
    return from_

def _rt_op(op_name: Any, *args: Any) -> Any:
    return 0

def _rt_sensor(*args: Any) -> Any:
    return 0

def _rt_control(type_: Any, target: Any, *params: Any) -> None:
    return None

def _rt_ucontrol(action: Any, *params: Any) -> None:
    return None

def _rt_draw(type_: Any, *params: Any) -> None:
    return None

def _rt_drawflush(display: Any) -> None:
    return None

def _rt_print(value: Any = "") -> None:
    return None

def _rt_printflush(message: Any) -> None:
    return None

def _rt_read(*args: Any) -> Any:
    return 0

def _rt_write(input_: Any, cell: Any, address: Any) -> None:
    return None

def _rt_wait(seconds: Any = 0.5) -> None:
    return None

def _rt_stop() -> None:
    return None

def _rt_end() -> None:
    return None

def _rt_ubind(unit_type: Any) -> None:
    return None

def _rt_radar(*args: Any) -> Any:
    return 0

def _rt_uradar(*args: Any) -> Any:
    return 0

def _rt_ulocate(*args: Any) -> None:
    return None

def _rt_lookup(*args: Any) -> Any:
    return 0

def _rt_packcolor(*args: Any) -> Any:
    return 0

def _rt_getlink(*args: Any) -> Any:
    return 0

def _rt_raw(value: Any) -> str:
    return str(value)


# ---------------------------------------------------------------------------
# Canonical Intrinsic Definitions (Single Source of Truth)
# ---------------------------------------------------------------------------

INTRINSIC_DEFINITIONS: List[IntrinsicDef] = [
    IntrinsicDef(
        name="jump",
        summary="Conditionally or unconditionally jump to a label or instruction address",
        docstring=(
            "Jump to a label or instruction address conditionally or unconditionally.\n\n"
            "Args:\n"
            "    target: Symbolic label name or numeric instruction address.\n"
            "    cond: Jump condition (Condition enum or string, e.g. Condition.EQUAL, 'lessThan', default 'always').\n"
            "    a: First comparison operand (default 0).\n"
            "    b: Second comparison operand (default 0)."
        ),
        min_args=1,
        max_args=4,
        valid_arg_counts=(1, 2, 3, 4),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("target", "Union[str, int]"),
                    IntrinsicParam("cond", "Union[Condition, str]", default='"always"'),
                    IntrinsicParam("a", "Any", default="0"),
                    IntrinsicParam("b", "Any", default="0"),
                ],
                return_type="None",
                docstring="Jump to a target label or address.",
            ),
        ],
        runtime_fn=_rt_jump,
    ),
    IntrinsicDef(
        name="set",
        summary="Set a variable to a value",
        docstring=(
            "Set a variable to a value.\n\n"
            "Args:\n"
            "    to: Target variable.\n"
            "    from_: Source value, variable, or literal."
        ),
        min_args=2,
        max_args=2,
        valid_arg_counts=(2,),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("to", "Any"),
                    IntrinsicParam("from_", "Any"),
                ],
                return_type="Any",
                docstring="Assign from_ value to variable to.",
            ),
        ],
        runtime_fn=_rt_set,
        has_assignment_form=True,
    ),
    IntrinsicDef(
        name="op",
        summary="Perform an arithmetic, logical, or mathematical operation",
        docstring=(
            "Perform a logic operation (arithmetic, bitwise, math function).\n\n"
            "Supported call conventions:\n"
            "    1. Expression form: result = op(op_name, a, b=0)\n"
            "    2. Statement form:  op(op_name, dest, a, b=0)\n\n"
            "Args:\n"
            "    op_name: LogicOp enum or operation string (e.g. LogicOp.ADD, 'mul', 'sin', 'rand').\n"
            "    dest: Target variable (in statement form).\n"
            "    a: First operand.\n"
            "    b: Second operand (default 0 for unary ops like sin, not, etc.)."
        ),
        min_args=2,
        max_args=4,
        valid_arg_counts=(2, 3, 4),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("op_name", "Union[LogicOp, str]"),
                    IntrinsicParam("dest", "Any"),
                    IntrinsicParam("a", "Any"),
                    IntrinsicParam("b", "Any", default="0"),
                ],
                return_type="Any",
                docstring="Perform operation and write result to dest variable (statement form).",
            ),
            IntrinsicSignature(
                params=[
                    IntrinsicParam("op_name", "Union[LogicOp, str]"),
                    IntrinsicParam("a", "Any"),
                    IntrinsicParam("b", "Any", default="0"),
                ],
                return_type="Any",
                docstring="Perform operation and return result (expression form: dest = op(...)).",
            ),
        ],
        runtime_fn=_rt_op,
        has_assignment_form=True,
    ),
    IntrinsicDef(
        name="sensor",
        summary="Read a property, item count, or liquid volume from a building or unit",
        docstring=(
            "Read a property, item count, or liquid volume from a building or unit.\n\n"
            "Supported call conventions:\n"
            "    1. Expression form: hp = sensor(building, SensorProperty.HEALTH)\n"
            "    2. Statement form:  sensor(hp, building, SensorProperty.HEALTH)\n\n"
            "Args:\n"
            "    dest: Target variable (in statement form).\n"
            "    block: Target building or unit.\n"
            "    prop: SensorProperty enum, string token (e.g. '@health', '@copper'), or raw()."
        ),
        min_args=2,
        max_args=3,
        valid_arg_counts=(2, 3),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("dest", "Any"),
                    IntrinsicParam("block", "Any"),
                    IntrinsicParam("prop", "Union[SensorProperty, str]"),
                ],
                return_type="Any",
                docstring="Read property from block into dest variable (statement form).",
            ),
            IntrinsicSignature(
                params=[
                    IntrinsicParam("block", "Any"),
                    IntrinsicParam("prop", "Union[SensorProperty, str]"),
                ],
                return_type="Any",
                docstring="Read property from block and return result (expression form: dest = sensor(...)).",
            ),
        ],
        runtime_fn=_rt_sensor,
        has_assignment_form=True,
    ),
    IntrinsicDef(
        name="control",
        summary="Control a building property (enabled, shoot, shootp, config, color)",
        docstring=(
            "Control a building property.\n\n"
            "Args:\n"
            "    type: ControlProperty enum or string (e.g. ControlProperty.ENABLED, 'shoot').\n"
            "    target: Target building.\n"
            "    p1, p2, p3, p4: Control parameters (default 0)."
        ),
        min_args=2,
        max_args=6,
        valid_arg_counts=(2, 3, 4, 5, 6),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("type", "Union[ControlProperty, str]"),
                    IntrinsicParam("target", "Any"),
                    IntrinsicParam("p1", "Any", default="0"),
                    IntrinsicParam("p2", "Any", default="0"),
                    IntrinsicParam("p3", "Any", default="0"),
                    IntrinsicParam("p4", "Any", default="0"),
                ],
                return_type="None",
                docstring="Set building control state.",
            ),
        ],
        runtime_fn=_rt_control,
    ),
    IntrinsicDef(
        name="ucontrol",
        summary="Issue a command to the currently bound unit",
        docstring=(
            "Issue a command to the currently bound unit.\n\n"
            "Args:\n"
            "    action: UnitControl enum or string (e.g. UnitControl.MOVE, UnitControl.APPROACH, 'target').\n"
            "    p1, p2, p3, p4, p5: Command parameters (default 0)."
        ),
        min_args=1,
        max_args=6,
        valid_arg_counts=(1, 2, 3, 4, 5, 6),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("action", "Union[UnitControl, str]"),
                    IntrinsicParam("p1", "Any", default="0"),
                    IntrinsicParam("p2", "Any", default="0"),
                    IntrinsicParam("p3", "Any", default="0"),
                    IntrinsicParam("p4", "Any", default="0"),
                    IntrinsicParam("p5", "Any", default="0"),
                ],
                return_type="None",
                docstring="Command bound unit.",
            ),
        ],
        runtime_fn=_rt_ucontrol,
    ),
    IntrinsicDef(
        name="draw",
        summary="Queue a drawing operation to the display buffer",
        docstring=(
            "Queue a drawing operation to display buffer.\n\n"
            "Args:\n"
            "    type: DrawType enum or string (e.g. DrawType.CLEAR, DrawType.LINE, DrawType.RECT, 'color').\n"
            "    x, y, p1, p2, p3, p4: Drawing coordinates, dimensions, or color components (default 0)."
        ),
        min_args=1,
        max_args=7,
        valid_arg_counts=(1, 2, 3, 4, 5, 6, 7),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("type", "Union[DrawType, str]"),
                    IntrinsicParam("x", "Any", default="0"),
                    IntrinsicParam("y", "Any", default="0"),
                    IntrinsicParam("p1", "Any", default="0"),
                    IntrinsicParam("p2", "Any", default="0"),
                    IntrinsicParam("p3", "Any", default="0"),
                    IntrinsicParam("p4", "Any", default="0"),
                ],
                return_type="None",
                docstring="Queue drawing operation.",
            ),
        ],
        runtime_fn=_rt_draw,
    ),
    IntrinsicDef(
        name="drawflush",
        summary="Flush queued draw operations to a logic display building",
        docstring=(
            "Flush queued draw operations to a logic display building.\n\n"
            "Args:\n"
            "    display: Target display block."
        ),
        min_args=1,
        max_args=1,
        valid_arg_counts=(1,),
        signatures=[
            IntrinsicSignature(
                params=[IntrinsicParam("display", "Any")],
                return_type="None",
                docstring="Flush display buffer.",
            ),
        ],
        runtime_fn=_rt_drawflush,
    ),
    IntrinsicDef(
        name="print",
        summary="Append text or a value to the processor print buffer",
        docstring=(
            "Append text or a value to the processor print buffer.\n\n"
            "Args:\n"
            "    value: Text string literal or variable to print."
        ),
        min_args=1,
        max_args=1,
        valid_arg_counts=(1,),
        signatures=[
            IntrinsicSignature(
                params=[IntrinsicParam("value", "Any")],
                return_type="None",
                docstring="Append value to print buffer.",
            ),
        ],
        runtime_fn=_rt_print,
    ),
    IntrinsicDef(
        name="printflush",
        summary="Flush the print buffer to a message block",
        docstring=(
            "Flush the print buffer to a message block.\n\n"
            "Args:\n"
            "    message: Target message block."
        ),
        min_args=1,
        max_args=1,
        valid_arg_counts=(1,),
        signatures=[
            IntrinsicSignature(
                params=[IntrinsicParam("message", "Any")],
                return_type="None",
                docstring="Flush print buffer to message block.",
            ),
        ],
        runtime_fn=_rt_printflush,
    ),
    IntrinsicDef(
        name="read",
        summary="Read a value from a memory cell or memory bank at index",
        docstring=(
            "Read a value from a memory cell or memory bank at the specified index.\n\n"
            "Supported call conventions:\n"
            "    1. Expression form: val = read(cell, index)\n"
            "    2. Statement form:  read(val, cell, index)\n\n"
            "Args:\n"
            "    dest: Target variable (in statement form).\n"
            "    cell: Target memory cell or memory bank.\n"
            "    address: Numeric address index."
        ),
        min_args=2,
        max_args=3,
        valid_arg_counts=(2, 3),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("dest", "Any"),
                    IntrinsicParam("cell", "Any"),
                    IntrinsicParam("address", "Any"),
                ],
                return_type="Any",
                docstring="Read number from cell at address into dest variable (statement form).",
            ),
            IntrinsicSignature(
                params=[
                    IntrinsicParam("cell", "Any"),
                    IntrinsicParam("address", "Any"),
                ],
                return_type="Any",
                docstring="Read number from cell at address and return it (expression form: dest = read(...)).",
            ),
        ],
        runtime_fn=_rt_read,
        has_assignment_form=True,
    ),
    IntrinsicDef(
        name="write",
        summary="Write a value to a memory cell or memory bank at index",
        docstring=(
            "Write a value to a memory cell or memory bank at the specified index.\n\n"
            "Args:\n"
            "    input: Value to write.\n"
            "    cell: Target memory cell or memory bank.\n"
            "    address: Numeric address index."
        ),
        min_args=3,
        max_args=3,
        valid_arg_counts=(3,),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("input", "Any"),
                    IntrinsicParam("cell", "Any"),
                    IntrinsicParam("address", "Any"),
                ],
                return_type="None",
                docstring="Write value to memory cell at address.",
            ),
        ],
        runtime_fn=_rt_write,
    ),
    IntrinsicDef(
        name="wait",
        summary="Pause processor execution for a specified duration in seconds",
        docstring=(
            "Pause processor execution for a duration in seconds.\n\n"
            "Args:\n"
            "    seconds: Duration to wait in seconds (default 0.5)."
        ),
        min_args=0,
        max_args=1,
        valid_arg_counts=(0, 1),
        signatures=[
            IntrinsicSignature(
                params=[IntrinsicParam("seconds", "Any", default="0.5")],
                return_type="None",
                docstring="Pause execution for seconds.",
            ),
        ],
        runtime_fn=_rt_wait,
    ),
    IntrinsicDef(
        name="stop",
        summary="Halt processor execution completely",
        docstring="Halt processor execution completely until reset.",
        min_args=0,
        max_args=0,
        valid_arg_counts=(0,),
        signatures=[
            IntrinsicSignature(
                params=[],
                return_type="None",
                docstring="Halt processor execution.",
            ),
        ],
        runtime_fn=_rt_stop,
    ),
    IntrinsicDef(
        name="end",
        summary="Jump processor execution back to instruction 0",
        docstring="Jump processor execution back to instruction 0 (restart loop).",
        min_args=0,
        max_args=0,
        valid_arg_counts=(0,),
        signatures=[
            IntrinsicSignature(
                params=[],
                return_type="None",
                docstring="Restart processor from instruction 0.",
            ),
        ],
        runtime_fn=_rt_end,
    ),
    IntrinsicDef(
        name="ubind",
        summary="Bind a unit of the specified type to this processor",
        docstring=(
            "Bind a unit of the specified type to this processor.\n\n"
            "Args:\n"
            "    unit_type: Units enum or string (e.g. Units.FLARE, '@flare', 'mono')."
        ),
        min_args=1,
        max_args=1,
        valid_arg_counts=(1,),
        signatures=[
            IntrinsicSignature(
                params=[IntrinsicParam("unit_type", "Union[Units, str]")],
                return_type="None",
                docstring="Bind a unit.",
            ),
        ],
        runtime_fn=_rt_ubind,
    ),
    IntrinsicDef(
        name="radar",
        summary="Locate units in range of a turret or building using radar filters",
        docstring=(
            "Locate units in range of a turret or building using radar filters.\n\n"
            "Supported call conventions:\n"
            "    1. Expression form: target = radar(target1, target2, target3, sort, turret, sort_order)\n"
            "    2. Statement form:  radar(target1, target2, target3, sort, turret, sort_order, target)\n\n"
            "Args:\n"
            "    target1, target2, target3: RadarTarget enum or string (e.g. RadarTarget.ENEMY, 'any').\n"
            "    sort: RadarSort enum or string (e.g. RadarSort.DISTANCE, 'health').\n"
            "    turret: Scanning turret or building.\n"
            "    sort_order: Sort direction (1 = min/closest, 0 = max/furthest).\n"
            "    output: Target variable (in statement form)."
        ),
        min_args=6,
        max_args=7,
        valid_arg_counts=(6, 7),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("target1", "Union[RadarTarget, str]"),
                    IntrinsicParam("target2", "Union[RadarTarget, str]"),
                    IntrinsicParam("target3", "Union[RadarTarget, str]"),
                    IntrinsicParam("sort", "Union[RadarSort, str]"),
                    IntrinsicParam("turret", "Any"),
                    IntrinsicParam("sort_order", "Any"),
                    IntrinsicParam("output", "Any"),
                ],
                return_type="Any",
                docstring="Scan radar and write found unit to output (statement form).",
            ),
            IntrinsicSignature(
                params=[
                    IntrinsicParam("target1", "Union[RadarTarget, str]"),
                    IntrinsicParam("target2", "Union[RadarTarget, str]"),
                    IntrinsicParam("target3", "Union[RadarTarget, str]"),
                    IntrinsicParam("sort", "Union[RadarSort, str]"),
                    IntrinsicParam("turret", "Any"),
                    IntrinsicParam("sort_order", "Any"),
                ],
                return_type="Any",
                docstring="Scan radar and return found unit (expression form: target = radar(...)).",
            ),
        ],
        runtime_fn=_rt_radar,
        has_assignment_form=True,
    ),
    IntrinsicDef(
        name="uradar",
        summary="Locate units using the currently bound unit radar",
        docstring=(
            "Locate units using the currently bound unit radar.\n\n"
            "Supported call conventions:\n"
            "    1. Expression form: target = uradar(target1, target2, target3, sort, sort_order)\n"
            "    2. Statement form:  uradar(target1, target2, target3, sort, sort_order, target)\n"
            "    3. Extended statement: uradar(target1, target2, target3, sort, p1, p2, target)\n\n"
            "Args:\n"
            "    target1, target2, target3: RadarTarget enum or string.\n"
            "    sort: RadarSort enum or string.\n"
            "    sort_order: Sort direction (1 = min, 0 = max).\n"
            "    output: Target variable (in statement form)."
        ),
        min_args=5,
        max_args=7,
        valid_arg_counts=(5, 6, 7),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("target1", "Union[RadarTarget, str]"),
                    IntrinsicParam("target2", "Union[RadarTarget, str]"),
                    IntrinsicParam("target3", "Union[RadarTarget, str]"),
                    IntrinsicParam("sort", "Union[RadarSort, str]"),
                    IntrinsicParam("sort_order", "Any"),
                    IntrinsicParam("output", "Any"),
                ],
                return_type="Any",
                docstring="Scan bound unit radar and write found unit to output (statement form).",
            ),
            IntrinsicSignature(
                params=[
                    IntrinsicParam("target1", "Union[RadarTarget, str]"),
                    IntrinsicParam("target2", "Union[RadarTarget, str]"),
                    IntrinsicParam("target3", "Union[RadarTarget, str]"),
                    IntrinsicParam("sort", "Union[RadarSort, str]"),
                    IntrinsicParam("p1", "Any"),
                    IntrinsicParam("p2", "Any"),
                    IntrinsicParam("output", "Any"),
                ],
                return_type="Any",
                docstring="Scan bound unit radar with extra parameters (extended statement form).",
            ),
            IntrinsicSignature(
                params=[
                    IntrinsicParam("target1", "Union[RadarTarget, str]"),
                    IntrinsicParam("target2", "Union[RadarTarget, str]"),
                    IntrinsicParam("target3", "Union[RadarTarget, str]"),
                    IntrinsicParam("sort", "Union[RadarSort, str]"),
                    IntrinsicParam("sort_order", "Any"),
                ],
                return_type="Any",
                docstring="Scan bound unit radar and return found unit (expression form: target = uradar(...)).",
            ),
        ],
        runtime_fn=_rt_uradar,
        has_assignment_form=True,
    ),
    IntrinsicDef(
        name="ulocate",
        summary="Locate positions, buildings, or ores with the bound unit",
        docstring=(
            "Locate positions, buildings, or ores with the bound unit.\n\n"
            "Args:\n"
            "    locate: Finding type ('ore', 'building', 'spawn', 'damaged').\n"
            "    flag: Finding flag / building type.\n"
            "    enemy: Enemy filter (1 / true, 0 / false).\n"
            "    ore: Ore type if locating ore (e.g. '@copper').\n"
            "    outX, outY: Output coordinates variables.\n"
            "    outFound: Output boolean found variable.\n"
            "    outBuild: Output building variable."
        ),
        min_args=8,
        max_args=8,
        valid_arg_counts=(8,),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("locate", "Any"),
                    IntrinsicParam("flag", "Any"),
                    IntrinsicParam("enemy", "Any"),
                    IntrinsicParam("ore", "Any"),
                    IntrinsicParam("outX", "Any"),
                    IntrinsicParam("outY", "Any"),
                    IntrinsicParam("outFound", "Any"),
                    IntrinsicParam("outBuild", "Any"),
                ],
                return_type="None",
                docstring="Locate target with bound unit.",
            ),
        ],
        runtime_fn=_rt_ulocate,
    ),
    IntrinsicDef(
        name="lookup",
        summary="Look up game content by ID index",
        docstring=(
            "Look up game content by ID index.\n\n"
            "Supported call conventions:\n"
            "    1. Expression form: item = lookup(LookupType.ITEM, 0)\n"
            "    2. Statement form:  lookup(LookupType.ITEM, item, 0)\n\n"
            "Args:\n"
            "    type: LookupType enum or string (item, block, unit, liquid, team).\n"
            "    dest: Target variable (in statement form).\n"
            "    index: Integer index."
        ),
        min_args=2,
        max_args=3,
        valid_arg_counts=(2, 3),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("type", "Union[LookupType, str]"),
                    IntrinsicParam("dest", "Any"),
                    IntrinsicParam("index", "Any"),
                ],
                return_type="Any",
                docstring="Look up content and write result to dest variable (statement form).",
            ),
            IntrinsicSignature(
                params=[
                    IntrinsicParam("type", "Union[LookupType, str]"),
                    IntrinsicParam("index", "Any"),
                ],
                return_type="Any",
                docstring="Look up content and return result (expression form: dest = lookup(...)).",
            ),
        ],
        runtime_fn=_rt_lookup,
        has_assignment_form=True,
    ),
    IntrinsicDef(
        name="packcolor",
        summary="Pack RGBA color components (0-1) into a single 64-bit number",
        docstring=(
            "Pack RGBA color components (0-1) into a single 64-bit number.\n\n"
            "Supported call conventions:\n"
            "    1. Expression form: col = packcolor(r, g, b, a)\n"
            "    2. Statement form:  packcolor(col, r, g, b, a)\n\n"
            "Args:\n"
            "    dest: Target variable (in statement form).\n"
            "    r, g, b, a: Red, green, blue, alpha components (0.0 to 1.0)."
        ),
        min_args=4,
        max_args=5,
        valid_arg_counts=(4, 5),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("dest", "Any"),
                    IntrinsicParam("r", "Any"),
                    IntrinsicParam("g", "Any"),
                    IntrinsicParam("b", "Any"),
                    IntrinsicParam("a", "Any"),
                ],
                return_type="Any",
                docstring="Pack color components into dest variable (statement form).",
            ),
            IntrinsicSignature(
                params=[
                    IntrinsicParam("r", "Any"),
                    IntrinsicParam("g", "Any"),
                    IntrinsicParam("b", "Any"),
                    IntrinsicParam("a", "Any"),
                ],
                return_type="Any",
                docstring="Pack color components and return result (expression form: dest = packcolor(...)).",
            ),
        ],
        runtime_fn=_rt_packcolor,
        has_assignment_form=True,
    ),
    IntrinsicDef(
        name="getlink",
        summary="Get linked building reference by link index",
        docstring=(
            "Get linked building reference by link index.\n\n"
            "Supported call conventions:\n"
            "    1. Expression form: block = getlink(0)\n"
            "    2. Statement form:  getlink(block, 0)\n\n"
            "Args:\n"
            "    dest: Target variable (in statement form).\n"
            "    index: 0-indexed link number."
        ),
        min_args=1,
        max_args=2,
        valid_arg_counts=(1, 2),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("dest", "Any"),
                    IntrinsicParam("index", "Any"),
                ],
                return_type="Any",
                docstring="Get linked block by index into dest variable (statement form).",
            ),
            IntrinsicSignature(
                params=[IntrinsicParam("index", "Any")],
                return_type="Any",
                docstring="Get linked block by index and return it (expression form: block = getlink(i)).",
            ),
        ],
        runtime_fn=_rt_getlink,
        has_assignment_form=True,
    ),
    IntrinsicDef(
        name="raw",
        summary="Explicit escape hatch to bypass registry validation in mlog code",
        docstring=(
            "Explicit escape hatch to bypass registry validation in mlog code.\n\n"
            "Args:\n"
            "    value: Unverified property string or token (e.g. '@myCustomModProp').\n\n"
            "Returns:\n"
            "    Raw token string that compiles verbatim into output mlog."
        ),
        min_args=1,
        max_args=1,
        valid_arg_counts=(1,),
        signatures=[
            IntrinsicSignature(
                params=[IntrinsicParam("value", "Any")],
                return_type="str",
                docstring="Bypass static registry validation and emit value verbatim.",
            ),
        ],
        runtime_fn=_rt_raw,
    ),
]

# Map by intrinsic name
INTRINSICS: Dict[str, IntrinsicDef] = {d.name: d for d in INTRINSIC_DEFINITIONS}

# Whitelist of allowed compiler intrinsic call names
ALLOWED_INTRINSICS: Set[str] = set(INTRINSICS.keys())

# Registry Enums dictionary (Enum class objects)
ALL_REGISTRY_ENUMS: Dict[str, type] = {
    "SensorProperty": SensorProperty,
    "ControlProperty": ControlProperty,
    "UnitControl": UnitControl,
    "DrawType": DrawType,
    "LogicOp": LogicOp,
    "Condition": Condition,
    "RadarTarget": RadarTarget,
    "RadarSort": RadarSort,
    "Items": Items,
    "Liquids": Liquids,
    "Units": Units,
    "Teams": Teams,
    "LookupType": LookupType,
}

# Complete set of symbols exported by the official `mlog` package
MLOG_EXPORTS: Set[str] = (
    ALLOWED_INTRINSICS
    | set(ALL_REGISTRY_ENUMS.keys())
    | {
        "compile_py",
        "CompileResult",
        "main",
        "null",
        "raw",
    }
)


# ---------------------------------------------------------------------------
# Stub (.pyi) Generator for VS Code / Pylance
# ---------------------------------------------------------------------------

def generate_pyi() -> str:
    """Generate the complete mlog.pyi typing stub content from compiler metadata.

    Guarantees that VS Code/Pylance receives accurate signature overloads,
    autocomplete documentation, and full Enum typing, completely synchronized
    with the compiler metadata single source of truth.
    """
    lines: List[str] = []
    lines.append('"""Auto-generated IDE typing stub for Mindustry Logic (mlog) Python DSL.')
    lines.append("Single Source of Truth: src/metadata.py and src/mlog_registry.py.")
    lines.append('Do not edit directly; regenerated and verified via test suite.')
    lines.append('"""')
    lines.append("")
    lines.append("from enum import Enum")
    lines.append("from typing import Any, Dict, List, Optional, Union, overload")
    lines.append("")
    lines.append("# Null constant representing null in Mindustry Logic")
    lines.append("null: Any = None")
    lines.append("")

    # Emit Enums
    lines.append("# " + "-" * 75)
    lines.append("# Mindustry Logic Enums (Three-Tier Tier 1)")
    lines.append("# " + "-" * 75)
    lines.append("")

    for enum_name in sorted(ALL_REGISTRY_ENUMS.keys()):
        enum_cls = ALL_REGISTRY_ENUMS[enum_name]
        lines.append(f"class {enum_name}(Enum):")
        doc = f'    """Mindustry Logic {enum_name} registry enum."""'
        lines.append(doc)
        members = getattr(enum_cls, "__members__", {})
        if members:
            for member_name in sorted(members.keys()):
                lines.append(f"    {member_name}: '{enum_name}'")
        else:
            lines.append("    ...")
        lines.append("")

    # Emit Compiler APIs
    lines.append("# " + "-" * 75)
    lines.append("# Compiler Core Entry Points")
    lines.append("# " + "-" * 75)
    lines.append("")
    lines.append("class CompileResult:")
    lines.append('    """Result of compilation containing final mlog text, IR, and label table."""')
    lines.append("    mlog: str")
    lines.append("    ir: List[Any]")
    lines.append("    label_table: Dict[str, int]")
    lines.append("")
    lines.append(
        "def compile_py(source: str, filename: str = '<stdin>', optimize: bool = False, validate: bool = True) -> CompileResult:"
    )
    lines.append('    """Compile Python subset source code into canonical vanilla mlog."""')
    lines.append("    ...")
    lines.append("")
    lines.append("def main(argv: Optional[List[str]] = None) -> int:")
    lines.append('    """CLI entry point for Python-to-mlog compiler."""')
    lines.append("    ...")
    lines.append("")

    # Emit Intrinsics
    lines.append("# " + "-" * 75)
    lines.append("# Compiler Intrinsics (Python DSL APIs)")
    lines.append("# " + "-" * 75)
    lines.append("")

    for name in sorted(INTRINSICS.keys()):
        idef = INTRINSICS[name]
        if len(idef.signatures) > 1:
            for sig in idef.signatures:
                param_strs = []
                for p in sig.params:
                    if p.default is not None:
                        param_strs.append(f"{p.name}: {p.type_annotation} = {p.default}")
                    else:
                        param_strs.append(f"{p.name}: {p.type_annotation}")
                params_joined = ", ".join(param_strs)
                lines.append("@overload")
                lines.append(f"def {name}({params_joined}) -> {sig.return_type}:")
                # Indented docstring
                doc_lines = sig.docstring.strip().splitlines()
                lines.append('    """' + doc_lines[0])
                for dl in doc_lines[1:]:
                    lines.append("    " + dl)
                lines.append('    """')
                lines.append("    ...")
                lines.append("")
        else:
            sig = idef.signatures[0]
            param_strs = []
            for p in sig.params:
                if p.default is not None:
                    param_strs.append(f"{p.name}: {p.type_annotation} = {p.default}")
                else:
                    param_strs.append(f"{p.name}: {p.type_annotation}")
            params_joined = ", ".join(param_strs)
            lines.append(f"def {name}({params_joined}) -> {sig.return_type}:")
            doc_lines = idef.docstring.strip().splitlines()
            lines.append('    """' + doc_lines[0])
            for dl in doc_lines[1:]:
                lines.append("    " + dl)
            lines.append('    """')
            lines.append("    ...")
            lines.append("")

    # Emit __all__
    all_exports_sorted = sorted(list(MLOG_EXPORTS))
    lines.append("__all__ = [")
    for exp in all_exports_sorted:
        lines.append(f'    "{exp}",')
    lines.append("]")
    lines.append("")

    return "\n".join(lines)
