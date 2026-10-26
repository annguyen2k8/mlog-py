"""Single Source of Truth (SSOT) metadata for Mindustry Logic compiler and Python DSL.

Defines all compiler intrinsics, signatures, docstrings, argument constraints,
and runtime implementations. Generates IDE typing stubs (.pyi) for VS Code / Pylance
and keeps runtime module, IDE stubs, and compiler passes strictly synchronized.
"""

import math
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Set, Tuple, Union

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
    REG_ALIGN,
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
    BUILTIN_VARIABLES_DATA,
)
from .mlog_registry_data import BUILTIN_VARS_SPEC


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

class _OpCallable:
    """Callable namespace object for Mindustry logic operations.

    Supports both legacy function-call syntax:
        op("add", dest, a, b)
        result = op("add", a, b)
    and modern namespace method syntax:
        result = op.add(a, b)
        op.add(dest, a, b)
        result = op.sin(deg)
        op.sin(dest, deg)
    """

    def __call__(self, op_name: Any, *args: Any) -> Any:
        return 0

    # Unary operations (16)
    def abs(self, *args: Any) -> Any:
        return 0

    def sign(self, *args: Any) -> Any:
        return 0

    def log(self, *args: Any) -> Any:
        return 0

    def log10(self, *args: Any) -> Any:
        return 0

    log_10 = log10

    def floor(self, *args: Any) -> Any:
        return 0

    def ceil(self, *args: Any) -> Any:
        return 0

    def round(self, *args: Any) -> Any:
        return 0

    def sqrt(self, *args: Any) -> Any:
        return 0

    def rand(self, *args: Any) -> Any:
        return 0

    def sin(self, *args: Any) -> Any:
        return 0

    def cos(self, *args: Any) -> Any:
        return 0

    def tan(self, *args: Any) -> Any:
        return 0

    def asin(self, *args: Any) -> Any:
        return 0

    def acos(self, *args: Any) -> Any:
        return 0

    def atan(self, *args: Any) -> Any:
        return 0

    # Binary operations (27)
    def add(self, *args: Any) -> Any:
        return 0

    def sub(self, *args: Any) -> Any:
        return 0

    def mul(self, *args: Any) -> Any:
        return 0

    def div(self, *args: Any) -> Any:
        return 0

    def idiv(self, *args: Any) -> Any:
        return 0

    def mod(self, *args: Any) -> Any:
        return 0

    def emod(self, *args: Any) -> Any:
        return 0

    def pow(self, *args: Any) -> Any:
        return 0

    def equal(self, *args: Any) -> Any:
        return 0

    def not_equal(self, *args: Any) -> Any:
        return 0

    notEqual = not_equal

    def land(self, *args: Any) -> Any:
        return 0

    def less_than(self, *args: Any) -> Any:
        return 0

    lessThan = less_than

    def less_than_eq(self, *args: Any) -> Any:
        return 0

    lessThanEq = less_than_eq

    def greater_than(self, *args: Any) -> Any:
        return 0

    greaterThan = greater_than

    def greater_than_eq(self, *args: Any) -> Any:
        return 0

    greaterThanEq = greater_than_eq

    def strict_equal(self, *args: Any) -> Any:
        return 0

    strictEqual = strict_equal

    def shl(self, *args: Any) -> Any:
        return 0

    def shr(self, *args: Any) -> Any:
        return 0

    def ushr(self, *args: Any) -> Any:
        return 0

    def xor(self, *args: Any) -> Any:
        return 0

    def max(self, *args: Any) -> Any:
        return 0

    def min(self, *args: Any) -> Any:
        return 0

    def angle(self, *args: Any) -> Any:
        return 0

    def angle_diff(self, *args: Any) -> Any:
        return 0

    angleDiff = angle_diff

    def len(self, *args: Any) -> Any:
        return 0

    length = len

    def noise(self, *args: Any) -> Any:
        return 0

    def logn(self, *args: Any) -> Any:
        return 0


_rt_op = _OpCallable()

def _rt_min(a: Any, b: Any) -> Any:
    return min(a, b)

def _rt_max(a: Any, b: Any) -> Any:
    return max(a, b)

def _rt_sensor(*args: Any) -> Any:
    return 0

def _rt_control(type_: Any, target: Any, *params: Any) -> None:
    return None

class _UnitControlCallable:
    """Callable namespace object for Mindustry unit control operations.

    Supports both legacy function-call syntax:
        ucontrol("move", x, y)
        ucontrol(UnitControl.MOVE, x, y)
    and modern namespace method syntax:
        ucontrol.move(x, y)
        ucontrol.approach(x, y, radius)
        ucontrol.mine(x, y)
        ucontrol.boost(True)
        ucontrol.idle()
    """

    def __call__(self, action: Any, *params: Any) -> None:
        return None

    def idle(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def move(self, x: Any, y: Any) -> None:
        return None

    def approach(self, x: Any, y: Any, radius: Any) -> None:
        return None

    def pathfind(self, x: Any, y: Any) -> None:
        return None

    def auto_pathfind(self) -> None:
        return None

    autoPathfind = auto_pathfind

    def boost(self, enable: Any) -> None:
        return None

    def target(self, x: Any, y: Any, shoot: Any) -> None:
        return None

    def targetp(self, unit: Any, shoot: Any) -> None:
        return None

    def item_drop(self, to: Any, amount: Any) -> None:
        return None

    itemDrop = item_drop

    def item_take(self, from_: Any, item: Any, amount: Any) -> None:
        return None

    itemTake = item_take

    def pay_drop(self) -> None:
        return None

    payDrop = pay_drop

    def pay_take(self, take_units: Any) -> None:
        return None

    payTake = pay_take

    def pay_enter(self) -> None:
        return None

    payEnter = pay_enter

    def mine(self, x: Any, y: Any) -> None:
        return None

    def flag(self, value: Any) -> None:
        return None

    def build(self, x: Any, y: Any, block: Any, rotation: Any, config: Any) -> None:
        return None

    def deconstruct(self, x: Any, y: Any) -> None:
        return None

    def get_block(self, x: Any, y: Any, out_type: Any, out_building: Any, out_floor: Any) -> None:
        return None

    getBlock = get_block

    def within(self, x: Any, y: Any, radius: Any, out_result: Any) -> None:
        return None

    def unbind(self) -> None:
        return None


_rt_ucontrol = _UnitControlCallable()
ucontrol = _rt_ucontrol

class _DrawCallable:
    """Callable namespace object for Mindustry draw operations.

    Supports both legacy function-call syntax:
        draw("line", x1, y1, x2, y2)
        draw(DrawType.LINE, x1, y1, x2, y2)
    and modern namespace method syntax:
        draw.line(x1, y1, x2, y2)
        draw.clear(r=0, g=0, b=0, a=0)
        draw.color(r, g, b, a=255)
        draw.rect(x, y, width, height)
        draw.reset()
    """

    def __call__(self, type_: Any, *params: Any) -> None:
        return None

    def clear(self, r: Any = 0, g: Any = 0, b: Any = 0, a: Any = 0) -> None:
        return None


    def color(self, r: Any, g: Any, b: Any, a: Any = 255) -> None:
        return None

    def col(self, color: Any) -> None:
        return None

    def stroke(self, width: Any) -> None:
        return None

    def line(self, x1: Any, y1: Any, x2: Any, y2: Any) -> None:
        return None

    def rect(self, x: Any, y: Any, width: Any, height: Any) -> None:
        return None

    def line_rect(self, x: Any, y: Any, width: Any, height: Any) -> None:
        return None

    lineRect = line_rect

    def poly(self, x: Any, y: Any, sides: Any, radius: Any, rotation: Any = 0) -> None:
        return None

    def line_poly(self, x: Any, y: Any, sides: Any, radius: Any, rotation: Any = 0) -> None:
        return None

    linePoly = line_poly

    def triangle(self, x1: Any, y1: Any, x2: Any, y2: Any, x3: Any, y3: Any) -> None:
        return None

    def image(self, x: Any, y: Any, image: Any, size: Any = 32, rotation: Any = 0) -> None:
        return None

    def print(self, x: Any, y: Any, align: Any = 0) -> None:
        return None

    def translate(self, x: Any, y: Any) -> None:
        return None

    def scale(self, x: Any, y: Any) -> None:
        return None

    def rotate(self, degrees: Any) -> None:
        return None

    def reset(self) -> None:
        return None

    def flush(self, display: Any) -> None:
        return None


_rt_draw = _DrawCallable()

def _rt_drawflush(display: Any) -> None:
    return None

MAX_TEXT_BUFFER: int = 400
_rt_print_buffer: List[str] = []


def _java_math_round(a: float) -> int:
    """Exact emulation of Java java.lang.Math.round(double a) -> (long)Math.floor(a + 0.5d)."""
    if math.isnan(a):
        return 0
    return math.floor(a + 0.5)


def _utf16_len(s: str) -> int:
    """Return length in UTF-16 code units (matching Java StringBuilder.length())."""
    return len(s.encode("utf-16-le", errors="surrogatepass")) // 2


def _utf16_slice(s: str, max_code_units: int) -> str:
    """Slice string by UTF-16 code units (matching Java StringBuilder.append(str, 0, n))."""
    b = s.encode("utf-16-le", errors="surrogatepass")
    return b[: max_code_units * 2].decode("utf-16-le", errors="surrogatepass")


def _rt_format_print_value(value: Any) -> str:
    """Format a value according to Mindustry Logic LExecutor.PrintI rules.

    References:
    - LExecutor.PrintI.run (Mindustry Java):
        - if value.isobj: toString(value.objval)
        - else: if Math.abs(numval - Math.round(numval)) < 0.00001: Math.round(numval) else: numval
    - LExecutor.PrintI.toString (Mindustry Java):
        - null -> "null"
        - String -> s
        - MappableContent -> content.name
        - Content -> "[content]"
        - Building -> build.block.name
        - Unit -> unit.type.name
        - Enum -> e.name()
        - Team -> team.name
        - other -> "[object]"
    - GlobalVars.java:
        - "false" = 0, "true" = 1 (booleans in Mindustry Logic are numbers 1 and 0)
    - LVar.java:
        - invalid(numval) (NaN or Infinite) -> sets objval = null, isobj = true -> formats as "null"
    """
    if value is None:
        return "null"

    # In Mindustry Logic, booleans true/false are numeric constants 1/0
    if isinstance(value, bool):
        return "1" if value else "0"

    if isinstance(value, int):
        return str(value)

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return "null"
        rounded = _java_math_round(value)
        if abs(value - rounded) < 0.00001:
            return str(rounded)
        return str(value)

    if isinstance(value, str):
        return value

    if isinstance(value, Enum):
        if hasattr(value, "value") and isinstance(value.value, str):
            val_str = value.value
            if val_str.startswith("@"):
                return val_str[1:]
            return val_str
        return value.name

    if hasattr(value, "block") and hasattr(value.block, "name"):
        return str(value.block.name)
    if hasattr(value, "type") and hasattr(value.type, "name"):
        return str(value.type.name)
    if hasattr(value, "name") and isinstance(value.name, str):
        val_name = value.name
        if val_name.startswith("@"):
            return val_name[1:]
        return val_name

    return "[object]"


def _rt_print(value: Any = "") -> None:
    """Append text or a value to the processor print buffer.

    Mindustry engine rules (LExecutor.PrintI):
    1. If exec.textBuffer.length() >= maxTextBuffer (400), return immediately.
       Length is measured in Java UTF-16 code units (char), where non-BMP
       characters (e.g. emojis) count as 2 units.
    2. Convert value according to toString / numeric formatting.
    3. Append value up to remaining capacity: Math.min(length, maxTextBuffer - current_length).
    """
    current_text = "".join(_rt_print_buffer)
    current_len = _utf16_len(current_text)
    if current_len >= MAX_TEXT_BUFFER:
        return None

    str_val = _rt_format_print_value(value)
    val_len = _utf16_len(str_val)
    remaining = MAX_TEXT_BUFFER - current_len
    if val_len > remaining:
        _rt_print_buffer.append(_utf16_slice(str_val, remaining))
    else:
        _rt_print_buffer.append(str_val)
    return None


def _rt_printchar(value: Any = 0) -> None:
    """Append a character to the processor print buffer matching LExecutor.PrintCharI."""
    current_text = "".join(_rt_print_buffer)
    if _utf16_len(current_text) >= MAX_TEXT_BUFFER:
        return None
    if hasattr(value, "emojiChar") and callable(getattr(value, "emojiChar")):
        char = chr(value.emojiChar())
    elif isinstance(value, (int, float)):
        if math.isnan(value) or math.isinf(value):
            char = "\0"
        else:
            try:
                char = chr(int(math.floor(float(value))))
            except (ValueError, OverflowError):
                char = "\0"
    else:
        char = "\0"
    _rt_print_buffer.append(char)
    return None


def _rt_format(value: Any, *values: Any) -> None:
    """Replace placeholders {0}..{9} in the print buffer matching LExecutor.FormatI."""
    all_values = (value,) + values
    for val in all_values:
        buf = "".join(_rt_print_buffer)
        placeholder_index = -1
        placeholder_number = 10

        buf_len = len(buf)
        for i in range(buf_len):
            if buf[i] == "{" and buf_len - i > 2:
                num_char = buf[i + 1]
                if "0" <= num_char <= "9" and buf[i + 2] == "}":
                    digit = ord(num_char) - ord("0")
                    if digit < placeholder_number:
                        placeholder_number = digit
                        placeholder_index = i

        if placeholder_index == -1:
            continue

        rep = _rt_format_print_value(val)
        new_buf = buf[:placeholder_index] + rep + buf[placeholder_index + 3:]
        if _utf16_len(new_buf) > MAX_TEXT_BUFFER:
            new_buf = _utf16_slice(new_buf, MAX_TEXT_BUFFER)
        _rt_print_buffer.clear()
        _rt_print_buffer.append(new_buf)
    return None


def _rt_printflush(message: Any = None) -> None:
    """Flush the print buffer to a message block and clear the buffer.

    Mindustry engine rules (LExecutor.PrintFlushI):
    1. If target is a printable building (e.g. message block) and printable(exec) is true:
       writes textBuffer to target.
    2. exec.textBuffer.setLength(0) is ALWAYS called unconditionally, even if target
       is null, invalid, destroyed, or not a printable building.
    """
    text = "".join(_rt_print_buffer)
    is_printable = True
    if hasattr(message, "printable") and callable(getattr(message, "printable")):
        is_printable = bool(message.printable())
    elif hasattr(message, "is_valid") and not message.is_valid:
        is_printable = False

    if is_printable:
        if hasattr(message, "print") and callable(getattr(message, "print")):
            message.print(text)
        elif hasattr(message, "message"):
            setattr(message, "message", text)
        elif isinstance(message, dict):
            message["message"] = text

    _rt_print_buffer.clear()
    return None


def get_print_buffer() -> str:
    """Return accumulated text in runtime print buffer (useful for testing and simulation)."""
    return "".join(_rt_print_buffer)


def clear_print_buffer() -> None:
    """Clear runtime print buffer."""
    _rt_print_buffer.clear()

def _rt_read(*args: Any) -> Any:
    return 0

def _rt_write(input_: Any, cell: Any, address: Any) -> None:
    return None

def _rt_wait(seconds: Any = 0.5) -> None:
    return None

def _rt_noop() -> None:
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

class LocateResult(NamedTuple):
    """Runtime mock result for ulocate building/spawn/damaged queries (4-tuple: x, y, found, building).

    NOTE: This is a static stub for local Python execution, type linting, and AST validation.
    It does NOT connect to or query a live Mindustry instance.
    """
    x: float = 0.0
    y: float = 0.0
    found: int = 0
    building: Any = None


class OreLocateResult(NamedTuple):
    """Runtime mock result for ulocate ore queries (3-tuple: x, y, found).

    NOTE: This is a static stub for local Python execution, type linting, and AST validation.
    It does NOT connect to or query a live Mindustry instance.
    """
    x: float = 0.0
    y: float = 0.0
    found: int = 0


class ColorChannels(NamedTuple):
    """Runtime mock result for unpackcolor queries (4-tuple: r, g, b, a).

    Field order matches the Mindustry `unpackcolor r g b a value` operand order
    enforced by LExecutor.UnpackColorI.

    NOTE: This is a static stub for local Python execution, type linting, and AST validation.
    It does NOT decode live packed colors; Mindustry channels are returned as 0.0.
    """
    r: float = 0.0
    g: float = 0.0
    b: float = 0.0
    a: float = 0.0


class _UnitLocateCallable:
    """Callable namespace object for Mindustry unit locate operations.

    NOTE: Runtime methods are local static stubs/mocks for syntax validation,
    AST compilation, and IDE autocompletion. They do not connect to or query
    a live Mindustry instance.

    Supports both modern Python tuple unpacking:
        core_x, core_y, found_core, core_build = ulocate.building("core", False)
        ore_x, ore_y, found_ore = ulocate.ore("@copper")
        spawn_x, spawn_y, found_spawn, spawn_build = ulocate.spawn()
        dmg_x, dmg_y, found_dmg, dmg_build = ulocate.damaged()

    and positional statement syntax:
        ulocate.building("core", False, core_x, core_y, found_core, core_build)
        ulocate.ore("@copper", ore_x, ore_y, found_ore)
        ulocate.spawn(spawn_x, spawn_y, found_spawn, spawn_build)
        ulocate.damaged(dmg_x, dmg_y, found_dmg, dmg_build)
        ulocate("ore", "core", "true", "@copper", outX, outY, found, building)
    """

    def __call__(self, locate: Any, *params: Any) -> Any:
        if len(params) >= 7:
            return None
        return LocateResult(0.0, 0.0, 0, None)

    def ore(self, ore: Any, *args: Any) -> Any:
        if args:
            return None
        return OreLocateResult(0.0, 0.0, 0)

    def building(self, group: Any, enemy: Any, *args: Any) -> Any:
        if args:
            return None
        return LocateResult(0.0, 0.0, 0, None)

    def spawn(self, *args: Any) -> Any:
        if args:
            return None
        return LocateResult(0.0, 0.0, 0, None)

    def damaged(self, *args: Any) -> Any:
        if args:
            return None
        return LocateResult(0.0, 0.0, 0, None)


_rt_ulocate = _UnitLocateCallable()
ulocate = _rt_ulocate

def _rt_lookup(*args: Any) -> Any:
    return 0

def _rt_packcolor(*args: Any) -> Any:
    return 0

def _rt_unpackcolor(*args: Any) -> Any:
    """Runtime stub for the Mindustry Logic unpackcolor opcode.

    Mirrors the compiler's dual call conventions by argument count only (no bytecode
    introspection): the single-argument expression form returns a ColorChannels 4-tuple
    for Pythonic unpacking (`r, g, b, a = unpackcolor(color)`), while the five-argument
    statement form is a no-op because plain Python cannot write through call arguments.
    """
    if len(args) == 1:
        return ColorChannels()
    return None

def _rt_select(*args: Any) -> Any:
    """Runtime stub for Mindustry Logic select opcode."""
    if len(args) == 3:
        cond, a, b = args
        return a if (cond not in (0, False, None, "0", "false", "null")) else b
    elif len(args) == 4:
        dest, cond, a, b = args
        return a if (cond not in (0, False, None, "0", "false", "null")) else b
    elif len(args) == 5:
        cond_op, comp0, comp1, a, b = args
        return a if _eval_condition_op(cond_op, comp0, comp1) else b
    elif len(args) == 6:
        dest, cond_op, comp0, comp1, a, b = args
        return a if _eval_condition_op(cond_op, comp0, comp1) else b
    return 0

def _parse_mindustry_val(val: Any) -> Tuple[bool, float, Any]:
    """Parse an operand into (is_num, numval, objval) matching Mindustry LVar/LAssembler."""
    if isinstance(val, bool):
        return True, 1.0 if val else 0.0, val
    if isinstance(val, (int, float)):
        return True, float(val), val
    if val is None or val == "null":
        return False, 0.0, None
    if isinstance(val, str):
        # Quoted strings are explicitly objects
        if val.startswith('"') and val.endswith('"'):
            return False, 0.0, val[1:-1]
        # Mindustry LAssembler parses unquoted numbers as numeric doubles
        try:
            d = float(val)
            return True, d, val
        except (ValueError, TypeError):
            pass
        return False, 0.0, val
    return False, 0.0, val


def _eval_condition_op(op: Any, a: Any, b: Any) -> bool:
    op_str = getattr(op, "name", str(op))
    if op_str == "always":
        return True

    is_num_a, na, oa = _parse_mindustry_val(a)
    is_num_b, nb, ob = _parse_mindustry_val(b)

    if op_str == "strictEqual":
        if is_num_a != is_num_b:
            return False
        if is_num_a:
            return na == nb
        return (type(oa) is type(ob)) and (oa == ob)

    both_obj = (not is_num_a) and (not is_num_b)
    if op_str == "equal":
        return (oa == ob) if both_obj else (abs(na - nb) < 0.000001)
    elif op_str == "notEqual":
        return (oa != ob) if both_obj else (abs(na - nb) >= 0.000001)
    elif op_str == "lessThan":
        return na < nb
    elif op_str == "lessThanEq":
        return na <= nb
    elif op_str == "greaterThan":
        return na > nb
    elif op_str == "greaterThanEq":
        return na >= nb
    return False

def _rt_getlink(*args: Any) -> Any:
    return 0

def _rt_setrate(ipt: Any = 60) -> None:
    return None

def _rt_raw(value: Any) -> str:
    return str(value)

def _rt_query(*args: Any) -> None:
    return None

def _rt_getblock(*args: Any) -> Any:
    return None

def _rt_setblock(*args: Any) -> None:
    return None

def _rt_spawn(*args: Any) -> Any:
    return None

def _rt_bullet(*args: Any) -> Any:
    return None

def _rt_status(*args: Any) -> None:
    return None

def _rt_explosion(*args: Any) -> None:
    return None

def _rt_getflag(*args: Any) -> Any:
    return None

def _rt_setflag(*args: Any) -> None:
    return None

def _rt_setprop(*args: Any) -> None:
    return None

def _rt_fetch(*args: Any) -> Any:
    return None

def _rt_sync(*args: Any) -> None:
    return None

def _rt_setrule(*args: Any) -> None:
    return None

def _rt_weathersense(*args: Any) -> Any:
    return 0

def _rt_weatherset(*args: Any) -> None:
    return None

def _rt_spawnwave(*args: Any) -> None:
    return None

def _rt_effect(*args: Any) -> None:
    return None

def _rt_message(*args: Any) -> Any:
    return 1


class _CutsceneCallable:
    """Callable namespace object for Mindustry cutscene operations.

    Supports both direct function-call syntax:
        cutscene(action, p1, p2, p3, p4)
        result = cutscene(action)
    and modern namespace method syntax:
        cutscene.pan(x, y, speed=0.06)
        cutscene.zoom(level)
        cutscene.stop()
        cutscene.shake(amount, duration)
        result = cutscene.active()
        result = cutscene.get_hud()
        cutscene.set_hud(shown)
    """

    def __call__(self, action: Any, p1: Any = 0, p2: Any = 0, p3: Any = 0, p4: Any = 0) -> Any:
        return 0

    def active(self, out_result: Any = None) -> Any:
        return 0

    def pan(self, x: Any, y: Any, speed: Any = 0.06) -> None:
        return None

    def zoom(self, level: Any) -> None:
        return None

    def stop(self) -> None:
        return None

    def shake(self, amount: Any, duration: Any) -> None:
        return None

    def get_hud(self, out_result: Any = None) -> Any:
        return 0

    def getHud(self, out_result: Any = None) -> Any:
        return 0

    def set_hud(self, shown: Any) -> None:
        return None

    def setHud(self, shown: Any) -> None:
        return None


_rt_cutscene = _CutsceneCallable()
cutscene = _rt_cutscene

def _rt_playsound(*args: Any) -> None:
    return None

def _rt_playmusic(*args: Any) -> None:
    return None

def _rt_makemarker(*args: Any) -> None:
    return None

def _rt_setmarker(*args: Any) -> None:
    return None

def _rt_localeprint(*args: Any) -> None:
    return None

def _rt_clientdata(*args: Any) -> None:
    return None


class _SoundCallable:
    """Callable namespace object for Mindustry sound operations."""

    def __call__(self, positional: Any, id: Any, volume: Any = 1, pitch: Any = 1, pan: Any = 0, x: Any = 0, y: Any = 0, limit: Any = True) -> None:
        return None

    def play(self, id: Any, volume: Any = 1, pitch: Any = 1, pan: Any = 0, limit: Any = True) -> None:
        return None

    def play_at(self, id: Any, x: Any, y: Any, volume: Any = 1, pitch: Any = 1, limit: Any = True) -> None:
        return None

    playAt = play_at


class _MusicCallable:
    """Callable namespace object for Mindustry music operations."""

    def __call__(self, name: Any, interrupt: Any = True) -> None:
        return None

    def play(self, name: Any, interrupt: Any = True) -> None:
        return None

    def stop(self) -> None:
        return None


class _MarkerCallable:
    """Callable namespace object for Mindustry marker operations."""

    def make(self, type: Any, id: Any, x: Any, y: Any, replace: Any = True) -> None:
        return None

    def remove(self, id: Any) -> None:
        return None

    def world(self, id: Any, enabled: Any = True) -> None:
        return None

    def minimap(self, id: Any, enabled: Any = True) -> None:
        return None

    def light(self, id: Any, enabled: Any = True) -> None:
        return None

    def autoscale(self, id: Any, enabled: Any = True) -> None:
        return None

    def pos(self, id: Any, x: Any, y: Any) -> None:
        return None

    def end_pos(self, id: Any, x: Any, y: Any) -> None:
        return None

    endPos = end_pos

    def draw_layer(self, id: Any, layer: Any) -> None:
        return None

    drawLayer = draw_layer

    def color(self, id: Any, color: Any) -> None:
        return None

    def radius(self, id: Any, radius: Any) -> None:
        return None

    def stroke(self, id: Any, stroke: Any) -> None:
        return None

    def outline(self, id: Any, outline: Any = True) -> None:
        return None

    def rotation(self, id: Any, rotation: Any) -> None:
        return None

    def shape(self, id: Any, sides: Any, fill: Any = 1, outline: Any = 1) -> None:
        return None

    def arc(self, id: Any, start: Any, end: Any) -> None:
        return None

    def flush_text(self, id: Any, fetch: Any = False) -> None:
        return None

    flushText = flush_text

    def font_size(self, id: Any, size: Any) -> None:
        return None

    fontSize = font_size

    def text_height(self, id: Any, height: Any) -> None:
        return None

    textHeight = text_height

    def text_align(self, id: Any, align: Any) -> None:
        return None

    textAlign = text_align

    def line_align(self, id: Any, align: Any) -> None:
        return None

    lineAlign = line_align

    def label_flags(self, id: Any, background: Any = 1, outline: Any = 1) -> None:
        return None

    labelFlags = label_flags

    def texture(self, id: Any, name: Any, print_flush: Any = False) -> None:
        return None

    def texture_size(self, id: Any, width: Any, height: Any) -> None:
        return None

    textureSize = texture_size

    def posi(self, id: Any, index: Any, x: Any, y: Any) -> None:
        return None

    def uvi(self, id: Any, index: Any, x: Any, y: Any) -> None:
        return None

    def colori(self, id: Any, index: Any, color: Any) -> None:
        return None


_rt_sound = _SoundCallable()
sound = _rt_sound
_rt_music = _MusicCallable()
music = _rt_music
_rt_marker = _MarkerCallable()
marker = _rt_marker


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
        name="setrate",
        summary="Set processor execution speed in instructions per tick (IPT)",
        docstring=(
            "Set processor execution speed in instructions per tick (IPT).\n\n"
            "Args:\n"
            "    ipt: Target instructions per tick rate (capped by processor max rate, e.g. 1000)."
        ),
        min_args=1,
        max_args=1,
        valid_arg_counts=(1,),
        signatures=[
            IntrinsicSignature(
                params=[IntrinsicParam("ipt", "Any")],
                return_type="None",
                docstring="Set processor execution rate to ipt instructions per tick.",
            ),
        ],
        runtime_fn=_rt_setrate,
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
            "Note: Mindustry Logic's print does NOT append a newline character.\n"
            "Multiple consecutive print() calls concatenate directly into a single string.\n"
            "To insert a newline, explicitly include '\\n' in the text string (e.g. print('Line 1\\n')).\n\n"
            "The processor print buffer has a maximum capacity of 400 characters (maxTextBuffer = 400).\n"
            "If the buffer is already full (>= 400 characters), subsequent calls are ignored.\n"
            "If a string exceeds remaining capacity, it is truncated to fit.\n"
            "Numbers within 0.00001 of an integer format as integers; null/NaN/Inf format as 'null'.\n\n"
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
                docstring=(
                    "Append value to print buffer without trailing newline.\n"
                    "Buffer capacity is 400 chars; consecutive calls concatenate directly."
                ),
            ),
        ],
        runtime_fn=_rt_print,
    ),
    IntrinsicDef(
        name="printchar",
        summary="Append character to the processor print buffer by code or emoji code",
        docstring=(
            "Append a character to the processor print buffer matching LExecutor.PrintCharI.\n\n"
            "If value is an unlockable content with emoji, appends its emoji character.\n"
            "Otherwise, appends chr(floor(value)).\n\n"
            "Args:\n"
            "    value: Character code (numeric) or content with emoji."
        ),
        min_args=1,
        max_args=1,
        valid_arg_counts=(1,),
        signatures=[
            IntrinsicSignature(
                params=[IntrinsicParam("value", "Any")],
                return_type="None",
                docstring="Append character to print buffer.",
            ),
        ],
        runtime_fn=_rt_printchar,
    ),
    IntrinsicDef(
        name="format",
        summary="Replace placeholders {0}..{9} in print buffer with values",
        docstring=(
            "Replace placeholders {0}..{9} in the print buffer matching LExecutor.FormatI.\n\n"
            "Supports single or multiple arguments:\n"
            "    format(value)\n"
            "    format(wScr, hScr)\n\n"
            "Args:\n"
            "    value: First value to replace the next placeholder with.\n"
            "    values: Additional values to replace subsequent placeholders."
        ),
        min_args=1,
        max_args=-1,
        valid_arg_counts=(),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("value", "Any"),
                    IntrinsicParam("*values", "Any"),
                ],
                return_type="None",
                docstring="Replace placeholders {0}..{9} in print buffer with values.",
            ),
        ],
        runtime_fn=_rt_format,
    ),
    IntrinsicDef(
        name="printflush",
        summary="Flush the print buffer to a message block",
        docstring=(
            "Flush the print buffer to a message block and clear the buffer.\n\n"
            "If target is a valid printable block (e.g. message1), text is displayed on the block.\n"
            "The processor print buffer is always cleared unconditionally to length 0.\n\n"
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
                docstring="Flush print buffer to message block and clear the buffer unconditionally.",
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
        name="noop",
        summary="No-operation instruction (occupies 1 instruction slot and does nothing)",
        docstring="No-operation instruction (occupies 1 instruction slot, executes nothing).",
        min_args=0,
        max_args=0,
        valid_arg_counts=(0,),
        signatures=[
            IntrinsicSignature(
                params=[],
                return_type="None",
                docstring="No-operation instruction (occupies 1 instruction slot, executes nothing).",
            ),
        ],
        runtime_fn=_rt_noop,
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
        name="unpackcolor",
        summary="Unpack double-precision color into r, g, b, a components in [0, 1]",
        docstring=(
            "Unpack a 64-bit double color into 4 target variables r, g, b, a.\n\n"
            "Supported call conventions:\n"
            "    1. Tuple unpacking form: r, g, b, a = unpackcolor(value)\n"
            "    2. Statement form:        unpackcolor(r, g, b, a, value)\n\n"
            "Both forms lower to the single Mindustry `unpackcolor r g b a value`\n"
            "instruction. Tuple unpacking requires exactly 4 target variables.\n\n"
            "Args:\n"
            "    r: Target variable for red channel.\n"
            "    g: Target variable for green channel.\n"
            "    b: Target variable for blue channel.\n"
            "    a: Target variable for alpha channel.\n"
            "    value: 64-bit packed double color operand."
        ),
        min_args=1,
        max_args=5,
        valid_arg_counts=(1, 5),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("value", "Any"),
                ],
                return_type="ColorChannels",
                docstring="Unpack a packed color value and return its RGBA channels (tuple unpacking form).",
            ),
            IntrinsicSignature(
                params=[
                    IntrinsicParam("r", "Any"),
                    IntrinsicParam("g", "Any"),
                    IntrinsicParam("b", "Any"),
                    IntrinsicParam("a", "Any"),
                    IntrinsicParam("value", "Any"),
                ],
                return_type="None",
                docstring="Unpack packed color value into r, g, b, a variables (statement form).",
            ),
        ],
        runtime_fn=_rt_unpackcolor,
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
            "    index: 0-indexed link number (in expression form: block = getlink(i)).\n"
            "    dest: Target variable (in statement form: getlink(dest, i))."
        ),
        min_args=1,
        max_args=2,
        valid_arg_counts=(1, 2),
        signatures=[
            IntrinsicSignature(
                params=[IntrinsicParam("index", "Any")],
                return_type="Any",
                docstring="Get linked block by index and return it (expression form: block = getlink(i)).",
            ),
            IntrinsicSignature(
                params=[
                    IntrinsicParam("dest", "Any"),
                    IntrinsicParam("index", "Any"),
                ],
                return_type="Any",
                docstring="Get linked block by index into dest variable (statement form: getlink(dest, i)).",
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
    IntrinsicDef(
        name="min",
        summary="Mathematical minimum of two values (compiles to MLog op min)",
        docstring=(
            "Compute the minimum of two values without compile-time evaluation.\n\n"
            "Args:\n"
            "    a: First operand.\n"
            "    b: Second operand.\n\n"
            "Returns:\n"
            "    The smaller of a and b."
        ),
        min_args=2,
        max_args=2,
        valid_arg_counts=(2,),
        signatures=[
            IntrinsicSignature(
                params=[IntrinsicParam("a", "Any"), IntrinsicParam("b", "Any")],
                return_type="Any",
                docstring="Compute min(a, b) via MLog 'op min'.",
            ),
        ],
        runtime_fn=_rt_min,
        has_assignment_form=True,
    ),
    IntrinsicDef(
        name="max",
        summary="Mathematical maximum of two values (compiles to MLog op max)",
        docstring=(
            "Compute the maximum of two values without compile-time evaluation.\n\n"
            "Args:\n"
            "    a: First operand.\n"
            "    b: Second operand.\n\n"
            "Returns:\n"
            "    The larger of a and b."
        ),
        min_args=2,
        max_args=2,
        valid_arg_counts=(2,),
        signatures=[
            IntrinsicSignature(
                params=[IntrinsicParam("a", "Any"), IntrinsicParam("b", "Any")],
                return_type="Any",
                docstring="Compute max(a, b) via MLog 'op max'.",
            ),
        ],
        runtime_fn=_rt_max,
        has_assignment_form=True,
    ),
    IntrinsicDef(
        name="select",
        summary="Conditional selection opcode (select result condition comp0 comp1 a b)",
        docstring=(
            "Conditionally select between two values based on a condition comparison.\n\n"
            "Supported call conventions:\n"
            "    1. Expression form (full):       result = select(cond_op, comp0, comp1, a, b)\n"
            "    2. Statement form (full):        select(dest, cond_op, comp0, comp1, a, b)\n"
            "    3. Expression form (simplified): result = select(cond, a, b)\n"
            "    4. Statement form (simplified):  select(dest, cond, a, b)\n\n"
            "Args:\n"
            "    dest: Target variable (in statement form).\n"
            "    cond_op: Condition operator ('equal', 'notEqual', 'lessThan', etc.).\n"
            "    comp0: First operand of condition comparison.\n"
            "    comp1: Second operand of condition comparison.\n"
            "    a: Value selected when condition is true.\n"
            "    b: Value selected when condition is false."
        ),
        min_args=3,
        max_args=6,
        valid_arg_counts=(3, 4, 5, 6),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("cond", "Any"),
                    IntrinsicParam("a", "Any"),
                    IntrinsicParam("b", "Any"),
                ],
                return_type="Any",
                docstring="Select between a and b based on truthiness of cond.",
            ),
            IntrinsicSignature(
                params=[
                    IntrinsicParam("dest", "Any"),
                    IntrinsicParam("cond", "Any"),
                    IntrinsicParam("a", "Any"),
                    IntrinsicParam("b", "Any"),
                ],
                return_type="None",
                docstring="Select between a and b into dest based on truthiness of cond.",
            ),
            IntrinsicSignature(
                params=[
                    IntrinsicParam("cond_op", "Union[Condition, str]"),
                    IntrinsicParam("comp0", "Any"),
                    IntrinsicParam("comp1", "Any"),
                    IntrinsicParam("a", "Any"),
                    IntrinsicParam("b", "Any"),
                ],
                return_type="Any",
                docstring="Select between a and b based on cond_op comparison between comp0 and comp1.",
            ),
            IntrinsicSignature(
                params=[
                    IntrinsicParam("dest", "Any"),
                    IntrinsicParam("cond_op", "Union[Condition, str]"),
                    IntrinsicParam("comp0", "Any"),
                    IntrinsicParam("comp1", "Any"),
                    IntrinsicParam("a", "Any"),
                    IntrinsicParam("b", "Any"),
                ],
                return_type="None",
                docstring="Select between a and b into dest based on cond_op comparison between comp0 and comp1.",
            ),
        ],
        runtime_fn=_rt_select,
        has_assignment_form=True,
    ),
    IntrinsicDef(
        name="query",
        summary="Query units or buildings in a specified spatial area (query shape type team x y w h)",
        docstring=(
            "Queries units or buildings in a specified spatial area.\n"
            "Results are outputted into @queries (can be read via read instruction or measured via sensor @size).\n\n"
            "Args:\n"
            "    shape: Spatial shape ('circle' or 'rect', or QueryShape enum).\n"
            "    type_: Target type ('unit' or 'building', or QueryType enum).\n"
            "    team: Target team (Teams enum, team string, or 'null' for all teams).\n"
            "    x: Center X coordinate in world/tile units.\n"
            "    y: Center Y coordinate in world/tile units.\n"
            "    w: Radius (circle) or Width (rect).\n"
            "    h: Height (rect) or unused (circle)."
        ),
        min_args=7,
        max_args=7,
        valid_arg_counts=(7,),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("shape", "Union[QueryShape, str]"),
                    IntrinsicParam("type_", "Union[QueryType, str]"),
                    IntrinsicParam("team", "Any"),
                    IntrinsicParam("x", "Any"),
                    IntrinsicParam("y", "Any"),
                    IntrinsicParam("w", "Any"),
                    IntrinsicParam("h", "Any"),
                ],
                return_type="None",
                docstring="Query units/buildings in specified area and populate @queries.",
            ),
        ],
        runtime_fn=_rt_query,
        has_assignment_form=False,
    ),
    IntrinsicDef(
        name="getblock",
        summary="Get block, floor, ore, or building at coordinates (getblock layer result x y)",
        docstring=(
            "Queries the block, floor, ore, or building at specified map tile coordinates.\n\n"
            "Args:\n"
            "    layer: Target layer ('floor', 'ore', 'block', or 'building', or TileLayer enum).\n"
            "    result: Variable name to store query result (in statement form).\n"
            "    x: Map tile X coordinate.\n"
            "    y: Map tile Y coordinate."
        ),
        min_args=3,
        max_args=4,
        valid_arg_counts=(3, 4),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("layer", "Union[TileLayer, str]"),
                    IntrinsicParam("x", "Any"),
                    IntrinsicParam("y", "Any"),
                ],
                return_type="Any",
                docstring="Get block/tile at coordinates into target variable.",
            ),
            IntrinsicSignature(
                params=[
                    IntrinsicParam("layer", "Union[TileLayer, str]"),
                    IntrinsicParam("result", "Any"),
                    IntrinsicParam("x", "Any"),
                    IntrinsicParam("y", "Any"),
                ],
                return_type="None",
                docstring="Get block/tile at coordinates into specified result variable.",
            ),
        ],
        runtime_fn=_rt_getblock,
        has_assignment_form=True,
    ),
    IntrinsicDef(
        name="setblock",
        summary="Set block, floor, or ore at coordinates (setblock layer block x y team rotation)",
        docstring=(
            "Sets the block, floor, or ore at specified map tile coordinates.\n\n"
            "Args:\n"
            "    layer: Target layer ('floor', 'ore', or 'block', or TileLayer enum).\n"
            "    block: Target block/floor content (e.g. '@copper-wall', '@dirt', '@air').\n"
            "    x: Map tile X coordinate.\n"
            "    y: Map tile Y coordinate.\n"
            "    team: Target team (optional, defaults to @derelict).\n"
            "    rotation: Block rotation 0..3 (optional, defaults to 0)."
        ),
        min_args=4,
        max_args=6,
        valid_arg_counts=(4, 5, 6),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("layer", "Union[TileLayer, str]"),
                    IntrinsicParam("block", "Any"),
                    IntrinsicParam("x", "Any"),
                    IntrinsicParam("y", "Any"),
                    IntrinsicParam("team", "Any", default='"@derelict"'),
                    IntrinsicParam("rotation", "Any", default="0"),
                ],
                return_type="None",
                docstring="Set block/floor/ore at specified coordinates.",
            ),
        ],
        runtime_fn=_rt_setblock,
        has_assignment_form=False,
    ),
    IntrinsicDef(
        name="spawn",
        summary="Spawn a unit (spawn type x y rotation team result effect)",
        docstring=(
            "Spawns a unit of the specified type at map coordinates with team and rotation.\n\n"
            "Args:\n"
            "    type: Unit type token (e.g. Units.DAGGER or '@dagger').\n"
            "    x: Map tile X coordinate.\n"
            "    y: Map tile Y coordinate.\n"
            "    rotation: Unit facing rotation in degrees.\n"
            "    team: Unit team (Teams enum or team string).\n"
            "    result: Variable name to store spawned unit (in statement form).\n"
            "    effect: Trigger spawn visual effect (0 or 1, default 0)."
        ),
        min_args=5,
        max_args=7,
        valid_arg_counts=(5, 6, 7),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("type", "Union[Units, str]"),
                    IntrinsicParam("x", "Any"),
                    IntrinsicParam("y", "Any"),
                    IntrinsicParam("rotation", "Any"),
                    IntrinsicParam("team", "Union[Teams, str]"),
                    IntrinsicParam("effect", "Any", default="0"),
                ],
                return_type="Any",
                docstring="Spawn a unit and assign to variable.",
            ),
            IntrinsicSignature(
                params=[
                    IntrinsicParam("type", "Union[Units, str]"),
                    IntrinsicParam("x", "Any"),
                    IntrinsicParam("y", "Any"),
                    IntrinsicParam("rotation", "Any"),
                    IntrinsicParam("team", "Union[Teams, str]"),
                    IntrinsicParam("result", "Any"),
                    IntrinsicParam("effect", "Any", default="0"),
                ],
                return_type="None",
                docstring="Spawn a unit into specified result variable.",
            ),
        ],
        runtime_fn=_rt_spawn,
        has_assignment_form=True,
    ),
    IntrinsicDef(
        name="bullet",
        summary="Create a bullet (bullet result from index x y rotation team owner damage velocityScl lifeScl aimX aimY)",
        docstring=(
            "Creates a bullet entity originating from a unit weapon or turret ammo type.\n\n"
            "Args:\n"
            "    result: Variable to store created bullet.\n"
            "    from_: Unit type (e.g. Units.DAGGER) or Turret block (e.g. '@duo').\n"
            "    index: Weapon index (0..) or ammo item content (e.g. Items.COPPER).\n"
            "    x: Map tile X coordinate.\n"
            "    y: Map tile Y coordinate.\n"
            "    rotation: Bullet firing angle in degrees.\n"
            "    team: Bullet team (Teams enum or team string).\n"
            "    owner: Bullet owner entity or null (default 'null').\n"
            "    damage: Explicit damage override (-1 for default, default -1).\n"
            "    velocityScl: Velocity multiplier (default 1).\n"
            "    lifeScl: Lifetime multiplier (default 1).\n"
            "    aimX: Aim target X coordinate (-1 for none, default -1).\n"
            "    aimY: Aim target Y coordinate (-1 for none, default -1)."
        ),
        min_args=6,
        max_args=13,
        valid_arg_counts=(6, 7, 8, 9, 10, 11, 12, 13),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("from_", "Any"),
                    IntrinsicParam("index", "Any"),
                    IntrinsicParam("x", "Any"),
                    IntrinsicParam("y", "Any"),
                    IntrinsicParam("rotation", "Any"),
                    IntrinsicParam("team", "Union[Teams, str]"),
                    IntrinsicParam("owner", "Any", default='"null"'),
                    IntrinsicParam("damage", "Any", default="-1"),
                    IntrinsicParam("velocityScl", "Any", default="1"),
                    IntrinsicParam("lifeScl", "Any", default="1"),
                    IntrinsicParam("aimX", "Any", default="-1"),
                    IntrinsicParam("aimY", "Any", default="-1"),
                ],
                return_type="Any",
                docstring="Create a bullet and assign to variable.",
            ),
            IntrinsicSignature(
                params=[
                    IntrinsicParam("result", "Any"),
                    IntrinsicParam("from_", "Any"),
                    IntrinsicParam("index", "Any"),
                    IntrinsicParam("x", "Any"),
                    IntrinsicParam("y", "Any"),
                    IntrinsicParam("rotation", "Any"),
                    IntrinsicParam("team", "Union[Teams, str]"),
                    IntrinsicParam("owner", "Any", default='"null"'),
                    IntrinsicParam("damage", "Any", default="-1"),
                    IntrinsicParam("velocityScl", "Any", default="1"),
                    IntrinsicParam("lifeScl", "Any", default="1"),
                    IntrinsicParam("aimX", "Any", default="-1"),
                    IntrinsicParam("aimY", "Any", default="-1"),
                ],
                return_type="None",
                docstring="Create a bullet into specified result variable.",
            ),
        ],
        runtime_fn=_rt_bullet,
        has_assignment_form=True,
    ),
    IntrinsicDef(
        name="status",
        summary="Apply or clear status effect on a unit (status clear effect unit duration)",
        docstring=(
            "Applies or clears a status effect on the target unit.\n\n"
            "Args:\n"
            "    clear: 1/True to unapply/clear, 0/False to apply.\n"
            "    effect: Status effect token (StatusEffects enum or string, e.g. StatusEffects.BURNING).\n"
            "    unit: Target unit variable.\n"
            "    duration: Effect duration in seconds (default 0)."
        ),
        min_args=3,
        max_args=4,
        valid_arg_counts=(3, 4),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("clear", "Any"),
                    IntrinsicParam("effect", "Union[StatusEffects, str]"),
                    IntrinsicParam("unit", "Any"),
                    IntrinsicParam("duration", "Any", default="0"),
                ],
                return_type="None",
                docstring="Apply or clear status effect on unit.",
            ),
        ],
        runtime_fn=_rt_status,
        has_assignment_form=False,
    ),
    IntrinsicDef(
        name="explosion",
        summary="Trigger a logic explosion (explosion team x y radius damage air ground pierce effect)",
        docstring=(
            "Creates an explosion dealing damage to enemy entities within radius.\n\n"
            "Args:\n"
            "    team: Team initiating explosion (friendly units/buildings take no damage).\n"
            "    x: Map tile X coordinate.\n"
            "    y: Map tile Y coordinate.\n"
            "    radius: Blast radius in tiles (max 100).\n"
            "    damage: Maximum blast damage at epicenter (damage < 0 ignored).\n"
            "    air: Damage flying targets (1 or 0, default 1).\n"
            "    ground: Damage ground targets (1 or 0, default 1).\n"
            "    pierce: Damage pierces armor/shields (1 or 0, default 0).\n"
            "    effect: Trigger explosion visual effect (1 or 0, default 1)."
        ),
        min_args=5,
        max_args=9,
        valid_arg_counts=(5, 6, 7, 8, 9),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("team", "Union[Teams, str]"),
                    IntrinsicParam("x", "Any"),
                    IntrinsicParam("y", "Any"),
                    IntrinsicParam("radius", "Any"),
                    IntrinsicParam("damage", "Any"),
                    IntrinsicParam("air", "Any", default="1"),
                    IntrinsicParam("ground", "Any", default="1"),
                    IntrinsicParam("pierce", "Any", default="0"),
                    IntrinsicParam("effect", "Any", default="1"),
                ],
                return_type="None",
                docstring="Trigger logic explosion at coordinates.",
            ),
        ],
        runtime_fn=_rt_explosion,
        has_assignment_form=False,
    ),
    IntrinsicDef(
        name="getflag",
        summary="Check if an objective flag is set in world rules (getflag result flag)",
        docstring=(
            "Queries whether the specified string flag is present in world objective flags.\n"
            "Returns 1 (true) or 0 (false). If flag operand is not a string, returns null.\n\n"
            "Supported call conventions:\n"
            "    1. Expression form: is_set = getflag(flag)\n"
            "    2. Statement form:  getflag(result, flag)\n\n"
            "Args:\n"
            "    flag: Flag name string (e.g. 'flag1' or 'sector_complete').\n"
            "    result: Variable name to receive the boolean result (in statement form)."
        ),
        min_args=1,
        max_args=2,
        valid_arg_counts=(1, 2),
        signatures=[
            IntrinsicSignature(
                params=[IntrinsicParam("flag", "Any")],
                return_type="Any",
                docstring="Check if objective flag is set and return 1 or 0 (expression form: res = getflag(flag)).",
            ),
            IntrinsicSignature(
                params=[IntrinsicParam("result", "Any"), IntrinsicParam("flag", "Any")],
                return_type="None",
                docstring="Check if objective flag is set into result variable (statement form: getflag(result, flag)).",
            ),
        ],
        runtime_fn=_rt_getflag,
        has_assignment_form=True,
    ),
    IntrinsicDef(
        name="setflag",
        summary="Set or unset an objective flag in world rules (setflag flag value)",
        docstring=(
            "Adds or removes an objective flag from world rules.\n"
            "If value evaluates to true (1), the flag is added; if false (0), the flag is removed.\n\n"
            "Args:\n"
            "    flag: Flag name string (e.g. 'flag1' or 'sector_complete').\n"
            "    value: Boolean truth value (1/True to add, 0/False to remove)."
        ),
        min_args=2,
        max_args=2,
        valid_arg_counts=(2,),
        signatures=[
            IntrinsicSignature(
                params=[IntrinsicParam("flag", "Any"), IntrinsicParam("value", "Any")],
                return_type="None",
                docstring="Set or unset an objective flag.",
            ),
        ],
        runtime_fn=_rt_setflag,
        has_assignment_form=False,
    ),
    IntrinsicDef(
        name="setprop",
        summary="Directly set property of unit or building (setprop type of value)",
        docstring=(
            "Directly modifies a property on a target Settable entity (Unit or Building).\n"
            "The property can be an LAccess property (e.g. '@health', '@team', '@shield', '@rotation')\n"
            "or an item/liquid UnlockableContent token (e.g. '@copper', '@water').\n\n"
            "Args:\n"
            "    type: Property token (SensorProperty enum, Item, Liquid, or string token).\n"
            "    of: Target unit or building entity.\n"
            "    value: New value to set."
        ),
        min_args=3,
        max_args=3,
        valid_arg_counts=(3,),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("type", "Any"),
                    IntrinsicParam("of", "Any"),
                    IntrinsicParam("value", "Any"),
                ],
                return_type="None",
                docstring="Set property on target unit or building.",
            ),
        ],
        runtime_fn=_rt_setprop,
        has_assignment_form=False,
    ),
    IntrinsicDef(
        name="fetch",
        summary="Fetch team entities or entity counts (fetch type result team index extra)",
        docstring=(
            "Queries entities or entity counts of a team from the game world.\n"
            "Types supported: unit, unitCount, player, playerCount, core, coreCount, build, buildCount.\n\n"
            "Supported call conventions:\n"
            "    1. Expression form: result = fetch(type, team, index=0, extra=0)\n"
            "    2. Statement form:  fetch(type, result, team, index=0, extra=0)\n\n"
            "Args:\n"
            "    type: FetchType enum or string (e.g. FetchType.CORE, FetchType.UNIT_COUNT).\n"
            "    team: Target team token (e.g. Teams.SHARDED, '@sharded').\n"
            "    index: 0-based collection index for entity queries (default 0).\n"
            "    extra: Content filter (e.g. Units.DAGGER for unit queries, '@conveyor' for build queries, default 0).\n"
            "    result: Variable name to receive output (in statement form)."
        ),
        min_args=2,
        max_args=5,
        valid_arg_counts=(2, 3, 4, 5),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("type", "Union[FetchType, str]"),
                    IntrinsicParam("team", "Union[Teams, str]"),
                    IntrinsicParam("index", "Any", default="0"),
                    IntrinsicParam("extra", "Any", default="0"),
                ],
                return_type="Any",
                docstring="Fetch entity or count and return result (expression form).",
            ),
            IntrinsicSignature(
                params=[
                    IntrinsicParam("type", "Union[FetchType, str]"),
                    IntrinsicParam("result", "Any"),
                    IntrinsicParam("team", "Union[Teams, str]"),
                    IntrinsicParam("index", "Any", default="0"),
                    IntrinsicParam("extra", "Any", default="0"),
                ],
                return_type="None",
                docstring="Fetch entity or count into result variable (statement form).",
            ),
        ],
        runtime_fn=_rt_fetch,
        has_assignment_form=True,
    ),
    IntrinsicDef(
        name="sync",
        summary="Broadcast processor variable state to clients (sync variable)",
        docstring=(
            "Broadcasts a processor variable value to multiplayer clients.\n"
            "Rate-limited by Mindustry engine to 20 syncs per second.\n\n"
            "Args:\n"
            "    variable: Variable name to synchronize."
        ),
        min_args=1,
        max_args=1,
        valid_arg_counts=(1,),
        signatures=[
            IntrinsicSignature(
                params=[IntrinsicParam("variable", "Any")],
                return_type="None",
                docstring="Synchronize variable value to multiplayer clients.",
            ),
        ],
        runtime_fn=_rt_sync,
        has_assignment_form=False,
    ),
    IntrinsicDef(
        name="setrule",
        summary="Modify game or team rules in world processor (setrule rule value p1 p2 p3 p4)",
        docstring=(
            "Modifies world rules or team-specific rules.\n"
            "For global rules (e.g. waveTimer, waves, waveSpacing), modifies rule using value.\n"
            "For team rules (e.g. unitHealth, buildSpeed, unitDamage), p1 is team and value is multiplier.\n"
            "For mapArea, p1=x, p2=y, p3=w, p4=h.\n"
            "For ban/unban, value is block or unit content to ban/unban.\n\n"
            "Args:\n"
            "    rule: LogicRules enum or string (e.g. LogicRules.WAVE_TIMER, LogicRules.UNIT_HEALTH).\n"
            "    value: Value or multiplier for rule.\n"
            "    p1, p2, p3, p4: Additional parameters (team, coordinate, dimension; default 0)."
        ),
        min_args=2,
        max_args=6,
        valid_arg_counts=(2, 3, 4, 5, 6),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("rule", "Union[LogicRules, str]"),
                    IntrinsicParam("value", "Any"),
                    IntrinsicParam("p1", "Any", default="0"),
                    IntrinsicParam("p2", "Any", default="0"),
                    IntrinsicParam("p3", "Any", default="0"),
                    IntrinsicParam("p4", "Any", default="0"),
                ],
                return_type="None",
                docstring="Modify game or team rule.",
            ),
        ],
        runtime_fn=_rt_setrule,
        has_assignment_form=False,
    ),
    IntrinsicDef(
        name="weathersense",
        summary="Sense if a weather event is active in world processor (weathersense to weather)",
        docstring=(
            "Checks if a specific weather event is currently active.\n\n"
            "Supported call conventions:\n"
            "    1. Expression form: is_active = weathersense(weather)\n"
            "    2. Statement form:  weathersense(to, weather)\n\n"
            "Args:\n"
            "    to: Destination variable (in statement form).\n"
            "    weather: Weather type (Weathers enum or token, e.g. Weathers.RAIN, '@snowing')."
        ),
        min_args=1,
        max_args=2,
        valid_arg_counts=(1, 2),
        signatures=[
            IntrinsicSignature(
                params=[IntrinsicParam("weather", "Union[Weathers, str]")],
                return_type="Any",
                docstring="Query whether weather event is active.",
            ),
            IntrinsicSignature(
                params=[
                    IntrinsicParam("to", "Any"),
                    IntrinsicParam("weather", "Union[Weathers, str]"),
                ],
                return_type="None",
                docstring="Query whether weather event is active into destination variable.",
            ),
        ],
        runtime_fn=_rt_weathersense,
        has_assignment_form=True,
    ),
    IntrinsicDef(
        name="weatherset",
        summary="Activate or deactivate a weather event in world processor (weatherset weather state)",
        docstring=(
            "Activates or deactivates a weather event.\n\n"
            "Args:\n"
            "    weather: Weather type (Weathers enum or token, e.g. Weathers.RAIN, '@snowing').\n"
            "    state: Target state (1/True to activate, 0/False to deactivate, default 1)."
        ),
        min_args=1,
        max_args=2,
        valid_arg_counts=(1, 2),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("weather", "Union[Weathers, str]"),
                    IntrinsicParam("state", "Any", default="1"),
                ],
                return_type="None",
                docstring="Set weather event activation state.",
            ),
        ],
        runtime_fn=_rt_weatherset,
        has_assignment_form=False,
    ),
    IntrinsicDef(
        name="spawnwave",
        summary="Spawn an enemy wave or advance to next wave (spawnwave x y natural)",
        docstring=(
            "Spawns an enemy wave in World Processor.\n\n"
            "If natural is True (1), triggers the natural wave progression (advancing @waveNumber).\n"
            "If natural is False (0), spawns enemy wave units from map spawn rules at (x, y).\n\n"
            "Args:\n"
            "    x: World tile X coordinate (default 0).\n"
            "    y: World tile Y coordinate (default 0).\n"
            "    natural: 1/True to advance natural wave, 0/False to spawn at coords (default 0)."
        ),
        min_args=2,
        max_args=3,
        valid_arg_counts=(2, 3),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("x", "Any"),
                    IntrinsicParam("y", "Any"),
                    IntrinsicParam("natural", "Any", default="0"),
                ],
                return_type="None",
                docstring="Spawn wave or advance wave progression.",
            ),
        ],
        runtime_fn=_rt_spawnwave,
        has_assignment_form=False,
    ),
    IntrinsicDef(
        name="effect",
        summary="Create a visual particle or explosion effect (effect type x y sizerot color data)",
        docstring=(
            "Creates a visual effect at world coordinates in World Processor.\n\n"
            "Args:\n"
            "    type: Effect name (Fx enum or string, e.g. Fx.WARN, Fx.EXPLOSION, 'spark').\n"
            "    x: World tile X coordinate.\n"
            "    y: World tile Y coordinate.\n"
            "    sizerot: Effect size or rotation angle (default 0).\n"
            "    color: Packed color integer or color literal (default 0).\n"
            "    data: Associated entity or block data (default 0)."
        ),
        min_args=3,
        max_args=6,
        valid_arg_counts=(3, 4, 5, 6),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("type", "Union[Fx, str]"),
                    IntrinsicParam("x", "Any"),
                    IntrinsicParam("y", "Any"),
                    IntrinsicParam("sizerot", "Any", default="0"),
                    IntrinsicParam("color", "Any", default="0"),
                    IntrinsicParam("data", "Any", default="0"),
                ],
                return_type="None",
                docstring="Create visual effect at coordinates.",
            ),
        ],
        runtime_fn=_rt_effect,
        has_assignment_form=False,
    ),
    IntrinsicDef(
        name="message",
        summary="Display an announcement, toast, notify, or set mission text (message type duration outSuccess)",
        docstring=(
            "Display an on-screen message or set mission text in World Processor.\n\n"
            "Args:\n"
            "    type: Message display type (MessageType enum or string, e.g. MessageType.ANNOUNCE, 'notify', 'toast', 'mission').\n"
            "    duration: Display duration in seconds (default 3).\n"
            "    out_success: Variable receiving success status (1 or 0) or @wait (default '@wait')."
        ),
        min_args=1,
        max_args=3,
        valid_arg_counts=(1, 2, 3),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("type", "Any"),
                    IntrinsicParam("duration", "Any", default="3"),
                    IntrinsicParam("out_success", "Any", default='"@wait"'),
                ],
                return_type="Any",
                docstring="Flush text buffer to announce, notify, toast, or set mission rule.",
            ),
        ],
        runtime_fn=_rt_message,
        has_assignment_form=True,
    ),
    IntrinsicDef(
        name="cutscene",
        summary="Control camera view, zoom, shake, or HUD during cutscenes (cutscene action p1 p2 p3 p4)",
        docstring=(
            "Control client camera and HUD elements in World Processor cutscenes.\n\n"
            "Args:\n"
            "    action: Cutscene action (CutsceneAction enum or string, e.g. CutsceneAction.PAN, 'zoom', 'stop', 'shake', 'active', 'getHud', 'setHud').\n"
            "    p1: Action param 1 (e.g. pan X, zoom level, shake amount, result var, or shown boolean).\n"
            "    p2: Action param 2 (e.g. pan Y, shake duration).\n"
            "    p3: Action param 3 (e.g. pan speed).\n"
            "    p4: Action param 4 (unused, default 0)."
        ),
        min_args=1,
        max_args=5,
        valid_arg_counts=(1, 2, 3, 4, 5),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("action", "Any"),
                    IntrinsicParam("p1", "Any", default="0"),
                    IntrinsicParam("p2", "Any", default="0"),
                    IntrinsicParam("p3", "Any", default="0"),
                    IntrinsicParam("p4", "Any", default="0"),
                ],
                return_type="Any",
                docstring="Manipulate camera or HUD cutscene state.",
            ),
        ],
        runtime_fn=_rt_cutscene,
        has_assignment_form=True,
    ),
    IntrinsicDef(
        name="playsound",
        summary="Play a sound effect globally or positionally (playsound positional id volume pitch pan x y limit)",
        docstring="Play a sound effect globally or at world coordinates.",
        min_args=2,
        max_args=8,
        valid_arg_counts=(2, 3, 4, 5, 6, 7, 8),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("positional", "Any"),
                    IntrinsicParam("id", "Any"),
                    IntrinsicParam("volume", "Any", default="1"),
                    IntrinsicParam("pitch", "Any", default="1"),
                    IntrinsicParam("pan", "Any", default="0"),
                    IntrinsicParam("x", "Any", default="0"),
                    IntrinsicParam("y", "Any", default="0"),
                    IntrinsicParam("limit", "Any", default="True"),
                ],
                return_type="None",
                docstring="Play a sound effect.",
            ),
        ],
        runtime_fn=_rt_playsound,
        has_assignment_form=False,
    ),
    IntrinsicDef(
        name="playmusic",
        summary="Play a music track or stop music (playmusic name interrupt)",
        docstring="Play a background music track.",
        min_args=1,
        max_args=2,
        valid_arg_counts=(1, 2),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("name", "Any"),
                    IntrinsicParam("interrupt", "Any", default="True"),
                ],
                return_type="None",
                docstring="Play background music track.",
            ),
        ],
        runtime_fn=_rt_playmusic,
        has_assignment_form=False,
    ),
    IntrinsicDef(
        name="makemarker",
        summary="Create an objective map marker (makemarker type id x y replace)",
        docstring="Create an objective map marker at tile coordinates.",
        min_args=4,
        max_args=5,
        valid_arg_counts=(4, 5),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("type", "Any"),
                    IntrinsicParam("id", "Any"),
                    IntrinsicParam("x", "Any"),
                    IntrinsicParam("y", "Any"),
                    IntrinsicParam("replace", "Any", default="True"),
                ],
                return_type="None",
                docstring="Create an objective map marker.",
            ),
        ],
        runtime_fn=_rt_makemarker,
        has_assignment_form=False,
    ),
    IntrinsicDef(
        name="setmarker",
        summary="Control properties of an existing map marker (setmarker type id p1 p2 p3)",
        docstring="Control properties or remove an existing map marker.",
        min_args=2,
        max_args=5,
        valid_arg_counts=(2, 3, 4, 5),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("type", "Any"),
                    IntrinsicParam("id", "Any"),
                    IntrinsicParam("p1", "Any", default="0"),
                    IntrinsicParam("p2", "Any", default="0"),
                    IntrinsicParam("p3", "Any", default="0"),
                ],
                return_type="None",
                docstring="Control map marker property.",
            ),
        ],
        runtime_fn=_rt_setmarker,
        has_assignment_form=False,
    ),
    IntrinsicDef(
        name="localeprint",
        summary="Append a localized bundle string to the logic print buffer (localeprint value)",
        docstring="Append a localized bundle string to the print buffer.",
        min_args=1,
        max_args=1,
        valid_arg_counts=(1,),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("value", "Any"),
                ],
                return_type="None",
                docstring="Print localized bundle string.",
            ),
        ],
        runtime_fn=_rt_localeprint,
        has_assignment_form=False,
    ),
    IntrinsicDef(
        name="clientdata",
        summary="Send logic data packet over network to client (clientdata channel value reliable)",
        docstring="Send custom network logic data on a channel.",
        min_args=2,
        max_args=3,
        valid_arg_counts=(2, 3),
        signatures=[
            IntrinsicSignature(
                params=[
                    IntrinsicParam("channel", "Any"),
                    IntrinsicParam("value", "Any"),
                    IntrinsicParam("reliable", "Any", default="False"),
                ],
                return_type="None",
                docstring="Send client logic data packet.",
            ),
        ],
        runtime_fn=_rt_clientdata,
        has_assignment_form=False,
    ),
]

# Map by intrinsic name
INTRINSICS: Dict[str, IntrinsicDef] = {d.name: d for d in INTRINSIC_DEFINITIONS}

# Whitelist of allowed compiler intrinsic call names
ALLOWED_INTRINSICS: Set[str] = set(INTRINSICS.keys())

# Registry Enums dictionary (Enum class objects)
ALL_REGISTRY_ENUMS: Dict[str, type] = {
    "Align": Align,
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
    "TileLayer": TileLayer,
    "QueryShape": QueryShape,
    "QueryType": QueryType,
    "StatusEffects": StatusEffects,
    "FetchType": FetchType,
    "LogicRules": LogicRules,
    "Weathers": Weathers,
    "Fx": Fx,
    "MessageType": MessageType,
    "CutsceneAction": CutsceneAction,
    "MarkerType": MarkerType,
    "MarkerControl": MarkerControl,
}

class Array:
    """Runtime representation and emulation of fixed-size Memory Cell / Bank arrays."""

    def __init__(self, block: str, size: int, dtype: Union[type, str] = int):
        if not isinstance(block, str):
            raise TypeError("Array block must be a string (e.g. 'cell1', 'bank1')")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise ValueError(f"Array size must be a positive integer, got {size!r}")

        if dtype in (int, "int"):
            self.dtype = int
            self._data: List[Union[int, float, bool]] = [0] * size
        elif dtype in (float, "float"):
            self.dtype = float
            self._data = [0.0] * size
        elif dtype in (bool, "bool"):
            self.dtype = bool
            self._data = [False] * size
        else:
            raise TypeError(f"unsupported Array dtype '{dtype}': expected int, float, or bool")

        self.block = block
        self.size = size

    def __len__(self) -> int:
        return self.size

    def __getitem__(self, index: int) -> Union[int, float, bool]:
        if not isinstance(index, int) or isinstance(index, bool):
            raise TypeError("Array index must be an integer, got boolean" if isinstance(index, bool) else "Array index must be an integer")
        if index < 0 or index >= self.size:
            raise IndexError(f"Array index out of bounds: {index} is not in range [0, {self.size})")
        val = self._data[index]
        if self.dtype is bool:
            if val is True or val == 1:
                return True
            elif val is False or val == 0:
                return False
            else:
                raise ValueError(f"Invalid boolean encoding in Array: expected 0 or 1, got {val!r}")
        return val

    def __setitem__(self, index: int, value: Any):
        if not isinstance(index, int) or isinstance(index, bool):
            raise TypeError("Array index must be an integer, got boolean" if isinstance(index, bool) else "Array index must be an integer")
        if index < 0 or index >= self.size:
            raise IndexError(f"Array index out of bounds: {index} is not in range [0, {self.size})")

        if self.dtype is int:
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"Array only stores integers, got {type(value).__name__}")
            self._data[index] = int(value)
        elif self.dtype is float:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"Array of type 'float' only stores numbers, got {type(value).__name__}")
            self._data[index] = float(value)
        elif self.dtype is bool:
            if not isinstance(value, bool):
                raise TypeError(f"Array of type 'bool' only stores booleans, got {type(value).__name__}")
            self._data[index] = bool(value)

    def __repr__(self) -> str:
        return f"Array({self.block!r}, size={self.size}, dtype={self.dtype.__name__})"


# Mindustry Built-in Variables (legacy aliases removed in favor of Vars API)
BUILTIN_VARIABLES: Set[str] = set()
BUILTIN_VARIABLE_TYPES: Dict[str, str] = {}


# Complete set of symbols exported by the official `mlog` package
MLOG_EXPORTS: Set[str] = (
    ALLOWED_INTRINSICS
    | set(ALL_REGISTRY_ENUMS.keys())
    | BUILTIN_VARIABLES
    | {
        "Array",
        "BuiltinVarToken",
        "compile_py",
        "CompileResult",
        "ColorChannels",
        "IntEnum",
        "LocateResult",
        "OreLocateResult",
        "main",
        "null",
        "raw",
        "Vars",
        "__version__",
        "_DrawCallable",
        "_OpCallable",
        "_UnitControlCallable",
        "_UnitLocateCallable",
        "_CutsceneCallable",
        "_SoundCallable",
        "_MusicCallable",
        "_MarkerCallable",
        "cutscene",
        "sound",
        "music",
        "marker",
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
    lines.append("from enum import Enum, IntEnum")
    lines.append("from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Union, overload")
    lines.append("")
    lines.append("# Package version")
    lines.append("__version__: str")
    lines.append("")
    lines.append("# Null constant representing null in Mindustry Logic")
    lines.append("null: Any = None")
    lines.append("")


    # Emit Vars Namespace
    lines.append("# " + "-" * 75)
    lines.append("# Mindustry Logic Built-in Variables Namespace (Vars API)")
    lines.append("# " + "-" * 75)
    lines.append("")
    lines.append("class BuiltinVarToken:")
    lines.append('    """Mindustry Logic built-in variable token representation."""')
    lines.append("    name: str")
    lines.append("    token: str")
    lines.append("    readonly: bool")
    lines.append("    category: str")
    lines.append("    type: str")
    lines.append("    doc: str")
    lines.append("")
    lines.append("class Vars:")
    lines.append('    """Mindustry Logic built-in variables namespace.')
    lines.append("    Provides direct access to native Mindustry built-in variables")
    lines.append("    and hardware registers using canonical Mindustry names.")
    lines.append('    """')
    for spec in sorted(BUILTIN_VARS_SPEC, key=lambda s: str(s["name"])):
        v_name = str(spec["name"])
        v_type = str(spec.get("type", "Any"))
        lines.append(f"    {v_name}: {v_type}")
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
        "def compile_py(source: str, filename: str = '<stdin>', optimize: bool = False, validate: bool = True, allow_functions: bool = False, fold_constants: bool = True, comments_to_print: bool = False) -> CompileResult:"
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
        if name == "draw":
            lines.append("class _DrawCallable:")
            lines.append('    """Callable namespace object for Mindustry draw operations.')
            lines.append("")
            lines.append("    Supports both legacy function-call syntax:")
            lines.append('        draw("line", x1, y1, x2, y2)')
            lines.append("        draw(DrawType.LINE, x1, y1, x2, y2)")
            lines.append("    and modern namespace method syntax:")
            lines.append("        draw.line(x1, y1, x2, y2)")
            lines.append("        draw.clear(r=0, g=0, b=0, a=0)")
            lines.append("        draw.color(r, g, b, a=255)")
            lines.append('    """')
            lines.append("    def __call__(self, type: Union[DrawType, str], x: Any = 0, y: Any = 0, p1: Any = 0, p2: Any = 0, p3: Any = 0, p4: Any = 0) -> None: ...")
            lines.append("    def clear(self, r: Any = 0, g: Any = 0, b: Any = 0, a: Any = 0) -> None: ...")
            lines.append("    def color(self, r: Any, g: Any, b: Any, a: Any = 255) -> None: ...")
            lines.append("    def col(self, color: Any) -> None: ...")
            lines.append("    def stroke(self, width: Any) -> None: ...")
            lines.append("    def line(self, x1: Any, y1: Any, x2: Any, y2: Any) -> None: ...")
            lines.append("    def rect(self, x: Any, y: Any, width: Any, height: Any) -> None: ...")
            lines.append("    def line_rect(self, x: Any, y: Any, width: Any, height: Any) -> None: ...")
            lines.append("    def lineRect(self, x: Any, y: Any, width: Any, height: Any) -> None: ...")
            lines.append("    def poly(self, x: Any, y: Any, sides: Any, radius: Any, rotation: Any = 0) -> None: ...")
            lines.append("    def line_poly(self, x: Any, y: Any, sides: Any, radius: Any, rotation: Any = 0) -> None: ...")
            lines.append("    def linePoly(self, x: Any, y: Any, sides: Any, radius: Any, rotation: Any = 0) -> None: ...")
            lines.append("    def triangle(self, x1: Any, y1: Any, x2: Any, y2: Any, x3: Any, y3: Any) -> None: ...")
            lines.append("    def image(self, x: Any, y: Any, image: Any, size: Any = 32, rotation: Any = 0) -> None: ...")
            lines.append("    def print(self, x: Any, y: Any, align: Any = 0) -> None: ...")
            lines.append("    def translate(self, x: Any, y: Any) -> None: ...")
            lines.append("    def scale(self, x: Any, y: Any) -> None: ...")
            lines.append("    def rotate(self, degrees: Any) -> None: ...")
            lines.append("    def reset(self) -> None: ...")
            lines.append("    def flush(self, display: Any) -> None: ...")
            lines.append("")
            lines.append("draw: _DrawCallable")
            lines.append("")
            continue
        if name == "ucontrol":
            lines.append("class _UnitControlCallable:")
            lines.append('    """Callable namespace object for Mindustry unit control operations.')
            lines.append("")
            lines.append("    Supports both legacy function-call syntax:")
            lines.append('        ucontrol("move", x, y)')
            lines.append("        ucontrol(UnitControl.MOVE, x, y)")
            lines.append("    and modern namespace method syntax:")
            lines.append("        ucontrol.move(x, y)")
            lines.append("        ucontrol.approach(x, y, radius)")
            lines.append("        ucontrol.mine(x, y)")
            lines.append("        ucontrol.boost(True)")
            lines.append("        ucontrol.idle()")
            lines.append('    """')
            lines.append("    def __call__(self, action: Union[UnitControl, str], p1: Any = 0, p2: Any = 0, p3: Any = 0, p4: Any = 0, p5: Any = 0) -> None: ...")
            lines.append("    def idle(self) -> None: ...")
            lines.append("    def stop(self) -> None: ...")
            lines.append("    def move(self, x: Any, y: Any) -> None: ...")
            lines.append("    def approach(self, x: Any, y: Any, radius: Any) -> None: ...")
            lines.append("    def pathfind(self, x: Any, y: Any) -> None: ...")
            lines.append("    def auto_pathfind(self) -> None: ...")
            lines.append("    def autoPathfind(self) -> None: ...")
            lines.append("    def boost(self, enable: Any) -> None: ...")
            lines.append("    def target(self, x: Any, y: Any, shoot: Any) -> None: ...")
            lines.append("    def targetp(self, unit: Any, shoot: Any) -> None: ...")
            lines.append("    def item_drop(self, to: Any, amount: Any) -> None: ...")
            lines.append("    def itemDrop(self, to: Any, amount: Any) -> None: ...")
            lines.append("    def item_take(self, from_: Any, item: Any, amount: Any) -> None: ...")
            lines.append("    def itemTake(self, from_: Any, item: Any, amount: Any) -> None: ...")
            lines.append("    def pay_drop(self) -> None: ...")
            lines.append("    def payDrop(self) -> None: ...")
            lines.append("    def pay_take(self, take_units: Any) -> None: ...")
            lines.append("    def payTake(self, take_units: Any) -> None: ...")
            lines.append("    def pay_enter(self) -> None: ...")
            lines.append("    def payEnter(self) -> None: ...")
            lines.append("    def mine(self, x: Any, y: Any) -> None: ...")
            lines.append("    def flag(self, value: Any) -> None: ...")
            lines.append("    def build(self, x: Any, y: Any, block: Any, rotation: Any, config: Any) -> None: ...")
            lines.append("    def deconstruct(self, x: Any, y: Any) -> None: ...")
            lines.append("    def get_block(self, x: Any, y: Any, out_type: Any, out_building: Any, out_floor: Any) -> None: ...")
            lines.append("    def getBlock(self, x: Any, y: Any, out_type: Any, out_building: Any, out_floor: Any) -> None: ...")
            lines.append("    def within(self, x: Any, y: Any, radius: Any, out_result: Any) -> None: ...")
            lines.append("    def unbind(self) -> None: ...")
            lines.append("")
            lines.append("ucontrol: _UnitControlCallable")
            lines.append("")
            continue
        if name == "cutscene":
            lines.append("class _CutsceneCallable:")
            lines.append('    """Callable namespace object for Mindustry cutscene operations.')
            lines.append("")
            lines.append("    Supports both direct function-call syntax:")
            lines.append('        cutscene("pan", x, y, speed)')
            lines.append("        cutscene(CutsceneAction.PAN, x, y, speed)")
            lines.append("        result = cutscene(CutsceneAction.ACTIVE)")
            lines.append("    and modern namespace method syntax:")
            lines.append("        cutscene.pan(x, y, speed=0.06)")
            lines.append("        cutscene.zoom(level)")
            lines.append("        cutscene.stop()")
            lines.append("        cutscene.shake(amount, duration)")
            lines.append("        result = cutscene.active()")
            lines.append("        result = cutscene.get_hud()")
            lines.append("        cutscene.set_hud(shown)")
            lines.append('    """')
            lines.append("    def __call__(self, action: Union[CutsceneAction, str], p1: Any = 0, p2: Any = 0, p3: Any = 0, p4: Any = 0) -> Any: ...")
            lines.append("    @overload")
            lines.append("    def active(self) -> Any: ...")
            lines.append("    @overload")
            lines.append("    def active(self, out_result: Any) -> None: ...")
            lines.append("    def active(self, *args: Any) -> Any: ...")
            lines.append("    def pan(self, x: Any, y: Any, speed: Any = 0.06) -> None: ...")
            lines.append("    def zoom(self, level: Any) -> None: ...")
            lines.append("    def stop(self) -> None: ...")
            lines.append("    def shake(self, amount: Any, duration: Any) -> None: ...")
            lines.append("    @overload")
            lines.append("    def get_hud(self) -> Any: ...")
            lines.append("    @overload")
            lines.append("    def get_hud(self, out_result: Any) -> None: ...")
            lines.append("    def get_hud(self, *args: Any) -> Any: ...")
            lines.append("    @overload")
            lines.append("    def getHud(self) -> Any: ...")
            lines.append("    @overload")
            lines.append("    def getHud(self, out_result: Any) -> None: ...")
            lines.append("    def getHud(self, *args: Any) -> Any: ...")
            lines.append("    def set_hud(self, shown: Any) -> None: ...")
            lines.append("    def setHud(self, shown: Any) -> None: ...")
            lines.append("")
            lines.append("cutscene: _CutsceneCallable")
            lines.append("")
            continue
        if name == "ulocate":
            lines.append("class LocateResult(NamedTuple):")
            lines.append('    """Runtime mock result for ulocate building/spawn/damaged queries (4-tuple: x, y, found, building)."""')
            lines.append("    x: float")
            lines.append("    y: float")
            lines.append("    found: int")
            lines.append("    building: Any")
            lines.append("")
            lines.append("class OreLocateResult(NamedTuple):")
            lines.append('    """Runtime mock result for ulocate ore queries (3-tuple: x, y, found)."""')
            lines.append("    x: float")
            lines.append("    y: float")
            lines.append("    found: int")
            lines.append("")
            lines.append("class _UnitLocateCallable:")
            lines.append('    """Callable namespace object for Mindustry unit locate operations.')
            lines.append("")
            lines.append("    NOTE: These runtime methods are local static stubs/mocks for AST validation")
            lines.append("    and IDE autocompletion. They do not connect to or query a live Mindustry game.")
            lines.append("")
            lines.append("    Supports both Pythonic tuple unpacking:")
            lines.append('        core_x, core_y, found_core, core_build = ulocate.building("core", False)')
            lines.append('        ore_x, ore_y, found_ore = ulocate.ore("@copper")')
            lines.append('        spawn_x, spawn_y, found_spawn, spawn_build = ulocate.spawn()')
            lines.append('        dmg_x, dmg_y, found_dmg, dmg_build = ulocate.damaged()')
            lines.append("    and positional argument syntax.")
            lines.append('    """')
            lines.append("    def __call__(self, locate: Any, *params: Any) -> Any: ...")
            lines.append("    @overload")
            lines.append("    def ore(self, ore: Any) -> OreLocateResult: ...")
            lines.append("    @overload")
            lines.append("    def ore(self, ore: Any, out_x: Any, out_y: Any, out_found: Any, out_build: Any = None) -> None: ...")
            lines.append("    @overload")
            lines.append("    def building(self, group: Any, enemy: Any) -> LocateResult: ...")
            lines.append("    @overload")
            lines.append("    def building(self, group: Any, enemy: Any, out_x: Any, out_y: Any, out_found: Any, out_building: Any = None) -> None: ...")
            lines.append("    @overload")
            lines.append("    def spawn(self) -> LocateResult: ...")
            lines.append("    @overload")
            lines.append("    def spawn(self, out_x: Any, out_y: Any, out_found: Any, out_build: Any = None) -> None: ...")
            lines.append("    @overload")
            lines.append("    def damaged(self) -> LocateResult: ...")
            lines.append("    @overload")
            lines.append("    def damaged(self, out_x: Any, out_y: Any, out_found: Any, out_building: Any = None) -> None: ...")
            lines.append("")
            lines.append("ulocate: _UnitLocateCallable")
            lines.append("")
            continue
        if name == "op":
            lines.append("class _OpCallable:")
            lines.append('    """Callable namespace object for Mindustry logic operations.')
            lines.append("")
            lines.append("    Supports both legacy function-call syntax:")
            lines.append('        op("add", dest, a, b)')
            lines.append('        result = op("add", a, b)')
            lines.append("    and modern namespace method syntax:")
            lines.append("        result = op.add(a, b)")
            lines.append("        op.add(dest, a, b)")
            lines.append("        result = op.sin(deg)")
            lines.append("        op.sin(dest, deg)")
            lines.append('    """')
            lines.append("    @overload")
            lines.append("    def __call__(self, op_name: Union[LogicOp, str], dest: Any, a: Any, b: Any = 0) -> Any: ...")
            lines.append("    @overload")
            lines.append("    def __call__(self, op_name: Union[LogicOp, str], a: Any, b: Any = 0) -> Any: ...")
            lines.append("    def __call__(self, op_name: Any, *args: Any) -> Any: ...")
            lines.append("")
            lines.append("    # Unary operations (15)")
            for u in ("abs", "sign", "log", "log10", "floor", "ceil", "round", "sqrt", "rand", "sin", "cos", "tan", "asin", "acos", "atan"):
                lines.append("    @overload")
                lines.append(f"    def {u}(self, a: Any) -> Any: ...")
                lines.append("    @overload")
                lines.append(f"    def {u}(self, dest: Any, a: Any) -> Any: ...")
                lines.append(f"    def {u}(self, *args: Any) -> Any: ...")
            lines.append("    log_10 = log10")
            lines.append("")
            lines.append("    # Binary operations (27)")
            for b in (
                "add", "sub", "mul", "div", "idiv", "mod", "emod", "pow",
                "equal", "not_equal", "notEqual", "land", "less_than", "lessThan",
                "less_than_eq", "lessThanEq", "greater_than", "greaterThan",
                "greater_than_eq", "greaterThanEq", "strict_equal", "strictEqual",
                "shl", "shr", "ushr", "xor",
                "max", "min", "angle", "angle_diff", "angleDiff", "len", "length",
                "noise", "logn",
            ):
                lines.append("    @overload")
                lines.append(f"    def {b}(self, a: Any, b: Any) -> Any: ...")
                lines.append("    @overload")
                lines.append(f"    def {b}(self, dest: Any, a: Any, b: Any) -> Any: ...")
                lines.append(f"    def {b}(self, *args: Any) -> Any: ...")
            lines.append("")
            lines.append("op: _OpCallable")
            lines.append("")
            continue
        if name == "unpackcolor":
            lines.append("class ColorChannels(NamedTuple):")
            lines.append('    """Runtime mock result for unpackcolor queries (4-tuple: r, g, b, a)."""')
            lines.append("    r: float")
            lines.append("    g: float")
            lines.append("    b: float")
            lines.append("    a: float")
            lines.append("")
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
                    lines.append(("    " + dl) if dl else "")
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
                lines.append(("    " + dl) if dl else "")
            lines.append('    """')
            lines.append("    ...")
            lines.append("")

    # Emit Sound Namespace
    lines.append("class _SoundCallable:")
    lines.append('    """Callable namespace object for Mindustry sound operations."""')
    lines.append("    def __call__(self, positional: Any, id: Any, volume: Any = 1, pitch: Any = 1, pan: Any = 0, x: Any = 0, y: Any = 0, limit: Any = True) -> None: ...")
    lines.append("    def play(self, id: Any, volume: Any = 1, pitch: Any = 1, pan: Any = 0, limit: Any = True) -> None: ...")
    lines.append("    def play_at(self, id: Any, x: Any, y: Any, volume: Any = 1, pitch: Any = 1, limit: Any = True) -> None: ...")
    lines.append("    def playAt(self, id: Any, x: Any, y: Any, volume: Any = 1, pitch: Any = 1, limit: Any = True) -> None: ...")
    lines.append("")
    lines.append("sound: _SoundCallable")
    lines.append("")

    # Emit Music Namespace
    lines.append("class _MusicCallable:")
    lines.append('    """Callable namespace object for Mindustry music operations."""')
    lines.append("    def __call__(self, name: Any, interrupt: Any = True) -> None: ...")
    lines.append("    def play(self, name: Any, interrupt: Any = True) -> None: ...")
    lines.append("    def stop(self) -> None: ...")
    lines.append("")
    lines.append("music: _MusicCallable")
    lines.append("")

    # Emit Marker Namespace
    lines.append("class _MarkerCallable:")
    lines.append('    """Callable namespace object for Mindustry map marker operations."""')
    lines.append("    def make(self, type: Union[MarkerType, str], id: Any, x: Any, y: Any, replace: Any = True) -> None: ...")
    lines.append("    def remove(self, id: Any) -> None: ...")
    lines.append("    def world(self, id: Any, enabled: Any = True) -> None: ...")
    lines.append("    def minimap(self, id: Any, enabled: Any = True) -> None: ...")
    lines.append("    def light(self, id: Any, enabled: Any = True) -> None: ...")
    lines.append("    def autoscale(self, id: Any, enabled: Any = True) -> None: ...")
    lines.append("    def pos(self, id: Any, x: Any, y: Any) -> None: ...")
    lines.append("    def end_pos(self, id: Any, x: Any, y: Any) -> None: ...")
    lines.append("    def endPos(self, id: Any, x: Any, y: Any) -> None: ...")
    lines.append("    def draw_layer(self, id: Any, layer: Any) -> None: ...")
    lines.append("    def drawLayer(self, id: Any, layer: Any) -> None: ...")
    lines.append("    def color(self, id: Any, color: Any) -> None: ...")
    lines.append("    def radius(self, id: Any, radius: Any) -> None: ...")
    lines.append("    def stroke(self, id: Any, stroke: Any) -> None: ...")
    lines.append("    def outline(self, id: Any, outline: Any = True) -> None: ...")
    lines.append("    def rotation(self, id: Any, rotation: Any) -> None: ...")
    lines.append("    def shape(self, id: Any, sides: Any, fill: Any = 1, outline: Any = 1) -> None: ...")
    lines.append("    def arc(self, id: Any, start: Any, end: Any) -> None: ...")
    lines.append("    def flush_text(self, id: Any, fetch: Any = False) -> None: ...")
    lines.append("    def flushText(self, id: Any, fetch: Any = False) -> None: ...")
    lines.append("    def font_size(self, id: Any, size: Any) -> None: ...")
    lines.append("    def fontSize(self, id: Any, size: Any) -> None: ...")
    lines.append("    def text_height(self, id: Any, height: Any) -> None: ...")
    lines.append("    def textHeight(self, id: Any, height: Any) -> None: ...")
    lines.append("    def text_align(self, id: Any, align: Any) -> None: ...")
    lines.append("    def textAlign(self, id: Any, align: Any) -> None: ...")
    lines.append("    def line_align(self, id: Any, align: Any) -> None: ...")
    lines.append("    def lineAlign(self, id: Any, align: Any) -> None: ...")
    lines.append("    def label_flags(self, id: Any, background: Any = 1, outline: Any = 1) -> None: ...")
    lines.append("    def labelFlags(self, id: Any, background: Any = 1, outline: Any = 1) -> None: ...")
    lines.append("    def texture(self, id: Any, name: Any, print_flush: Any = False) -> None: ...")
    lines.append("    def texture_size(self, id: Any, width: Any, height: Any) -> None: ...")
    lines.append("    def textureSize(self, id: Any, width: Any, height: Any) -> None: ...")
    lines.append("    def posi(self, id: Any, index: Any, x: Any, y: Any) -> None: ...")
    lines.append("    def uvi(self, id: Any, index: Any, x: Any, y: Any) -> None: ...")
    lines.append("    def colori(self, id: Any, index: Any, color: Any) -> None: ...")
    lines.append("")
    lines.append("marker: _MarkerCallable")
    lines.append("")

    # Emit Array Class
    lines.append("# " + "-" * 75)
    lines.append("# Array Class (Memory Cell / Bank Allocator)")
    lines.append("# " + "-" * 75)
    lines.append("")
    lines.append("class Array:")
    lines.append('    """Fixed-size memory array backed by a Mindustry Memory Cell (max 64) or Memory Bank (max 512)."""')
    lines.append("    block: str")
    lines.append("    size: int")
    lines.append("    dtype: type")
    lines.append("    def __init__(self, block: str, size: int, dtype: Union[type, str] = int) -> None: ...")
    lines.append("    def __getitem__(self, index: int) -> Any: ...")
    lines.append("    def __setitem__(self, index: int, value: Any) -> None: ...")
    lines.append("    def __len__(self) -> int: ...")
    lines.append("")

    # Emit __all__
    all_exports_sorted = sorted(list(MLOG_EXPORTS))
    lines.append("__all__ = [")
    for exp in all_exports_sorted:
        lines.append(f'    "{exp}",')
    lines.append("]")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    content = generate_pyi()
    for p in ("mlog.pyi", "src/mlog.pyi"):
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
    print("Updated mlog.pyi and src/mlog.pyi successfully.")

