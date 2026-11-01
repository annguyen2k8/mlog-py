"""Structured Control Flow Intermediate Representation (IR).

Represents recovered structured program constructs (If, While, Break, Continue, Pass,
Instruction, Unstructured) independent of high-level expression synthesis or variable analysis.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .instruction import MlogInstruction
from .semantics import format_semantic_argument, UNARY_LOGIC_OPS


# Mapping of Mindustry logic comparison operators to Python operators
CMP_TO_PY = {
    "equal": "==",
    "notEqual": "!=",
    "lessThan": "<",
    "lessThanEq": "<=",
    "greaterThan": ">",
    "greaterThanEq": ">=",
    "strictEqual": "is",
}

CMP_INVERSE_TO_PY = {
    "equal": "!=",
    "notEqual": "==",
    "lessThan": ">=",
    "lessThanEq": ">",
    "greaterThan": "<=",
    "greaterThanEq": "<",
    "strictEqual": "is not",
}


def is_compiler_temporary(name: str) -> bool:
    """Return True if variable name matches standard compiler temporary conventions."""
    if name.startswith("__tmp"):
        return True
    if name.startswith("*tmp"):
        return True
    if name.startswith("_tmp") and (len(name) <= 5 or name[4:].isdigit()):
        return True
    return False


def is_zero_operand(token: str) -> bool:
    """Return True for numeric zero operands used as canonical dummy arguments."""
    try:
        return float(token) == 0.0
    except (TypeError, ValueError):
        return False


def is_canonical_zero_operand(token: str) -> bool:
    """Return True only for the canonical dummy token ``0``."""
    return token == "0"


def format_control_operand(
    arg_idx: int,
    arg: str,
    defined_variables: Optional[Set[str]],
    args: Tuple[str, ...],
) -> str:
    """Format a generic control operand while preserving noncanonical zero spellings."""
    if arg_idx >= 2 and arg != "0" and is_zero_operand(arg):
        if arg in ("0.0", "-0.0"):
            return arg
        # raw() preserves exotic spellings such as 0e0 and 00 that Python would
        # otherwise normalize or reject as a literal.
        return f"raw({arg!r})"
    return format_semantic_argument("control", arg_idx, arg, defined_variables, args)


def format_operand(op: str) -> str:
    """Format an mlog operand token into Python-friendly representation."""
    if op == "true":
        return "True"
    if op == "false":
        return "False"
    if op == "null":
        return "None"
    if op.startswith("@"):
        return repr(op)
    return op


def condition_to_python(cond: str, a: str, b: str, invert: bool = False) -> str:
    """Format an mlog jump condition into a Python boolean expression string."""
    a_py = format_operand(a)
    b_py = format_operand(b)

    if cond == "always":
        return "False" if invert else "True"

    # Special handling for boolean constants (e.g. equal true 0 -> inverted is True)
    if cond == "equal" and a == "true" and b == "0":
        return "True" if invert else "False"
    if cond == "notEqual" and a == "true" and b == "0":
        return "False" if invert else "True"

    # Truthiness checks: a == 0 or a != 0
    if cond == "equal" and b == "0":
        # Inverted of (a == 0) is (a != 0)
        return f"{a_py} != 0" if invert else f"{a_py} == 0"
    if cond == "notEqual" and b == "0":
        # Inverted of (a != 0) is (a == 0)
        return f"{a_py} == 0" if invert else f"{a_py} != 0"

    op_map = CMP_INVERSE_TO_PY if invert else CMP_TO_PY
    py_op = op_map.get(cond, "==")
    return f"{a_py} {py_op} {b_py}"


ALIGN_TOKEN_TO_ENUM: Dict[str, str] = {
    "@center": "Align.CENTER",
    "@top": "Align.TOP",
    "@bottom": "Align.BOTTOM",
    "@left": "Align.LEFT",
    "@right": "Align.RIGHT",
    "@topLeft": "Align.TOP_LEFT",
    "@topRight": "Align.TOP_RIGHT",
    "@bottomLeft": "Align.BOTTOM_LEFT",
    "@bottomRight": "Align.BOTTOM_RIGHT",
    "center": "Align.CENTER",
    "top": "Align.TOP",
    "bottom": "Align.BOTTOM",
    "left": "Align.LEFT",
    "right": "Align.RIGHT",
    "topLeft": "Align.TOP_LEFT",
    "topRight": "Align.TOP_RIGHT",
    "bottomLeft": "Align.BOTTOM_LEFT",
    "bottomRight": "Align.BOTTOM_RIGHT",
}


def instruction_to_python(
    instr: MlogInstruction,
    defined_variables: Optional[Set[str]] = None,
) -> str:
    """Convert an MlogInstruction into a Python DSL statement string without expression synthesis."""
    op = instr.opcode
    args = instr.args

    if op == "draw" and len(args) >= 1:
        cmd = args[0]
        if cmd == "clear" and len(args) >= 4:
            r = format_semantic_argument("draw", 1, args[1], defined_variables, args)
            g = format_semantic_argument("draw", 2, args[2], defined_variables, args)
            b = format_semantic_argument("draw", 3, args[3], defined_variables, args)
            return f"draw.clear({r}, {g}, {b})"
        elif cmd == "color" and len(args) >= 5:
            r = format_semantic_argument("draw", 1, args[1], defined_variables, args)
            g = format_semantic_argument("draw", 2, args[2], defined_variables, args)
            b = format_semantic_argument("draw", 3, args[3], defined_variables, args)
            a = format_semantic_argument("draw", 4, args[4], defined_variables, args)
            if a == "255":
                return f"draw.color({r}, {g}, {b})"
            return f"draw.color({r}, {g}, {b}, {a})"
        elif cmd == "col" and len(args) >= 2:
            color = format_semantic_argument("draw", 1, args[1], defined_variables, args)
            return f"draw.col({color})"
        elif cmd == "stroke" and len(args) >= 2:
            width = format_semantic_argument("draw", 1, args[1], defined_variables, args)
            return f"draw.stroke({width})"
        elif cmd == "line" and len(args) >= 5:
            x1 = format_semantic_argument("draw", 1, args[1], defined_variables, args)
            y1 = format_semantic_argument("draw", 2, args[2], defined_variables, args)
            x2 = format_semantic_argument("draw", 3, args[3], defined_variables, args)
            y2 = format_semantic_argument("draw", 4, args[4], defined_variables, args)
            return f"draw.line({x1}, {y1}, {x2}, {y2})"
        elif cmd == "rect" and len(args) >= 5:
            x = format_semantic_argument("draw", 1, args[1], defined_variables, args)
            y = format_semantic_argument("draw", 2, args[2], defined_variables, args)
            w = format_semantic_argument("draw", 3, args[3], defined_variables, args)
            h = format_semantic_argument("draw", 4, args[4], defined_variables, args)
            return f"draw.rect({x}, {y}, {w}, {h})"
        elif cmd in ("lineRect", "line_rect") and len(args) >= 5:
            x = format_semantic_argument("draw", 1, args[1], defined_variables, args)
            y = format_semantic_argument("draw", 2, args[2], defined_variables, args)
            w = format_semantic_argument("draw", 3, args[3], defined_variables, args)
            h = format_semantic_argument("draw", 4, args[4], defined_variables, args)
            return f"draw.line_rect({x}, {y}, {w}, {h})"
        elif cmd == "poly" and len(args) >= 6:
            x = format_semantic_argument("draw", 1, args[1], defined_variables, args)
            y = format_semantic_argument("draw", 2, args[2], defined_variables, args)
            sides = format_semantic_argument("draw", 3, args[3], defined_variables, args)
            radius = format_semantic_argument("draw", 4, args[4], defined_variables, args)
            rot = format_semantic_argument("draw", 5, args[5], defined_variables, args)
            if rot in ("0", "0.0"):
                return f"draw.poly({x}, {y}, {sides}, {radius})"
            return f"draw.poly({x}, {y}, {sides}, {radius}, {rot})"
        elif cmd in ("linePoly", "line_poly") and len(args) >= 6:
            x = format_semantic_argument("draw", 1, args[1], defined_variables, args)
            y = format_semantic_argument("draw", 2, args[2], defined_variables, args)
            sides = format_semantic_argument("draw", 3, args[3], defined_variables, args)
            radius = format_semantic_argument("draw", 4, args[4], defined_variables, args)
            rot = format_semantic_argument("draw", 5, args[5], defined_variables, args)
            if rot in ("0", "0.0"):
                return f"draw.line_poly({x}, {y}, {sides}, {radius})"
            return f"draw.line_poly({x}, {y}, {sides}, {radius}, {rot})"
        elif cmd == "triangle" and len(args) >= 7:
            x1 = format_semantic_argument("draw", 1, args[1], defined_variables, args)
            y1 = format_semantic_argument("draw", 2, args[2], defined_variables, args)
            x2 = format_semantic_argument("draw", 3, args[3], defined_variables, args)
            y2 = format_semantic_argument("draw", 4, args[4], defined_variables, args)
            x3 = format_semantic_argument("draw", 5, args[5], defined_variables, args)
            y3 = format_semantic_argument("draw", 6, args[6], defined_variables, args)
            return f"draw.triangle({x1}, {y1}, {x2}, {y2}, {x3}, {y3})"
        elif cmd == "image" and len(args) >= 6:
            x = format_semantic_argument("draw", 1, args[1], defined_variables, args)
            y = format_semantic_argument("draw", 2, args[2], defined_variables, args)
            img = format_semantic_argument("draw", 3, args[3], defined_variables, args)
            size = format_semantic_argument("draw", 4, args[4], defined_variables, args)
            rot = format_semantic_argument("draw", 5, args[5], defined_variables, args)
            if rot in ("0", "0.0"):
                if size in ("32", "32.0"):
                    return f"draw.image({x}, {y}, {img})"
                return f"draw.image({x}, {y}, {img}, {size})"
            return f"draw.image({x}, {y}, {img}, {size}, {rot})"
        elif cmd == "print" and len(args) >= 4:
            x = format_semantic_argument("draw", 1, args[1], defined_variables, args)
            y = format_semantic_argument("draw", 2, args[2], defined_variables, args)
            align_token = args[3]
            if align_token in ALIGN_TOKEN_TO_ENUM:
                return f"draw.print({x}, {y}, {ALIGN_TOKEN_TO_ENUM[align_token]})"
            elif align_token in ("0", "0.0"):
                return f"draw.print({x}, {y})"
            else:
                align_arg = format_semantic_argument("draw", 3, align_token, defined_variables, args)
                return f"draw.print({x}, {y}, {align_arg})"
        elif cmd == "translate" and len(args) >= 3:
            x = format_semantic_argument("draw", 1, args[1], defined_variables, args)
            y = format_semantic_argument("draw", 2, args[2], defined_variables, args)
            return f"draw.translate({x}, {y})"
        elif cmd == "scale" and len(args) >= 3:
            x = format_semantic_argument("draw", 1, args[1], defined_variables, args)
            y = format_semantic_argument("draw", 2, args[2], defined_variables, args)
            return f"draw.scale({x}, {y})"
        elif cmd == "rotate" and len(args) >= 4:
            deg = format_semantic_argument("draw", 3, args[3], defined_variables, args)
            return f"draw.rotate({deg})"
        elif cmd == "reset":
            return "draw.reset()"

    if op == "control" and len(args) == 6:
        control_type = args[0]
        if control_type == "enabled" and all(is_canonical_zero_operand(a) for a in args[3:6]):
            target = format_semantic_argument("control", 1, args[1], defined_variables, args)
            value = format_semantic_argument("control", 2, args[2], defined_variables, args)
            return f"control.enabled({target}, {value})"
        elif control_type == "shoot" and is_canonical_zero_operand(args[5]):
            target = format_semantic_argument("control", 1, args[1], defined_variables, args)
            x = format_semantic_argument("control", 2, args[2], defined_variables, args)
            y = format_semantic_argument("control", 3, args[3], defined_variables, args)
            shoot = format_semantic_argument("control", 4, args[4], defined_variables, args)
            return f"control.shoot({target}, {x}, {y}, {shoot})"
        elif control_type == "shootp" and all(is_canonical_zero_operand(a) for a in args[4:6]):
            target = format_semantic_argument("control", 1, args[1], defined_variables, args)
            unit = format_semantic_argument("control", 2, args[2], defined_variables, args)
            shoot = format_semantic_argument("control", 3, args[3], defined_variables, args)
            return f"control.shootp({target}, {unit}, {shoot})"
        elif control_type == "config" and all(is_canonical_zero_operand(a) for a in args[3:6]):
            target = format_semantic_argument("control", 1, args[1], defined_variables, args)
            value = format_semantic_argument("control", 2, args[2], defined_variables, args)
            return f"control.config({target}, {value})"
        elif control_type == "color" and all(is_canonical_zero_operand(a) for a in args[3:6]):
            target = format_semantic_argument("control", 1, args[1], defined_variables, args)
            value = format_semantic_argument("control", 2, args[2], defined_variables, args)
            return f"control.color({target}, {value})"

    if op == "ucontrol" and len(args) >= 1:
        action = args[0]
        if action in ("idle", "stop"):
            return f"ucontrol.{action}()"
        elif action == "move" and len(args) >= 3:
            x = format_semantic_argument("ucontrol", 1, args[1], defined_variables, args)
            y = format_semantic_argument("ucontrol", 2, args[2], defined_variables, args)
            return f"ucontrol.move({x}, {y})"
        elif action == "approach" and len(args) >= 4:
            x = format_semantic_argument("ucontrol", 1, args[1], defined_variables, args)
            y = format_semantic_argument("ucontrol", 2, args[2], defined_variables, args)
            r = format_semantic_argument("ucontrol", 3, args[3], defined_variables, args)
            return f"ucontrol.approach({x}, {y}, {r})"
        elif action == "pathfind" and len(args) >= 3:
            x = format_semantic_argument("ucontrol", 1, args[1], defined_variables, args)
            y = format_semantic_argument("ucontrol", 2, args[2], defined_variables, args)
            return f"ucontrol.pathfind({x}, {y})"
        elif action in ("autoPathfind", "auto_pathfind"):
            return "ucontrol.auto_pathfind()"
        elif action == "boost" and len(args) >= 2:
            enable = format_semantic_argument("ucontrol", 1, args[1], defined_variables, args)
            return f"ucontrol.boost({enable})"
        elif action == "target" and len(args) >= 4:
            x = format_semantic_argument("ucontrol", 1, args[1], defined_variables, args)
            y = format_semantic_argument("ucontrol", 2, args[2], defined_variables, args)
            shoot = format_semantic_argument("ucontrol", 3, args[3], defined_variables, args)
            return f"ucontrol.target({x}, {y}, {shoot})"
        elif action == "targetp" and len(args) >= 3:
            unit = format_semantic_argument("ucontrol", 1, args[1], defined_variables, args)
            shoot = format_semantic_argument("ucontrol", 2, args[2], defined_variables, args)
            return f"ucontrol.targetp({unit}, {shoot})"
        elif action in ("itemDrop", "item_drop") and len(args) >= 3:
            to = format_semantic_argument("ucontrol", 1, args[1], defined_variables, args)
            amount = format_semantic_argument("ucontrol", 2, args[2], defined_variables, args)
            return f"ucontrol.item_drop({to}, {amount})"
        elif action in ("itemTake", "item_take") and len(args) >= 4:
            from_ = format_semantic_argument("ucontrol", 1, args[1], defined_variables, args)
            item = format_semantic_argument("ucontrol", 2, args[2], defined_variables, args)
            amount = format_semantic_argument("ucontrol", 3, args[3], defined_variables, args)
            return f"ucontrol.item_take({from_}, {item}, {amount})"
        elif action in ("payDrop", "pay_drop"):
            return "ucontrol.pay_drop()"
        elif action in ("payTake", "pay_take") and len(args) >= 2:
            take_units = format_semantic_argument("ucontrol", 1, args[1], defined_variables, args)
            return f"ucontrol.pay_take({take_units})"
        elif action in ("payEnter", "pay_enter"):
            return "ucontrol.pay_enter()"
        elif action == "mine" and len(args) >= 3:
            x = format_semantic_argument("ucontrol", 1, args[1], defined_variables, args)
            y = format_semantic_argument("ucontrol", 2, args[2], defined_variables, args)
            return f"ucontrol.mine({x}, {y})"
        elif action == "flag" and len(args) >= 2:
            val = format_semantic_argument("ucontrol", 1, args[1], defined_variables, args)
            return f"ucontrol.flag({val})"
        elif action == "build" and len(args) >= 6:
            x = format_semantic_argument("ucontrol", 1, args[1], defined_variables, args)
            y = format_semantic_argument("ucontrol", 2, args[2], defined_variables, args)
            block = format_semantic_argument("ucontrol", 3, args[3], defined_variables, args)
            rot = format_semantic_argument("ucontrol", 4, args[4], defined_variables, args)
            config = format_semantic_argument("ucontrol", 5, args[5], defined_variables, args)
            return f"ucontrol.build({x}, {y}, {block}, {rot}, {config})"
        elif action == "deconstruct" and len(args) >= 3:
            x = format_semantic_argument("ucontrol", 1, args[1], defined_variables, args)
            y = format_semantic_argument("ucontrol", 2, args[2], defined_variables, args)
            return f"ucontrol.deconstruct({x}, {y})"
        elif action in ("getBlock", "get_block") and len(args) >= 6:
            x = format_semantic_argument("ucontrol", 1, args[1], defined_variables, args)
            y = format_semantic_argument("ucontrol", 2, args[2], defined_variables, args)
            out_t = format_semantic_argument("ucontrol", 3, args[3], defined_variables, args)
            out_b = format_semantic_argument("ucontrol", 4, args[4], defined_variables, args)
            out_f = format_semantic_argument("ucontrol", 5, args[5], defined_variables, args)
            return f"ucontrol.get_block({x}, {y}, {out_t}, {out_b}, {out_f})"
        elif action == "within" and len(args) >= 5:
            x = format_semantic_argument("ucontrol", 1, args[1], defined_variables, args)
            y = format_semantic_argument("ucontrol", 2, args[2], defined_variables, args)
            r = format_semantic_argument("ucontrol", 3, args[3], defined_variables, args)
            out_res = format_semantic_argument("ucontrol", 4, args[4], defined_variables, args)
            return f"ucontrol.within({x}, {y}, {r}, {out_res})"
        elif action == "unbind":
            return "ucontrol.unbind()"


    if op == "set" and len(args) == 2:
        dest, val = args[0], format_operand(args[1])
        if dest.isidentifier() and not dest.startswith("@"):
            return f"{dest} = {val}"
        return f'set("{dest}", {val})'

    if op == "op" and len(args) >= 3:
        op_name = args[0]
        dest = args[1]
        a = format_operand(args[2])
        is_unary = op_name in UNARY_LOGIC_OPS
        if dest.isidentifier() and not dest.startswith("@"):
            if op_name in ("min", "max") and len(args) >= 4:
                b = format_operand(args[3])
                return f"{dest} = {op_name}({a}, {b})"
            if len(args) == 4 and not is_unary:
                b = format_operand(args[3])
                return f'{dest} = op("{op_name}", {a}, {b})'
            return f'{dest} = op("{op_name}", {a})'
        dest_str = repr(dest)
        if len(args) == 4 and not is_unary:
            b = format_operand(args[3])
            return f'op("{op_name}", {dest_str}, {a}, {b})'
        return f'op("{op_name}", {dest_str}, {a})'

    if op == "read" and len(args) == 3:
        dest = args[0]
        if dest.isidentifier() and not dest.startswith("@"):
            cell = format_semantic_argument("read", 1, args[1], defined_variables, args)
            addr = format_semantic_argument("read", 2, args[2], defined_variables, args)
            return f"{dest} = read({cell}, {addr})"

    if op == "sensor" and len(args) == 3:
        dest = args[0]
        if dest.isidentifier() and not dest.startswith("@"):
            block = format_semantic_argument("sensor", 1, args[1], defined_variables, args)
            prop = format_semantic_argument("sensor", 2, args[2], defined_variables, args)
            return f"{dest} = sensor({block}, {prop})"

    if op == "getlink" and len(args) == 2:
        dest = args[0]
        if dest.isidentifier() and not dest.startswith("@"):
            idx = format_semantic_argument("getlink", 1, args[1], defined_variables, args)
            return f"{dest} = getlink({idx})"

    if op == "lookup" and len(args) == 3:
        dest = args[1]
        if dest.isidentifier() and not dest.startswith("@"):
            type_ = format_semantic_argument("lookup", 0, args[0], defined_variables, args)
            idx = format_semantic_argument("lookup", 2, args[2], defined_variables, args)
            return f"{dest} = lookup({type_}, {idx})"

    if op == "packcolor" and len(args) == 5:
        dest = args[0]
        if dest.isidentifier() and not dest.startswith("@"):
            params = [format_semantic_argument("packcolor", i, args[i], defined_variables, args) for i in range(1, 5)]
            return f"{dest} = packcolor({', '.join(params)})"

    if op == "radar" and len(args) >= 7:
        dest = args[6]
        if dest.isidentifier() and not dest.startswith("@"):
            params = [format_semantic_argument("radar", i, args[i], defined_variables, args) for i in range(6)]
            return f"{dest} = radar({', '.join(params)})"

    if op == "uradar":
        if len(args) == 7:
            dest = args[6]
            if dest.isidentifier() and not dest.startswith("@"):
                params = [format_semantic_argument("uradar", i, args[i], defined_variables, args) for i in (0, 1, 2, 3, 5)]
                return f"{dest} = uradar({', '.join(params)})"
        elif len(args) == 6:
            dest = args[5]
            if dest.isidentifier() and not dest.startswith("@"):
                params = [format_semantic_argument("uradar", i, args[i], defined_variables, args) for i in range(5)]
                return f"{dest} = uradar({', '.join(params)})"


    if op == "select" and len(args) == 6:
        dest = args[0]
        if dest.isidentifier() and not dest.startswith("@"):
            cond = args[1]
            c0 = format_semantic_argument("select", 2, args[2], defined_variables, args)
            c1 = format_semantic_argument("select", 3, args[3], defined_variables, args)
            a = format_semantic_argument("select", 4, args[4], defined_variables, args)
            b = format_semantic_argument("select", 5, args[5], defined_variables, args)
            if cond == "notEqual" and args[3] in ("0", "false"):
                test = c0
            elif cond == "equal" and args[3] in ("0", "false"):
                test = f"not {c0}"
            elif cond in CMP_TO_PY:
                py_op = CMP_TO_PY[cond]
                test = f"{c0} {py_op} {c1}"
            elif cond == "always":
                test = "True"
            else:
                test = f"{c0} {cond} {c1}"
            return f"{dest} = {a} if {test} else {b}"

    if op == "noop":
        return "noop()"

    if op == "stop":
        return "stop()"

    if op == "end":
        return "end()"

    if op == "wait":
        arg = format_operand(args[0]) if args else "0.5"
        return f"wait({arg})"

    if op == "ulocate" and len(args) >= 8:
        locate = args[0]
        out_x, out_y, out_found, out_build = args[4], args[5], args[6], args[7]
        is_temp = is_compiler_temporary(out_build)
        targets = f"{out_x}, {out_y}, {out_found}" if is_temp else f"{out_x}, {out_y}, {out_found}, {out_build}"
        if locate == "building":
            group = format_semantic_argument("ulocate", 1, args[1], defined_variables, args)
            enemy = format_semantic_argument("ulocate", 2, args[2], defined_variables, args)
            return f"{targets} = ulocate.building({group}, {enemy})"
        elif locate == "ore":
            ore = format_semantic_argument("ulocate", 3, args[3], defined_variables, args)
            return f"{targets} = ulocate.ore({ore})"
        elif locate == "spawn":
            return f"{targets} = ulocate.spawn()"
        elif locate == "damaged":
            return f"{targets} = ulocate.damaged()"

    if op == "spawn" and len(args) == 7:
        dest = args[5]
        if dest.isidentifier() and not dest.startswith("@"):
            params = [format_semantic_argument("spawn", i, args[i], defined_variables, args) for i in (0, 1, 2, 3, 4, 6)]
            return f"{dest} = spawn({', '.join(params)})"

    if op == "bullet" and len(args) == 13:
        dest = args[0]
        if dest.isidentifier() and not dest.startswith("@"):
            params = [format_semantic_argument("bullet", i, args[i], defined_variables, args) for i in range(1, len(args))]
            return f"{dest} = bullet({', '.join(params)})"

    if op == "message" and len(args) == 3:
        type_ = format_semantic_argument("message", 0, args[0], defined_variables, args)
        duration = format_semantic_argument("message", 1, args[1], defined_variables, args)
        out_success = args[2]
        if out_success != "@wait" and out_success.isidentifier():
            return f"{out_success} = message({type_}, {duration})"
        elif duration == "3":
            return f"message({type_})"
        else:
            return f"message({type_}, {duration})"

    if op == "cutscene" and len(args) == 5:
        action = args[0]
        if action == "active":
            dest = args[1]
            if dest.isidentifier() and not dest.startswith("@"):
                return f"{dest} = cutscene.active()"
            return f"cutscene.active({dest})"
        elif action in ("getHud", "get_hud"):
            dest = args[1]
            if dest.isidentifier() and not dest.startswith("@"):
                return f"{dest} = cutscene.get_hud()"
            return f"cutscene.get_hud({dest})"
        elif action == "pan":
            x = format_semantic_argument("cutscene", 1, args[1], defined_variables, args)
            y = format_semantic_argument("cutscene", 2, args[2], defined_variables, args)
            speed = format_semantic_argument("cutscene", 3, args[3], defined_variables, args)
            if speed in ("0.06", "0.060000"):
                return f"cutscene.pan({x}, {y})"
            return f"cutscene.pan({x}, {y}, {speed})"
        elif action == "zoom":
            level = format_semantic_argument("cutscene", 1, args[1], defined_variables, args)
            return f"cutscene.zoom({level})"
        elif action == "stop":
            return "cutscene.stop()"
        elif action == "shake":
            amount = format_semantic_argument("cutscene", 1, args[1], defined_variables, args)
            duration = format_semantic_argument("cutscene", 2, args[2], defined_variables, args)
            return f"cutscene.shake({amount}, {duration})"
        elif action in ("setHud", "set_hud"):
            shown = format_semantic_argument("cutscene", 1, args[1], defined_variables, args)
            if shown == "1":
                return "cutscene.set_hud(True)"
            elif shown == "0":
                return "cutscene.set_hud(False)"
            return f"cutscene.set_hud({shown})"

    # Format arguments using semantic roles from SSOT metadata.
    # Generic control instructions preserve noncanonical zero dummy spellings.
    if op == "control":
        formatted_args = [
            format_control_operand(idx, arg, defined_variables, args)
            for idx, arg in enumerate(args)
        ]
    else:
        formatted_args = [
            format_semantic_argument(op, idx, arg, defined_variables, args)
            for idx, arg in enumerate(args)
        ]
    return f"{op}({', '.join(formatted_args)})"


class StructuredNode(ABC):
    """Base class for all structured control flow IR nodes."""

    @abstractmethod
    def to_python(self, indent: int = 0) -> str:
        """Render this node as Python source code with the given indentation level."""
        pass


@dataclass
class InstructionNode(StructuredNode):
    """Wraps an mlog instruction executed linearly."""
    instruction: MlogInstruction
    source_addresses: List[int] = field(default_factory=list)
    defined_variables: Optional[Set[str]] = None

    def __post_init__(self):
        if not self.source_addresses and self.instruction is not None:
            self.source_addresses = [self.instruction.address]

    def to_python(self, indent: int = 0) -> str:
        prefix = "    " * indent
        return prefix + instruction_to_python(self.instruction, self.defined_variables)


@dataclass
class PassNode(StructuredNode):
    """Represents an empty branch ('pass')."""
    source_addresses: List[int] = field(default_factory=list)

    def to_python(self, indent: int = 0) -> str:
        prefix = "    " * indent
        return prefix + "pass"


@dataclass
class BreakNode(StructuredNode):
    """Represents a 'break' statement targeting the innermost loop."""
    loop_id: Optional[int] = None
    source_addresses: List[int] = field(default_factory=list)

    def to_python(self, indent: int = 0) -> str:
        prefix = "    " * indent
        return prefix + "break"


@dataclass
class ContinueNode(StructuredNode):
    """Represents a 'continue' statement targeting the innermost loop header."""
    loop_id: Optional[int] = None
    source_addresses: List[int] = field(default_factory=list)

    def to_python(self, indent: int = 0) -> str:
        prefix = "    " * indent
        return prefix + "continue"


@dataclass
class AssignNode(StructuredNode):
    """Represents a variable assignment: target = value"""
    target: str
    value: Any  # Expr
    source_addresses: List[int] = field(default_factory=list)

    def to_python(self, indent: int = 0) -> str:
        prefix = "    " * indent
        val_str = self.value.to_python() if hasattr(self.value, "to_python") else str(self.value)
        if not self.target.isidentifier() or self.target.startswith("@"):
            return f'{prefix}set("{self.target}", {val_str})'
        return f"{prefix}{self.target} = {val_str}"


@dataclass
class ExprStmtNode(StructuredNode):
    """Represents an expression statement (e.g. function call)."""
    expr: Any  # Expr
    source_addresses: List[int] = field(default_factory=list)

    def to_python(self, indent: int = 0) -> str:
        prefix = "    " * indent
        val_str = self.expr.to_python() if hasattr(self.expr, "to_python") else str(self.expr)
        return f"{prefix}{val_str}"


@dataclass
class IfNode(StructuredNode):
    """Represents an if / elif / else statement."""
    condition_str: str
    then_body: List[StructuredNode] = field(default_factory=list)
    else_body: List[StructuredNode] = field(default_factory=list)
    is_elif: bool = False
    condition_expr: Optional[Any] = None
    source_addresses: List[int] = field(default_factory=list)

    @property
    def condition_text(self) -> str:
        if self.condition_expr is not None:
            return self.condition_expr.to_python()
        return self.condition_str

    def to_python(self, indent: int = 0) -> str:
        prefix = "    " * indent
        lines = []

        # Header: 'elif ...' if chained, else 'if ...'
        keyword = "elif" if self.is_elif else "if"
        lines.append(f"{prefix}{keyword} {self.condition_text}:")

        # Then body
        if not self.then_body:
            lines.append(f"{prefix}    pass")
        else:
            for node in self.then_body:
                lines.append(node.to_python(indent + 1))

        # Else body
        if self.else_body:
            # Check if else branch is another IfNode that should be emitted as elif
            if len(self.else_body) == 1 and isinstance(self.else_body[0], IfNode) and self.else_body[0].is_elif:
                lines.append(self.else_body[0].to_python(indent))
            else:
                lines.append(f"{prefix}else:")
                for node in self.else_body:
                    lines.append(node.to_python(indent + 1))

        return "\n".join(lines)


@dataclass
class WhileNode(StructuredNode):
    """Represents a while loop."""
    condition_str: str
    body: List[StructuredNode] = field(default_factory=list)
    loop_id: Optional[int] = None
    condition_expr: Optional[Any] = None
    source_addresses: List[int] = field(default_factory=list)

    @property
    def condition_text(self) -> str:
        if self.condition_expr is not None:
            return self.condition_expr.to_python()
        return self.condition_str

    def to_python(self, indent: int = 0) -> str:
        prefix = "    " * indent
        lines = [f"{prefix}while {self.condition_text}:"]

        if not self.body:
            lines.append(f"{prefix}    pass")
        else:
            for node in self.body:
                lines.append(node.to_python(indent + 1))

        return "\n".join(lines)


@dataclass
class UnstructuredNode(StructuredNode):
    """Represents an unstructured control flow fragment or irreducible CFG fallback.

    Preserves exact semantics through raw jumps / labels / comments without guessing.
    """
    reason: str
    instructions: List[MlogInstruction] = field(default_factory=list)
    source_addresses: List[int] = field(default_factory=list)
    defined_variables: Optional[Set[str]] = None

    def __post_init__(self):
        if not self.source_addresses and self.instructions:
            self.source_addresses = [i.address for i in self.instructions]

    def to_python(self, indent: int = 0) -> str:
        prefix = "    " * indent
        lines = [f"{prefix}# [UNSTRUCTURED REGION]: {self.reason}"]
        for instr in self.instructions:
            if instr.is_jump:
                formatted_args = [
                    format_semantic_argument("jump", idx, a, self.defined_variables, instr.args)
                    for idx, a in enumerate(instr.args)
                ]
                args_repr = ", ".join(formatted_args)
                lines.append(f"{prefix}jump({args_repr})  # addr {instr.address}")
            else:
                lines.append(f"{prefix}{instruction_to_python(instr, self.defined_variables)}")
        return "\n".join(lines)


@dataclass
class StructuredProgram:
    """Represents the complete structured program."""
    body: List[StructuredNode] = field(default_factory=list)
    is_fully_structured: bool = True
    unstructured_reasons: List[str] = field(default_factory=list)
    instruction_by_address: Dict[int, MlogInstruction] = field(default_factory=dict)
    defined_variables: Optional[Set[str]] = None

    def to_python(self, debug: bool = False) -> str:
        """Render the structured program into valid Python DSL code."""
        if debug:
            from .sourcemap import SourceMapEmitter
            code, _ = SourceMapEmitter(self.instruction_by_address, debug=True).emit_program(self)
            return code

        if not self.body:
            return "pass\n"

        from .dsl_symbols import format_import_header, get_required_dsl_imports

        body = "\n".join(node.to_python(indent=0) for node in self.body)
        symbols = get_required_dsl_imports(self, rendered_body=body)
        header = format_import_header(symbols)
        if header:
            return f"{header}\n\n{body}\n"
        return f"{body}\n"

    def generate_source_map(self, debug: bool = False) -> Tuple[str, Any]:
        """Render Python DSL code and return associated SourceMap."""
        from .sourcemap import SourceMapEmitter
        return SourceMapEmitter(self.instruction_by_address, debug=debug).emit_program(self)
