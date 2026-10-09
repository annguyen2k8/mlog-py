"""Compiler: lowers validated Python AST to intermediate representation (IR)."""

import ast
from typing import List, Optional, Tuple, Union

from .errors import CompileError, SourceLocation
from .ir import IRJump, IRLabel, IRNode, IROp, IRRaw, IRSet
from .mlog_registry import (
    BaseRegistry,
    ENUM_CLASS_TO_REGISTRY,
    REG_CONDITIONS,
    REG_CONTROL_PROPERTIES,
    REG_DRAW_TYPES,
    REG_LOGIC_OPS,
    REG_LOOKUP_TYPES,
    REG_RADAR_SORTS,
    REG_RADAR_TARGETS,
    REG_SENSOR_PROPERTIES,
    REG_UNIT_CONTROL,
    REG_UNIT_TYPES,
)
from .parser import get_loc, parse_and_validate



BIN_OP_MAP = {
    ast.Add: "add",
    ast.Sub: "sub",
    ast.Mult: "mul",
    ast.Div: "div",
    ast.FloorDiv: "idiv",
    ast.Mod: "mod",
    ast.Pow: "pow",
    ast.LShift: "shl",
    ast.RShift: "shr",
    ast.BitOr: "or",
    ast.BitAnd: "and",
    ast.BitXor: "xor",
}

BITWISE_BIN_OPS = (ast.BitAnd, ast.BitOr, ast.BitXor, ast.LShift, ast.RShift)
MIN_INT64 = -9223372036854775808
MAX_INT64 = 9223372036854775807


def _is_literal_float(node: ast.AST) -> bool:
    """Check if node is an explicit float literal."""
    return isinstance(node, ast.Constant) and isinstance(node.value, float)


def _get_literal_int(node: ast.AST) -> Optional[int]:
    """Extract integer value if node is a literal integer or negated literal integer."""
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        if isinstance(node.operand, ast.Constant) and isinstance(node.operand.value, int) and not isinstance(node.operand.value, bool):
            return -node.operand.value
    return None

CMP_OP_MAP = {
    ast.Eq: "equal",
    ast.NotEq: "notEqual",
    ast.Lt: "lessThan",
    ast.LtE: "lessThanEq",
    ast.Gt: "greaterThan",
    ast.GtE: "greaterThanEq",
    ast.Is: "strictEqual",
    ast.IsNot: "notEqual",
}

CMP_OP_INVERSE_MAP = {
    ast.Eq: "notEqual",
    ast.NotEq: "equal",
    ast.Lt: "greaterThanEq",
    ast.LtE: "greaterThan",
    ast.Gt: "lessThanEq",
    ast.GtE: "lessThan",
    ast.Is: "notEqual",
    ast.IsNot: "strictEqual",
}


class RawValue:
    """Wrapper indicating an explicitly unvalidated raw token from raw()."""

    def __init__(self, val: str):
        self.val = val

    def __str__(self) -> str:
        return self.val


class Compiler:
    """Lowers a validated Python AST into a list of IR instructions."""

    def __init__(self, filename: str = "<stdin>", allow_functions: bool = False):
        self.filename = filename
        self.allow_functions = allow_functions
        self.instructions: List[IRNode] = []
        self._temp_counter = 0
        self._label_counter = 0
        self._loop_stack: List[Tuple[str, str]] = []  # (start_label, end_label)
        self.functions: dict = {}  # name -> ast.FunctionDef
        self._current_function: Optional[str] = None

    def new_temp(self, loc: Optional[SourceLocation] = None) -> str:
        """Allocate a new deterministic temporary variable name."""
        name = f"__tmp{self._temp_counter}"
        self._temp_counter += 1
        return name

    def new_label(self, prefix: str = "L") -> str:
        """Allocate a new deterministic internal label name."""
        name = f"__{prefix}_{self._label_counter}"
        self._label_counter += 1
        return name

    def loc(self, node: ast.AST) -> SourceLocation:
        """Get source location for an AST node."""
        return get_loc(node, self.filename)

    def error(self, msg: str, node: ast.AST):
        """Raise a CompileError at the AST node's source location."""
        raise CompileError(msg, self.loc(node))

    def format_name(self, name: str, node: ast.AST) -> str:
        """Format an identifier name, mapping at_ prefix to @ if present."""
        if name.startswith("__tmp"):
            self.error(
                f"variable name '{name}' is reserved for compiler temporaries",
                node,
            )
        if name.startswith("at_"):
            return "@" + name[3:]
        if name in ("counter", "_counter"):
            return "@counter"
        return name

    def format_constant(self, val: object, loc: SourceLocation, is_negated: bool = False) -> str:
        """Format a constant literal for mlog."""
        if isinstance(val, bool):
            return "true" if val else "false"
        elif isinstance(val, int):
            max_limit = -MIN_INT64 if is_negated else MAX_INT64
            min_limit = MIN_INT64
            if val < min_limit or val > max_limit:
                raise CompileError(
                    f"integer literal {val} exceeds signed 64-bit integer range [{MIN_INT64}, {MAX_INT64}]",
                    loc,
                )
            return str(val)
        elif isinstance(val, float):
            return str(val)
        elif isinstance(val, str):
            if val.startswith("@"):
                return val
            escaped = val.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            return f'"{escaped}"'
        else:
            raise CompileError(f"unsupported constant value: {val!r}", loc)

    def compile_expr(self, expr: ast.expr, target_dest: Optional[str] = None) -> str:
        """Compile an expression, optionally writing result directly to target_dest.
        Returns the variable name or literal string holding the result.
        """
        loc = self.loc(expr)

        if isinstance(expr, ast.Constant):
            val_str = self.format_constant(expr.value, loc)
            if target_dest is not None:
                self.instructions.append(IRSet(to=target_dest, from_=val_str, loc=loc))
                return target_dest
            return val_str

        elif isinstance(expr, ast.Name):
            name_str = self.format_name(expr.id, expr)
            if target_dest is not None:
                self.instructions.append(IRSet(to=target_dest, from_=name_str, loc=loc))
                return target_dest
            return name_str

        elif isinstance(expr, ast.BinOp):
            op_cls = type(expr.op)
            if op_cls not in BIN_OP_MAP:
                self.error(f"unsupported binary operator: {op_cls.__name__}", expr)
            op_name = BIN_OP_MAP[op_cls]

            # Semantic hardening: bitwise operator checks on literal operands
            if op_cls in BITWISE_BIN_OPS:
                if _is_literal_float(expr.left) or _is_literal_float(expr.right):
                    self.error(
                        f"unsupported operand type for bitwise operator {op_cls.__name__}: float literal",
                        expr,
                    )
                if op_cls in (ast.LShift, ast.RShift):
                    shift_val = _get_literal_int(expr.right)
                    if shift_val is not None:
                        if shift_val < 0:
                            self.error("negative shift count is not supported", expr)
                        elif shift_val >= 64:
                            self.error(
                                f"shift count {shift_val} >= 64 exceeds 64-bit integer width",
                                expr,
                            )

            # Compile left and right operands to temporary or literal values
            left_val = self.compile_expr(expr.left)
            right_val = self.compile_expr(expr.right)

            dest = target_dest if target_dest is not None else self.new_temp(loc)
            self.instructions.append(
                IROp(op=op_name, dest=dest, a=left_val, b=right_val, loc=loc)
            )
            return dest

        elif isinstance(expr, ast.UnaryOp):
            if isinstance(expr.op, ast.USub):
                if isinstance(expr.operand, ast.Constant):
                    # -2**63 (-9223372036854775808): Arc/Mindustry parser fails on token
                    # "9223372036854775808" (returns Double.NaN -> parsed as identifier).
                    # Lowering -2**63 to `op shl dest 1 63` produces exact Long.MIN_VALUE
                    # in Mindustry runtime without relying on the problematic token.
                    if expr.operand.value == -MIN_INT64:
                        dest = target_dest if target_dest is not None else self.new_temp(loc)
                        self.instructions.append(
                            IROp(op="shl", dest=dest, a="1", b="63", loc=loc)
                        )
                        return dest
                    val = self.format_constant(expr.operand.value, self.loc(expr.operand), is_negated=True)
                else:
                    val = self.compile_expr(expr.operand)
                dest = target_dest if target_dest is not None else self.new_temp(loc)
                self.instructions.append(
                    IROp(op="sub", dest=dest, a="0", b=val, loc=loc)
                )
                return dest
            elif isinstance(expr.op, ast.UAdd):
                return self.compile_expr(expr.operand, target_dest=target_dest)
            elif isinstance(expr.op, ast.Invert):
                if _is_literal_float(expr.operand):
                    self.error(
                        "unsupported operand type for bitwise Invert (~): float literal",
                        expr,
                    )
                val = self.compile_expr(expr.operand)
                dest = target_dest if target_dest is not None else self.new_temp(loc)
                self.instructions.append(
                    IROp(op="not", dest=dest, a=val, b="0", loc=loc)
                )
                return dest
            elif isinstance(expr.op, ast.Not):
                val = self.compile_expr(expr.operand)
                dest = target_dest if target_dest is not None else self.new_temp(loc)
                self.instructions.append(
                    IROp(op="equal", dest=dest, a=val, b="0", loc=loc)
                )
                return dest
            else:
                self.error(f"unsupported unary operator: {type(expr.op).__name__}", expr)

        elif isinstance(expr, ast.Compare):
            if len(expr.ops) != 1 or len(expr.comparators) != 1:
                self.error("chained comparisons are not supported", expr)
            cmp_cls = type(expr.ops[0])
            if cmp_cls not in CMP_OP_MAP:
                self.error(
                    f"unsupported comparison operator: {cmp_cls.__name__}", expr
                )
            op_name = CMP_OP_MAP[cmp_cls]
            left_val = self.compile_expr(expr.left)
            right_val = self.compile_expr(expr.comparators[0])
            dest = target_dest if target_dest is not None else self.new_temp(loc)
            self.instructions.append(
                IROp(op=op_name, dest=dest, a=left_val, b=right_val, loc=loc)
            )
            return dest

        elif isinstance(expr, ast.BoolOp):
            dest = target_dest if target_dest is not None else self.new_temp(loc)
            end_lbl = self.new_label("boolop_end")
            if isinstance(expr.op, ast.And):
                for i, val in enumerate(expr.values):
                    v = self.compile_expr(val)
                    self.instructions.append(IRSet(to=dest, from_=v, loc=loc))
                    if i < len(expr.values) - 1:
                        self.instructions.append(
                            IRJump(target=end_lbl, cond="equal", a=dest, b="0", loc=loc)
                        )
            elif isinstance(expr.op, ast.Or):
                for i, val in enumerate(expr.values):
                    v = self.compile_expr(val)
                    self.instructions.append(IRSet(to=dest, from_=v, loc=loc))
                    if i < len(expr.values) - 1:
                        self.instructions.append(
                            IRJump(target=end_lbl, cond="notEqual", a=dest, b="0", loc=loc)
                        )
            self.instructions.append(IRLabel(name=end_lbl, loc=loc))
            return dest

        elif isinstance(expr, ast.Call):
            return self.compile_call(expr, target_dest=target_dest)

        elif isinstance(expr, ast.Attribute):
            val_str = self.compile_attribute(expr)
            if target_dest is not None:
                self.instructions.append(IRSet(to=target_dest, from_=val_str, loc=loc))
                return target_dest
            return val_str

        self.error(f"unsupported expression type: {type(expr).__name__}", expr)

    def compile_attribute(self, node: ast.Attribute) -> str:
        """Compile a DSL Enum attribute access, e.g. SensorProperty.HEALTH."""
        loc = self.loc(node)
        if isinstance(node.value, ast.Name):
            cls_name = node.value.id
            if cls_name in ENUM_CLASS_TO_REGISTRY:
                reg = ENUM_CLASS_TO_REGISTRY[cls_name]
                entry = reg.by_source_name.get(node.attr.upper())
                if entry is None:
                    self.error(f"unknown {cls_name} attribute '{node.attr}'", node)
                return entry.mlog_token
        self.error(f"unsupported attribute access '{node.attr}'", node)

    def validate_arg(
        self,
        val: Union[str, RawValue],
        registry: BaseRegistry,
        loc: SourceLocation,
    ) -> str:
        """Validate an intrinsic argument against a registry unless wrapped in raw()."""
        if isinstance(val, RawValue):
            return str(val)
        return registry.validate(str(val), loc)

    def format_intrinsic_arg(
        self,
        arg: ast.expr,
        is_ident: bool = False,
        is_string_literal: bool = False,
    ) -> Union[str, RawValue]:
        """Format an argument to a compiler intrinsic."""
        loc = self.loc(arg)
        # Explicit raw() escape hatch
        if (
            isinstance(arg, ast.Call)
            and isinstance(arg.func, ast.Name)
            and arg.func.id == "raw"
        ):
            if len(arg.args) != 1:
                self.error("raw() takes exactly 1 argument", arg)
            raw_str = self.format_intrinsic_arg(arg.args[0], is_ident=True)
            return RawValue(str(raw_str))

        if isinstance(arg, ast.Attribute):
            return self.compile_attribute(arg)

        if isinstance(arg, ast.Constant):
            val = arg.value
            if isinstance(val, str):
                if val.startswith("@"):
                    return val
                if is_ident or not is_string_literal:
                    return val
                escaped = (
                    val.replace("\\", "\\\\")
                    .replace('"', '\\"')
                    .replace("\n", "\\n")
                )
                return f'"{escaped}"'
            elif isinstance(val, bool):
                return "true" if val else "false"
            elif val is None:
                return "null"
            else:
                return str(val)
        elif isinstance(arg, ast.Name):
            return self.format_name(arg.id, arg)
        else:
            return self.compile_expr(arg)

    def compile_call(
        self, call: ast.Call, target_dest: Optional[str] = None
    ) -> str:
        """Compile a compiler intrinsic function call."""
        loc = self.loc(call)
        assert isinstance(call.func, ast.Name)
        func_name = call.func.id
        args = call.args

        if self.allow_functions and func_name in self.functions:
            fn_def = self.functions[func_name]
            param_names = [arg.arg for arg in fn_def.args.args]
            if len(args) != len(param_names):
                self.error(
                    f"function '{func_name}' takes {len(param_names)} arguments but {len(args)} were given",
                    call,
                )
            for param_name, arg_expr in zip(param_names, args):
                arg_val = self.compile_expr(arg_expr)
                self.instructions.append(IRSet(to=param_name, from_=arg_val, loc=loc))

            ret_site_lbl = self.new_label(f"ret_{func_name}")
            ret_var = f"__ret_{func_name}"
            self.instructions.append(IRSet(to=ret_var, from_=ret_site_lbl, loc=loc))
            self.instructions.append(
                IRJump(target=f"__fn_{func_name}", cond="always", a="0", b="0", loc=loc)
            )
            self.instructions.append(IRLabel(name=ret_site_lbl, loc=loc))

            if target_dest is not None:
                retval_var = f"__retval_{func_name}"
                self.instructions.append(IRSet(to=target_dest, from_=retval_var, loc=loc))
                return target_dest
            return "0"

        if func_name == "set":
            if len(args) != 2:
                self.error("invalid arguments for set: expected set(to, from)", call)
            to_str = str(self.format_intrinsic_arg(args[0], is_ident=True))
            from_str = str(self.format_intrinsic_arg(args[1], is_ident=False))
            self.instructions.append(IRSet(to=to_str, from_=from_str, loc=loc))
            if target_dest is not None and target_dest != to_str:
                self.instructions.append(
                    IRSet(to=target_dest, from_=to_str, loc=loc)
                )
            return to_str

        elif func_name == "op":
            if len(args) == 4:
                op_arg = self.format_intrinsic_arg(args[0], is_ident=True)
                op_name = self.validate_arg(op_arg, REG_LOGIC_OPS, self.loc(args[0]))
                dest = str(self.format_intrinsic_arg(args[1], is_ident=True))
                a = str(self.format_intrinsic_arg(args[2], is_ident=False))
                b = str(self.format_intrinsic_arg(args[3], is_ident=False))
                self.instructions.append(
                    IROp(op=op_name, dest=dest, a=a, b=b, loc=loc)
                )
                return dest
            elif len(args) == 3 and target_dest is not None:
                op_arg = self.format_intrinsic_arg(args[0], is_ident=True)
                op_name = self.validate_arg(op_arg, REG_LOGIC_OPS, self.loc(args[0]))
                a = str(self.format_intrinsic_arg(args[1], is_ident=False))
                b = str(self.format_intrinsic_arg(args[2], is_ident=False))
                self.instructions.append(
                    IROp(op=op_name, dest=target_dest, a=a, b=b, loc=loc)
                )
                return target_dest
            elif len(args) == 3 and target_dest is None:
                op_arg = self.format_intrinsic_arg(args[0], is_ident=True)
                op_name = self.validate_arg(op_arg, REG_LOGIC_OPS, self.loc(args[0]))
                dest = str(self.format_intrinsic_arg(args[1], is_ident=True))
                a = str(self.format_intrinsic_arg(args[2], is_ident=False))
                self.instructions.append(
                    IROp(op=op_name, dest=dest, a=a, b="0", loc=loc)
                )
                return dest
            elif len(args) == 2 and target_dest is not None:
                op_arg = self.format_intrinsic_arg(args[0], is_ident=True)
                op_name = self.validate_arg(op_arg, REG_LOGIC_OPS, self.loc(args[0]))
                a = str(self.format_intrinsic_arg(args[1], is_ident=False))
                self.instructions.append(
                    IROp(op=op_name, dest=target_dest, a=a, b="0", loc=loc)
                )
                return target_dest
            else:
                self.error(
                    "invalid arguments for op: expected op(op_name, dest, a, [b]) or dest = op(op_name, a, [b])",
                    call,
                )

        elif func_name in ("min", "max"):
            if len(args) != 2:
                self.error(
                    f"{func_name}() takes exactly 2 arguments ({len(args)} given)",
                    call,
                )
            a_val = str(self.compile_expr(args[0]))
            b_val = str(self.compile_expr(args[1]))
            dest = target_dest if target_dest is not None else self.new_temp(loc)
            self.instructions.append(
                IROp(op=func_name, dest=dest, a=a_val, b=b_val, loc=loc)
            )
            return dest

        elif func_name == "jump":
            if len(args) < 1 or len(args) > 4:
                self.error("invalid arguments for jump: expected jump(target, [cond], [a], [b])", call)
            target = str(self.format_intrinsic_arg(args[0], is_ident=True))
            if len(args) > 1:
                cond_arg = self.format_intrinsic_arg(args[1], is_ident=True)
                cond = self.validate_arg(cond_arg, REG_CONDITIONS, self.loc(args[1]))
            else:
                cond = "always"
            a = (
                str(self.format_intrinsic_arg(args[2], is_ident=False))
                if len(args) > 2
                else "0"
            )
            b = (
                str(self.format_intrinsic_arg(args[3], is_ident=False))
                if len(args) > 3
                else "0"
            )
            self.instructions.append(
                IRJump(target=target, cond=cond, a=a, b=b, loc=loc)
            )
            return "0"

        elif func_name == "read":
            if len(args) == 3:
                dest = str(self.format_intrinsic_arg(args[0], is_ident=True))
                cell = str(self.format_intrinsic_arg(args[1], is_ident=True))
                addr = str(self.format_intrinsic_arg(args[2], is_ident=False))
                self.instructions.append(
                    IRRaw(opcode="read", args=[dest, cell, addr], loc=loc)
                )
                return dest
            elif len(args) == 2 and target_dest is not None:
                cell = str(self.format_intrinsic_arg(args[0], is_ident=True))
                addr = str(self.format_intrinsic_arg(args[1], is_ident=False))
                self.instructions.append(
                    IRRaw(opcode="read", args=[target_dest, cell, addr], loc=loc)
                )
                return target_dest
            else:
                self.error(
                    "invalid arguments for read: expected read(dest, cell, address) or dest = read(cell, address)",
                    call,
                )

        elif func_name == "write":
            if len(args) != 3:
                self.error("invalid arguments for write: expected write(input, cell, address)", call)
            val = str(self.format_intrinsic_arg(args[0], is_ident=False))
            cell = str(self.format_intrinsic_arg(args[1], is_ident=True))
            addr = str(self.format_intrinsic_arg(args[2], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="write", args=[val, cell, addr], loc=loc)
            )
            return "0"

        elif func_name == "draw":
            if len(args) < 1 or len(args) > 7:
                self.error(
                    "invalid arguments for draw: expected draw(type, [x], [y], [p1], [p2], [p3], [p4])",
                    call,
                )
            type_arg = self.format_intrinsic_arg(args[0], is_ident=True)
            type_str = self.validate_arg(type_arg, REG_DRAW_TYPES, self.loc(args[0]))
            param_strs = [type_str]
            for i in range(1, 7):
                if i < len(args):
                    param_strs.append(
                        str(self.format_intrinsic_arg(args[i], is_ident=False))
                    )
                else:
                    param_strs.append("0")
            self.instructions.append(
                IRRaw(opcode="draw", args=param_strs, loc=loc)
            )
            return "0"

        elif func_name == "drawflush":
            if len(args) != 1:
                self.error("invalid arguments for drawflush: expected drawflush(display)", call)
            target = str(self.format_intrinsic_arg(args[0], is_ident=True))
            self.instructions.append(
                IRRaw(opcode="drawflush", args=[target], loc=loc)
            )
            return "0"

        elif func_name == "print":
            if len(args) != 1:
                self.error("invalid arguments for print: expected print(value)", call)
            val = str(self.format_intrinsic_arg(
                args[0], is_ident=False, is_string_literal=True
            ))
            self.instructions.append(
                IRRaw(opcode="print", args=[val], loc=loc)
            )
            return "0"

        elif func_name == "printflush":
            if len(args) != 1:
                self.error("invalid arguments for printflush: expected printflush(message)", call)
            target = str(self.format_intrinsic_arg(args[0], is_ident=True))
            self.instructions.append(
                IRRaw(opcode="printflush", args=[target], loc=loc)
            )
            return "0"

        elif func_name == "sensor":
            if len(args) == 3:
                dest = str(self.format_intrinsic_arg(args[0], is_ident=True))
                block = str(self.format_intrinsic_arg(args[1], is_ident=True))
                prop_arg = self.format_intrinsic_arg(args[2], is_ident=True)
                prop = self.validate_arg(prop_arg, REG_SENSOR_PROPERTIES, self.loc(args[2]))
                self.instructions.append(
                    IRRaw(opcode="sensor", args=[dest, block, prop], loc=loc)
                )
                return dest
            elif len(args) == 2 and target_dest is not None:
                block = str(self.format_intrinsic_arg(args[0], is_ident=True))
                prop_arg = self.format_intrinsic_arg(args[1], is_ident=True)
                prop = self.validate_arg(prop_arg, REG_SENSOR_PROPERTIES, self.loc(args[1]))
                self.instructions.append(
                    IRRaw(opcode="sensor", args=[target_dest, block, prop], loc=loc)
                )
                return target_dest
            else:
                self.error(
                    "invalid arguments for sensor: expected sensor(dest, block, prop) or dest = sensor(block, prop)",
                    call,
                )

        elif func_name == "control":
            if len(args) < 2 or len(args) > 6:
                self.error(
                    "invalid arguments for control: expected control(type, target, [p1], [p2], [p3], [p4])",
                    call,
                )
            type_arg = self.format_intrinsic_arg(args[0], is_ident=True)
            type_str = self.validate_arg(type_arg, REG_CONTROL_PROPERTIES, self.loc(args[0]))
            target = str(self.format_intrinsic_arg(args[1], is_ident=True))
            param_strs = [type_str, target]
            for i in range(2, 6):
                if i < len(args):
                    param_strs.append(
                        str(self.format_intrinsic_arg(args[i], is_ident=False))
                    )
                else:
                    param_strs.append("0")
            self.instructions.append(
                IRRaw(opcode="control", args=param_strs, loc=loc)
            )
            return "0"

        elif func_name == "ubind":
            if len(args) != 1:
                self.error("invalid arguments for ubind: expected ubind(unit_type)", call)
            unit_arg = self.format_intrinsic_arg(args[0], is_ident=True)
            unit_str = self.validate_arg(unit_arg, REG_UNIT_TYPES, self.loc(args[0]))
            self.instructions.append(
                IRRaw(opcode="ubind", args=[unit_str], loc=loc)
            )
            return "0"

        elif func_name == "ucontrol":
            if len(args) < 1 or len(args) > 6:
                self.error(
                    "invalid arguments for ucontrol: expected ucontrol(action, [p1], [p2], [p3], [p4], [p5])",
                    call,
                )
            type_arg = self.format_intrinsic_arg(args[0], is_ident=True)
            type_str = self.validate_arg(type_arg, REG_UNIT_CONTROL, self.loc(args[0]))
            param_strs = [type_str]
            for i in range(1, 6):
                if i < len(args):
                    param_strs.append(
                        str(self.format_intrinsic_arg(args[i], is_ident=False))
                    )
                else:
                    param_strs.append("0")
            self.instructions.append(
                IRRaw(opcode="ucontrol", args=param_strs, loc=loc)
            )
            return "0"

        elif func_name == "radar":
            if len(args) == 6 and target_dest is not None:
                t1 = self.validate_arg(self.format_intrinsic_arg(args[0], is_ident=True), REG_RADAR_TARGETS, self.loc(args[0]))
                t2 = self.validate_arg(self.format_intrinsic_arg(args[1], is_ident=True), REG_RADAR_TARGETS, self.loc(args[1]))
                t3 = self.validate_arg(self.format_intrinsic_arg(args[2], is_ident=True), REG_RADAR_TARGETS, self.loc(args[2]))
                sort = self.validate_arg(self.format_intrinsic_arg(args[3], is_ident=True), REG_RADAR_SORTS, self.loc(args[3]))
                turret = str(self.format_intrinsic_arg(args[4], is_ident=True))
                sort_order = str(self.format_intrinsic_arg(args[5], is_ident=False))
                self.instructions.append(
                    IRRaw(
                        opcode="radar",
                        args=[t1, t2, t3, sort, turret, sort_order, target_dest],
                        loc=loc,
                    )
                )
                return target_dest
            elif len(args) == 7:
                t1 = self.validate_arg(self.format_intrinsic_arg(args[0], is_ident=True), REG_RADAR_TARGETS, self.loc(args[0]))
                t2 = self.validate_arg(self.format_intrinsic_arg(args[1], is_ident=True), REG_RADAR_TARGETS, self.loc(args[1]))
                t3 = self.validate_arg(self.format_intrinsic_arg(args[2], is_ident=True), REG_RADAR_TARGETS, self.loc(args[2]))
                sort = self.validate_arg(self.format_intrinsic_arg(args[3], is_ident=True), REG_RADAR_SORTS, self.loc(args[3]))
                turret = str(self.format_intrinsic_arg(args[4], is_ident=True))
                sort_order = str(self.format_intrinsic_arg(args[5], is_ident=False))
                out = str(self.format_intrinsic_arg(args[6], is_ident=True))
                self.instructions.append(
                    IRRaw(
                        opcode="radar",
                        args=[t1, t2, t3, sort, turret, sort_order, out],
                        loc=loc,
                    )
                )
                return out
            else:
                self.error(
                    "invalid arguments for radar: expected radar(target1, target2, target3, sort, turret, sort_order, output) or output = radar(target1, target2, target3, sort, turret, sort_order)",
                    call,
                )

        elif func_name == "uradar":
            if len(args) == 5 and target_dest is not None:
                t1 = self.validate_arg(self.format_intrinsic_arg(args[0], is_ident=True), REG_RADAR_TARGETS, self.loc(args[0]))
                t2 = self.validate_arg(self.format_intrinsic_arg(args[1], is_ident=True), REG_RADAR_TARGETS, self.loc(args[1]))
                t3 = self.validate_arg(self.format_intrinsic_arg(args[2], is_ident=True), REG_RADAR_TARGETS, self.loc(args[2]))
                sort = self.validate_arg(self.format_intrinsic_arg(args[3], is_ident=True), REG_RADAR_SORTS, self.loc(args[3]))
                sort_order = str(self.format_intrinsic_arg(args[4], is_ident=False))
                self.instructions.append(
                    IRRaw(
                        opcode="uradar",
                        args=[t1, t2, t3, sort, "0", sort_order, target_dest],
                        loc=loc,
                    )
                )
                return target_dest
            elif len(args) == 6:
                t1 = self.validate_arg(self.format_intrinsic_arg(args[0], is_ident=True), REG_RADAR_TARGETS, self.loc(args[0]))
                t2 = self.validate_arg(self.format_intrinsic_arg(args[1], is_ident=True), REG_RADAR_TARGETS, self.loc(args[1]))
                t3 = self.validate_arg(self.format_intrinsic_arg(args[2], is_ident=True), REG_RADAR_TARGETS, self.loc(args[2]))
                sort = self.validate_arg(self.format_intrinsic_arg(args[3], is_ident=True), REG_RADAR_SORTS, self.loc(args[3]))
                sort_order = str(self.format_intrinsic_arg(args[4], is_ident=False))
                out = str(self.format_intrinsic_arg(args[5], is_ident=True))
                self.instructions.append(
                    IRRaw(
                        opcode="uradar",
                        args=[t1, t2, t3, sort, "0", sort_order, out],
                        loc=loc,
                    )
                )
                return out
            elif len(args) == 7:
                t1 = self.validate_arg(self.format_intrinsic_arg(args[0], is_ident=True), REG_RADAR_TARGETS, self.loc(args[0]))
                t2 = self.validate_arg(self.format_intrinsic_arg(args[1], is_ident=True), REG_RADAR_TARGETS, self.loc(args[1]))
                t3 = self.validate_arg(self.format_intrinsic_arg(args[2], is_ident=True), REG_RADAR_TARGETS, self.loc(args[2]))
                sort = self.validate_arg(self.format_intrinsic_arg(args[3], is_ident=True), REG_RADAR_SORTS, self.loc(args[3]))
                params = [
                    t1, t2, t3, sort,
                    str(self.format_intrinsic_arg(args[4], is_ident=False)),
                    str(self.format_intrinsic_arg(args[5], is_ident=False)),
                    str(self.format_intrinsic_arg(args[6], is_ident=True)),
                ]
                self.instructions.append(
                    IRRaw(opcode="uradar", args=params, loc=loc)
                )
                return params[-1]
            else:
                self.error(
                    "invalid arguments for uradar: expected uradar(target1, target2, target3, sort, sort_order, output) or output = uradar(target1, target2, target3, sort, sort_order)",
                    call,
                )

        elif func_name == "lookup":
            if len(args) == 3:
                type_arg = self.format_intrinsic_arg(args[0], is_ident=True)
                type_str = self.validate_arg(type_arg, REG_LOOKUP_TYPES, self.loc(args[0]))
                dest = str(self.format_intrinsic_arg(args[1], is_ident=True))
                idx = str(self.format_intrinsic_arg(args[2], is_ident=False))
                self.instructions.append(
                    IRRaw(opcode="lookup", args=[type_str, dest, idx], loc=loc)
                )
                return dest
            elif len(args) == 2 and target_dest is not None:
                type_arg = self.format_intrinsic_arg(args[0], is_ident=True)
                type_str = self.validate_arg(type_arg, REG_LOOKUP_TYPES, self.loc(args[0]))
                idx = str(self.format_intrinsic_arg(args[1], is_ident=False))
                self.instructions.append(
                    IRRaw(opcode="lookup", args=[type_str, target_dest, idx], loc=loc)
                )
                return target_dest
            else:
                self.error(
                    "invalid arguments for lookup: expected lookup(type, dest, index) or dest = lookup(type, index)",
                    call,
                )

        elif func_name == "packcolor":
            if len(args) == 5:
                dest = str(self.format_intrinsic_arg(args[0], is_ident=True))
                r = str(self.format_intrinsic_arg(args[1], is_ident=False))
                g = str(self.format_intrinsic_arg(args[2], is_ident=False))
                b = str(self.format_intrinsic_arg(args[3], is_ident=False))
                a = str(self.format_intrinsic_arg(args[4], is_ident=False))
                self.instructions.append(
                    IRRaw(opcode="packcolor", args=[dest, r, g, b, a], loc=loc)
                )
                return dest
            elif len(args) == 4 and target_dest is not None:
                r = str(self.format_intrinsic_arg(args[0], is_ident=False))
                g = str(self.format_intrinsic_arg(args[1], is_ident=False))
                b = str(self.format_intrinsic_arg(args[2], is_ident=False))
                a = str(self.format_intrinsic_arg(args[3], is_ident=False))
                self.instructions.append(
                    IRRaw(opcode="packcolor", args=[target_dest, r, g, b, a], loc=loc)
                )
                return target_dest
            else:
                self.error(
                    "invalid arguments for packcolor: expected packcolor(dest, r, g, b, a) or dest = packcolor(r, g, b, a)",
                    call,
                )

        elif func_name == "getlink":
            if len(args) == 2:
                dest = str(self.format_intrinsic_arg(args[0], is_ident=True))
                idx = str(self.format_intrinsic_arg(args[1], is_ident=False))
                self.instructions.append(
                    IRRaw(opcode="getlink", args=[dest, idx], loc=loc)
                )
                return dest
            elif len(args) == 1 and target_dest is not None:
                idx = str(self.format_intrinsic_arg(args[0], is_ident=False))
                self.instructions.append(
                    IRRaw(opcode="getlink", args=[target_dest, idx], loc=loc)
                )
                return target_dest
            else:
                self.error(
                    "invalid arguments for getlink: expected getlink(dest, index) or dest = getlink(index)",
                    call,
                )

        elif func_name == "ulocate":
            if len(args) != 8:
                self.error(
                    "invalid arguments for ulocate: expected ulocate(locate, flag, enemy, ore, outX, outY, outFound, outBuild)",
                    call,
                )
            params = [
                str(self.format_intrinsic_arg(a, is_ident=True)) for a in args
            ]
            self.instructions.append(
                IRRaw(opcode="ulocate", args=params, loc=loc)
            )
            return "0"

        elif func_name == "wait":
            if len(args) > 1:
                self.error("invalid arguments for wait: expected wait([seconds])", call)
            sec = (
                str(self.format_intrinsic_arg(args[0], is_ident=False))
                if args
                else "0.5"
            )
            self.instructions.append(
                IRRaw(opcode="wait", args=[sec], loc=loc)
            )
            return "0"

        elif func_name == "stop":
            if len(args) != 0:
                self.error("invalid arguments for stop: expected stop()", call)
            self.instructions.append(IRRaw(opcode="stop", args=[], loc=loc))
            return "0"

        elif func_name == "end":
            if len(args) != 0:
                self.error("invalid arguments for end: expected end()", call)
            self.instructions.append(IRRaw(opcode="end", args=[], loc=loc))
            return "0"

        else:
            self.error(f"unknown compiler intrinsic: '{func_name}'", call)

    def compile_assignment(self, node: ast.Assign):
        """Compile an assignment statement: target = value"""
        target = node.targets[0]
        assert isinstance(target, ast.Name)
        target_name = self.format_name(target.id, target)
        self.compile_expr(node.value, target_dest=target_name)

    def compile_condition(
        self,
        test: ast.expr,
        true_label: Optional[str] = None,
        false_label: Optional[str] = None,
    ):
        """Compile a boolean condition for control flow with strict short-circuiting."""
        loc = self.loc(test)

        # 1. 'not' expression
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            self.compile_condition(
                test.operand, true_label=false_label, false_label=true_label
            )
            return

        # 2. 'and' expression: short-circuit on false
        if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
            need_false_label = false_label is None
            f_lbl = (
                false_label if not need_false_label else self.new_label("and_false")
            )
            for i, val in enumerate(test.values):
                if i < len(test.values) - 1:
                    self.compile_condition(val, true_label=None, false_label=f_lbl)
                else:
                    last_false = f_lbl if not need_false_label else None
                    self.compile_condition(
                        val, true_label=true_label, false_label=last_false
                    )
            if need_false_label:
                self.instructions.append(IRLabel(name=f_lbl, loc=loc))
            return

        # 3. 'or' expression: short-circuit on true
        if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.Or):
            need_true_label = true_label is None
            t_lbl = true_label if not need_true_label else self.new_label("or_true")
            for i, val in enumerate(test.values):
                if i < len(test.values) - 1:
                    self.compile_condition(val, true_label=t_lbl, false_label=None)
                else:
                    last_true = t_lbl if not need_true_label else None
                    self.compile_condition(
                        val, true_label=last_true, false_label=false_label
                    )
            if need_true_label:
                self.instructions.append(IRLabel(name=t_lbl, loc=loc))
            return

        # 4. Comparison expression (e.g. a == b, a < b)
        if isinstance(test, ast.Compare):
            if len(test.ops) != 1 or len(test.comparators) != 1:
                self.error("chained comparisons are not supported", test)
            cmp_cls = type(test.ops[0])
            if cmp_cls not in CMP_OP_MAP:
                self.error(
                    f"unsupported comparison operator: {cmp_cls.__name__}", test
                )
            fwd_cond = CMP_OP_MAP[cmp_cls]
            inv_cond = CMP_OP_INVERSE_MAP[cmp_cls]

            left_val = self.compile_expr(test.left)
            right_val = self.compile_expr(test.comparators[0])

            if false_label is not None and true_label is None:
                # Jump to false_label if condition is FALSE (using inverse operator)
                self.instructions.append(
                    IRJump(
                        target=false_label,
                        cond=inv_cond,
                        a=left_val,
                        b=right_val,
                        loc=loc,
                    )
                )
            elif true_label is not None and false_label is None:
                # Jump to true_label if condition is TRUE (using forward operator)
                self.instructions.append(
                    IRJump(
                        target=true_label,
                        cond=fwd_cond,
                        a=left_val,
                        b=right_val,
                        loc=loc,
                    )
                )
            elif true_label is not None and false_label is not None:
                self.instructions.append(
                    IRJump(
                        target=true_label,
                        cond=fwd_cond,
                        a=left_val,
                        b=right_val,
                        loc=loc,
                    )
                )
                self.instructions.append(
                    IRJump(
                        target=false_label,
                        cond="always",
                        a="0",
                        b="0",
                        loc=loc,
                    )
                )
            return

        # 5. General truthiness expression (e.g. if x:)
        val = self.compile_expr(test)
        if false_label is not None and true_label is None:
            # If val == 0 / false, jump to false_label
            self.instructions.append(
                IRJump(target=false_label, cond="equal", a=val, b="0", loc=loc)
            )
        elif true_label is not None and false_label is None:
            # If val != 0 / false, jump to true_label
            self.instructions.append(
                IRJump(target=true_label, cond="notEqual", a=val, b="0", loc=loc)
            )
        elif true_label is not None and false_label is not None:
            self.instructions.append(
                IRJump(target=true_label, cond="notEqual", a=val, b="0", loc=loc)
            )
            self.instructions.append(
                IRJump(target=false_label, cond="always", a="0", b="0", loc=loc)
            )

    def compile_if(self, node: ast.If):
        """Compile an if / elif / else statement."""
        loc = self.loc(node)
        has_else = bool(node.orelse)
        else_label = (
            self.new_label("if_else") if has_else else self.new_label("if_end")
        )
        end_label = self.new_label("if_end") if has_else else else_label

        # Compile condition: jump to else_label when condition is false
        self.compile_condition(node.test, true_label=None, false_label=else_label)

        # Compile body
        for stmt in node.body:
            self.compile_stmt(stmt)

        if has_else:
            # Skip the else branch upon completing body
            self.instructions.append(
                IRJump(target=end_label, cond="always", a="0", b="0", loc=loc)
            )
            self.instructions.append(IRLabel(name=else_label, loc=loc))
            for stmt in node.orelse:
                self.compile_stmt(stmt)
            self.instructions.append(IRLabel(name=end_label, loc=loc))
        else:
            self.instructions.append(IRLabel(name=else_label, loc=loc))

    def compile_while(self, node: ast.While):
        """Compile a while loop."""
        loc = self.loc(node)
        while_start = self.new_label("while_start")
        while_end = self.new_label("while_end")

        # Emit loop start label
        self.instructions.append(IRLabel(name=while_start, loc=loc))

        # Push loop context for break and continue
        self._loop_stack.append((while_start, while_end))

        # Compile condition: if false, jump to while_end
        self.compile_condition(node.test, true_label=None, false_label=while_end)

        # Compile loop body
        for stmt in node.body:
            self.compile_stmt(stmt)

        # Jump back to loop start
        self.instructions.append(
            IRJump(target=while_start, cond="always", a="0", b="0", loc=loc)
        )

        # Pop loop context
        self._loop_stack.pop()

        # Compile orelse block if present (executed on normal termination)
        if node.orelse:
            for stmt in node.orelse:
                self.compile_stmt(stmt)

        # Emit loop end label
        self.instructions.append(IRLabel(name=while_end, loc=loc))

    def compile_for(self, node: ast.For):
        """Compile a for loop (e.g. for i in range(...): ...).

        Supports range(stop), range(start, stop), range(start, stop, step).
        Step can be positive, negative, or a dynamic expression.
        Continue statements safely target for_latch, executing the step increment
        before looping back to the condition check.
        """
        loc = self.loc(node)
        target_name = self.format_name(node.target.id, node.target)

        # Parse range arguments
        args = node.iter.args
        if len(args) == 1:
            start_expr = ast.Constant(value=0)
            stop_expr = args[0]
            step_expr = ast.Constant(value=1)
        elif len(args) == 2:
            start_expr = args[0]
            stop_expr = args[1]
            step_expr = ast.Constant(value=1)
        else:
            start_expr = args[0]
            stop_expr = args[1]
            step_expr = args[2]

        # 1. Initialize loop variable: target = start
        start_val = self.compile_expr(start_expr)
        self.instructions.append(IRSet(to=target_name, from_=start_val, loc=loc))

        # Evaluate stop and step values into registers/temporaries
        stop_val = self.compile_expr(stop_expr)
        step_val = self.compile_expr(step_expr)

        # Determine step sign statically if possible
        static_step = _get_literal_int(step_expr)
        if static_step == 0:
            self.error("range() step argument must not be zero", step_expr)

        for_check = self.new_label("for_check")
        for_body = self.new_label("for_body")
        for_latch = self.new_label("for_latch")
        for_end = self.new_label("for_end")

        # Push loop context: 'continue' jumps to for_latch (to run step increment),
        # 'break' jumps to for_end
        self._loop_stack.append((for_latch, for_end))

        # Loop condition check
        self.instructions.append(IRLabel(name=for_check, loc=loc))
        if static_step is not None:
            if static_step > 0:
                # If target >= stop, loop finishes -> jump to for_end
                self.instructions.append(
                    IRJump(target=for_end, cond="greaterThanEq", a=target_name, b=stop_val, loc=loc)
                )
            else:
                # Step is negative: if target <= stop, loop finishes -> jump to for_end
                self.instructions.append(
                    IRJump(target=for_end, cond="lessThanEq", a=target_name, b=stop_val, loc=loc)
                )
        else:
            # Dynamic step: branch on step > 0
            neg_step_lbl = self.new_label("for_neg_step")
            self.instructions.append(
                IRJump(target=neg_step_lbl, cond="lessThanEq", a=step_val, b="0", loc=loc)
            )
            # Positive step: if target >= stop -> for_end
            self.instructions.append(
                IRJump(target=for_end, cond="greaterThanEq", a=target_name, b=stop_val, loc=loc)
            )
            self.instructions.append(
                IRJump(target=for_body, cond="always", a="0", b="0", loc=loc)
            )
            # Negative step check
            self.instructions.append(IRLabel(name=neg_step_lbl, loc=loc))
            self.instructions.append(
                IRJump(target=for_end, cond="lessThanEq", a=target_name, b=stop_val, loc=loc)
            )
            self.instructions.append(IRLabel(name=for_body, loc=loc))

        # Loop body
        for stmt in node.body:
            self.compile_stmt(stmt)

        # Latch: increment target by step and jump back to for_check
        self.instructions.append(IRLabel(name=for_latch, loc=loc))
        self.instructions.append(
            IROp(op="add", dest=target_name, a=target_name, b=step_val, loc=loc)
        )
        self.instructions.append(
            IRJump(target=for_check, cond="always", a="0", b="0", loc=loc)
        )

        # Pop loop context
        self._loop_stack.pop()

        # Orelse block (executed on normal loop exhaustion)
        if node.orelse:
            for stmt in node.orelse:
                self.compile_stmt(stmt)

        # Loop end label
        self.instructions.append(IRLabel(name=for_end, loc=loc))

    def compile_break(self, node: ast.Break):
        """Compile a break statement."""
        loc = self.loc(node)
        if not self._loop_stack:
            self.error("'break' outside of loop", node)
        _, for_or_while_end = self._loop_stack[-1]
        self.instructions.append(
            IRJump(target=for_or_while_end, cond="always", a="0", b="0", loc=loc)
        )

    def compile_continue(self, node: ast.Continue):
        """Compile a continue statement."""
        loc = self.loc(node)
        if not self._loop_stack:
            self.error("'continue' outside of loop", node)
        latch_or_start, _ = self._loop_stack[-1]
        self.instructions.append(
            IRJump(target=latch_or_start, cond="always", a="0", b="0", loc=loc)
        )

    def compile_function_def(self, node: ast.FunctionDef):
        """Compile a user function definition."""
        fn_name = node.name
        self._current_function = fn_name
        fn_lbl = f"__fn_{fn_name}"
        self.instructions.append(IRLabel(name=fn_lbl, loc=self.loc(node)))

        has_explicit_return = False
        for stmt in node.body:
            if isinstance(stmt, ast.Return):
                has_explicit_return = True
            self.compile_stmt(stmt)

        # If last statement was not an explicit return, emit fallback return
        if not has_explicit_return:
            ret_var = f"__ret_{fn_name}"
            self.instructions.append(
                IRSet(to="@counter", from_=ret_var, loc=self.loc(node))
            )
        self._current_function = None

    def compile_return(self, node: ast.Return):
        """Compile a return statement inside a function."""
        loc = self.loc(node)
        if self._current_function is None:
            self.error("'return' outside of function", node)
        fn_name = self._current_function
        if node.value is not None:
            ret_val = self.compile_expr(node.value)
            retval_var = f"__retval_{fn_name}"
            self.instructions.append(IRSet(to=retval_var, from_=ret_val, loc=loc))
        ret_var = f"__ret_{fn_name}"
        self.instructions.append(IRSet(to="@counter", from_=ret_var, loc=loc))

    def compile_stmt(self, stmt: ast.stmt):
        """Compile a single statement."""
        if isinstance(stmt, ast.Assign):
            self.compile_assignment(stmt)
        elif isinstance(stmt, ast.If):
            self.compile_if(stmt)
        elif isinstance(stmt, ast.While):
            self.compile_while(stmt)
        elif isinstance(stmt, ast.For):
            self.compile_for(stmt)
        elif isinstance(stmt, ast.Break):
            self.compile_break(stmt)
        elif isinstance(stmt, ast.Continue):
            self.compile_continue(stmt)
        elif isinstance(stmt, ast.Expr):
            self.compile_expr(stmt.value)
        elif isinstance(stmt, ast.Pass):
            pass
        elif isinstance(stmt, (ast.Import, ast.ImportFrom)):
            pass
        elif isinstance(stmt, ast.FunctionDef):
            if not self.allow_functions:
                self.error("function definitions are not supported", stmt)
            self.compile_function_def(stmt)
        elif isinstance(stmt, ast.Return):
            if not self.allow_functions:
                self.error("return statements are not supported", stmt)
            self.compile_return(stmt)
        else:

            self.error(
                f"statement type '{type(stmt).__name__}' not supported in this phase",
                stmt,
            )

    def compile(self, tree: ast.Module) -> List[IRNode]:
        """Compile an AST module into a list of IR nodes."""
        self.instructions.clear()
        self._temp_counter = 0
        self._label_counter = 0
        self._loop_stack.clear()

        if self.allow_functions:
            functions = [s for s in tree.body if isinstance(s, ast.FunctionDef)]
            for fn in functions:
                self.functions[fn.name] = fn
            global_stmts = [s for s in tree.body if not isinstance(s, ast.FunctionDef)]

            if functions and global_stmts:
                main_lbl = self.new_label("main")
                self.instructions.append(
                    IRJump(target=main_lbl, cond="always", a="0", b="0", loc=self.loc(tree))
                )
                for fn in functions:
                    self.compile_function_def(fn)
                self.instructions.append(IRLabel(name=main_lbl, loc=self.loc(tree)))
                for stmt in global_stmts:
                    self.compile_stmt(stmt)
                return self.instructions

        for stmt in tree.body:
            self.compile_stmt(stmt)
        return self.instructions



def compile_source_to_ir(
    source: str,
    filename: str = "<stdin>",
    allow_functions: bool = False,
) -> List[IRNode]:
    """Parse, validate, and compile Python source code into IR."""
    tree = parse_and_validate(source, filename, allow_functions=allow_functions)
    compiler = Compiler(filename, allow_functions=allow_functions)
    return compiler.compile(tree)
