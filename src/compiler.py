"""Compiler: lowers validated Python AST to intermediate representation (IR)."""

import ast
from typing import List, Optional, Set, Tuple, Union

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
from .allocator import ArraySymbol, MemoryBlockAllocator
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
    if isinstance(node, ast.Constant) and isinstance(node.value, float):
        return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        return isinstance(node.operand, ast.Constant) and isinstance(node.operand.value, float)
    return False


def _get_literal_int(node: ast.AST) -> Optional[int]:
    """Extract integer value if node is a literal integer or negated literal integer."""
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        if isinstance(node.operand, ast.Constant) and isinstance(node.operand.value, int) and not isinstance(node.operand.value, bool):
            return -node.operand.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
        if isinstance(node.operand, ast.Constant) and isinstance(node.operand.value, int) and not isinstance(node.operand.value, bool):
            return node.operand.value
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


def _parse_array_call(compiler: "Compiler", call: ast.Call, loc: SourceLocation) -> Tuple[str, int, str]:
    """Parse and validate arguments to Array(block, size, dtype=...) or Array(block, size=..., dtype=...)."""
    block_node = None
    size_node = None
    dtype_node = None

    for kw in call.keywords:
        if kw.arg == "size":
            size_node = kw.value
        elif kw.arg == "block":
            block_node = kw.value
        elif kw.arg == "dtype":
            dtype_node = kw.value
        else:
            compiler.error(f"unexpected keyword argument '{kw.arg}' in Array()", kw)

    pos_args = list(call.args)
    if block_node is None and pos_args:
        block_node = pos_args.pop(0)
    if size_node is None and pos_args:
        size_node = pos_args.pop(0)
    if dtype_node is None and pos_args:
        dtype_node = pos_args.pop(0)

    if pos_args:
        compiler.error(f"Array() takes at most 3 arguments, got {len(call.args) + len(call.keywords)}", call)

    if block_node is None:
        compiler.error("missing required argument 'block' in Array()", call)
    if size_node is None:
        compiler.error("missing required argument 'size' in Array()", call)

    if not (isinstance(block_node, ast.Constant) and isinstance(block_node.value, str)):
        compiler.error("Array memory block must be a string literal (e.g. 'cell1', 'bank1')", block_node)
    block_name = block_node.value

    size_val = _get_literal_int(size_node)
    if size_val is None:
        compiler.error("Array size must be a positive integer literal", size_node)
    if size_val <= 0:
        compiler.error(f"Array size must be a positive integer (> 0), got {size_val}", size_node)

    dtype_str = "int"
    if dtype_node is not None:
        if isinstance(dtype_node, ast.Name):
            dtype_str = dtype_node.id
        elif isinstance(dtype_node, ast.Constant) and isinstance(dtype_node.value, str):
            dtype_str = dtype_node.value.lower()
        else:
            compiler.error("Array dtype must be int, float, or bool (e.g. dtype=float)", dtype_node)

        if dtype_str not in ("int", "float", "bool"):
            compiler.error(f"unsupported Array dtype '{dtype_str}': expected int, float, or bool", dtype_node)

    return block_name, size_val, dtype_str


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
        self.allocator = MemoryBlockAllocator()
        self._pre_allocated_arrays: Set[str] = set()

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
            if expr.id in self.allocator.arrays:
                self.error(f"cannot use Array '{expr.id}' directly in an expression; use element indexing '{expr.id}[i]'", expr)
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
            if isinstance(expr.func, ast.Name) and expr.func.id == "len":
                if len(expr.args) == 1 and isinstance(expr.args[0], ast.Name) and expr.args[0].id in self.allocator.arrays:
                    arr = self.allocator.arrays[expr.args[0].id]
                    size_str = str(arr.size)
                    if target_dest is not None:
                        self.instructions.append(IRSet(to=target_dest, from_=size_str, loc=loc))
                        return target_dest
                    return size_str
                else:
                    self.error("len() is only supported on Array objects", expr)
            return self.compile_call(expr, target_dest=target_dest)

        elif isinstance(expr, ast.Subscript):
            if not isinstance(expr.value, ast.Name):
                self.error("subscript indexing is only supported on simple array names", expr.value)
            arr_name = expr.value.id
            arr = self.allocator.get_array(arr_name)
            if arr is None:
                self.error(f"'{arr_name}' is not an Array", expr.value)

            if _is_literal_float(expr.slice):
                self.error("array index must be an integer, got float literal", expr.slice)
            if isinstance(expr.slice, ast.Constant) and isinstance(expr.slice.value, str):
                self.error("array index must be an integer, got string literal", expr.slice)
            if isinstance(expr.slice, ast.Constant) and isinstance(expr.slice.value, bool):
                self.error("array index must be an integer, got boolean literal", expr.slice)

            literal_idx = _get_literal_int(expr.slice)
            if literal_idx is not None:
                if literal_idx < 0 or literal_idx >= arr.size:
                    self.error(
                        f"array index out of bounds: index {literal_idx} is outside valid range [0, {arr.size}) for Array '{arr_name}'",
                        expr.slice,
                    )
                abs_addr = str(arr.base_offset + literal_idx)
                dest = target_dest if target_dest is not None else self.new_temp(loc)
                self.instructions.append(
                    IRRaw(opcode="read", args=[dest, arr.block, abs_addr], loc=loc)
                )
                return dest
            else:
                idx_expr = self.compile_expr(expr.slice)
                if arr.base_offset == 0:
                    addr = idx_expr
                else:
                    addr = self.new_temp(loc)
                    self.instructions.append(
                        IROp(op="add", dest=addr, a=idx_expr, b=str(arr.base_offset), loc=loc)
                    )
                dest = target_dest if target_dest is not None else self.new_temp(loc)
                self.instructions.append(
                    IRRaw(opcode="read", args=[dest, arr.block, addr], loc=loc)
                )
                return dest

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
        loc = self.loc(node)

        # Case 1: Array element assignment: a[i] = value
        if isinstance(target, ast.Subscript):
            if not isinstance(target.value, ast.Name):
                self.error("subscript assignment is only supported on simple array names", target.value)
            arr_name = target.value.id
            arr = self.allocator.get_array(arr_name)
            if arr is None:
                self.error(f"'{arr_name}' is not an Array", target.value)

            # Type checking on assigned value based on array dtype
            if arr.dtype == "int":
                if _is_literal_float(node.value):
                    self.error("Array only stores integers; float literal is not supported", node.value)
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    self.error("Array only stores integers; string literal is not supported", node.value)
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, bool):
                    self.error("Array only stores integers; boolean literal is not supported", node.value)
            elif arr.dtype == "float":
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    self.error("Array of type 'float' only stores numbers; string literal is not supported", node.value)
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, bool):
                    self.error("Array of type 'float' only stores numbers; boolean literal is not supported", node.value)
            elif arr.dtype == "bool":
                if _get_literal_int(node.value) is not None:
                    self.error("Array of type 'bool' only stores booleans; integer literal is not supported", node.value)
                if _is_literal_float(node.value):
                    self.error("Array of type 'bool' only stores booleans; float literal is not supported", node.value)
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    self.error("Array of type 'bool' only stores booleans; string literal is not supported", node.value)

            target_tmp = self.new_temp(loc) if isinstance(node.value, ast.Call) else None
            val = self.compile_expr(node.value, target_dest=target_tmp)

            if arr.dtype == "bool":
                # Normalize dynamic expressions to boolean (0 or 1) unless syntactically known to be boolean
                if not (
                    (isinstance(node.value, ast.Constant) and isinstance(node.value.value, bool))
                    or isinstance(node.value, ast.Compare)
                    or (isinstance(node.value, ast.UnaryOp) and isinstance(node.value.op, ast.Not))
                ):
                    bool_norm = self.new_temp(loc)
                    self.instructions.append(
                        IROp(op="notEqual", dest=bool_norm, a=val, b="0", loc=loc)
                    )
                    val = bool_norm

            # Check index type
            if _is_literal_float(target.slice):
                self.error("array index must be an integer, got float literal", target.slice)
            if isinstance(target.slice, ast.Constant) and isinstance(target.slice.value, str):
                self.error("array index must be an integer, got string literal", target.slice)
            if isinstance(target.slice, ast.Constant) and isinstance(target.slice.value, bool):
                self.error("array index must be an integer, got boolean literal", target.slice)

            literal_idx = _get_literal_int(target.slice)
            if literal_idx is not None:
                if literal_idx < 0 or literal_idx >= arr.size:
                    self.error(
                        f"array index out of bounds: index {literal_idx} is outside valid range [0, {arr.size}) for Array '{arr_name}'",
                        target.slice,
                    )
                abs_addr = str(arr.base_offset + literal_idx)
                self.instructions.append(
                    IRRaw(opcode="write", args=[val, arr.block, abs_addr], loc=loc)
                )
            else:
                idx_expr = self.compile_expr(target.slice)
                if arr.base_offset == 0:
                    addr = idx_expr
                else:
                    addr = self.new_temp(loc)
                    self.instructions.append(
                        IROp(op="add", dest=addr, a=idx_expr, b=str(arr.base_offset), loc=loc)
                    )
                self.instructions.append(
                    IRRaw(opcode="write", args=[val, arr.block, addr], loc=loc)
                )
            return

        # Case 2: Target is a simple Name
        assert isinstance(target, ast.Name)
        target_name = target.id

        # Check if value is an Array declaration: arr = Array(...)
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "Array":
            if self._current_function is not None:
                self.error("Array declaration is not allowed inside functions; declare arrays at the module level", node)
            if self._loop_stack:
                self.error("Array declaration is not allowed inside loops; declare arrays at the module level", node)
            if target_name in self._pre_allocated_arrays:
                return
            block_name, size_val, dtype_val = _parse_array_call(self, node.value, loc)
            self.allocator.allocate(name=target_name, block=block_name, size=size_val, dtype=dtype_val, loc=loc)
            return

        # Cannot reassign an existing Array variable
        if target_name in self.allocator.arrays:
            self.error(f"cannot reassign Array variable '{target_name}'", target)

        # Cannot assign an Array directly to another variable
        if isinstance(node.value, ast.Name) and node.value.id in self.allocator.arrays:
            self.error(
                f"cannot assign Array '{node.value.id}' directly to a variable; use element indexing '{node.value.id}[i]'",
                node.value,
            )

        formatted_target = self.format_name(target_name, target)
        self.compile_expr(node.value, target_dest=formatted_target)

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
        while_orelse = self.new_label("while_orelse") if node.orelse else while_end

        # Emit loop start label
        self.instructions.append(IRLabel(name=while_start, loc=loc))

        # Push loop context for break and continue
        # break jumps to while_end (skipping orelse)
        self._loop_stack.append((while_start, while_end))

        # Compile condition: if false, jump to while_orelse (or while_end if no orelse)
        self.compile_condition(node.test, true_label=None, false_label=while_orelse)

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
            self.instructions.append(IRLabel(name=while_orelse, loc=loc))
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
        for_orelse = self.new_label("for_orelse") if node.orelse else for_end

        # Push loop context: 'continue' jumps to for_latch (to run step increment),
        # 'break' jumps to for_end (skipping orelse)
        self._loop_stack.append((for_latch, for_end))

        # Loop condition check
        self.instructions.append(IRLabel(name=for_check, loc=loc))
        if static_step is not None:
            if static_step > 0:
                # If target >= stop, loop finishes -> jump to for_orelse
                self.instructions.append(
                    IRJump(target=for_orelse, cond="greaterThanEq", a=target_name, b=stop_val, loc=loc)
                )
            else:
                # Step is negative: if target <= stop, loop finishes -> jump to for_orelse
                self.instructions.append(
                    IRJump(target=for_orelse, cond="lessThanEq", a=target_name, b=stop_val, loc=loc)
                )
        else:
            # Dynamic step: branch on step > 0
            neg_step_lbl = self.new_label("for_neg_step")
            self.instructions.append(
                IRJump(target=neg_step_lbl, cond="lessThanEq", a=step_val, b="0", loc=loc)
            )
            # Positive step: if target >= stop -> for_orelse
            self.instructions.append(
                IRJump(target=for_orelse, cond="greaterThanEq", a=target_name, b=stop_val, loc=loc)
            )
            self.instructions.append(
                IRJump(target=for_body, cond="always", a="0", b="0", loc=loc)
            )
            # Negative step check
            self.instructions.append(IRLabel(name=neg_step_lbl, loc=loc))
            self.instructions.append(
                IRJump(target=for_orelse, cond="lessThanEq", a=target_name, b=stop_val, loc=loc)
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
            self.instructions.append(IRLabel(name=for_orelse, loc=loc))
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
            if isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name) and stmt.value.func.id == "Array":
                self.error("Array declaration must be assigned to a variable, e.g. 'a = Array(...)'", stmt)
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
        self.allocator = MemoryBlockAllocator()
        self._pre_allocated_arrays.clear()

        # Pre-register top-level Array declarations so they are visible to functions and global statements
        for stmt in tree.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                val = stmt.value
                if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id == "Array":
                    target_name = stmt.targets[0].id
                    loc = self.loc(stmt)
                    block_name, size_val, dtype_val = _parse_array_call(self, val, loc)
                    self.allocator.allocate(name=target_name, block=block_name, size=size_val, dtype=dtype_val, loc=loc)
                    self._pre_allocated_arrays.add(target_name)

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
