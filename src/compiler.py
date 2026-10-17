"""Compiler: lowers validated Python AST to intermediate representation (IR)."""

import ast
import math
from typing import List, Optional, Set, Tuple, Union

from .errors import CompileError, SourceLocation
from .ir import IRJump, IRLabel, IRNode, IROp, IRRaw, IRSet
from .mlog_registry import (
    BaseRegistry,
    ENUM_CLASS_TO_REGISTRY,
    REG_ALIGN,
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
    REG_TILE_LAYERS,
    REG_QUERY_SHAPES,
    REG_QUERY_TYPES,
    REG_STATUS_EFFECTS,
    REG_FETCH_TYPES,
    REG_LOGIC_RULES,
    REG_WEATHERS,
    REG_LOGIC_FX,
    REG_MESSAGE_TYPES,
    REG_CUTSCENE_ACTIONS,
    REG_MARKER_TYPES,
    REG_MARKER_CONTROLS,
    REG_TEAMS,
    BUILTIN_VARIABLES_DATA,
    to_snake,
)
from .mlog_registry_data import BUILTIN_CONSTANTS
from .allocator import ArraySymbol, MemoryBlockAllocator
from .parser import get_loc, parse_and_validate



BIN_OP_MAP = {
    ast.Add: "add",
    ast.Sub: "sub",
    ast.Mult: "mul",
    ast.Div: "div",
    ast.FloorDiv: "idiv",
    ast.Mod: "emod",
    ast.Pow: "pow",
    ast.LShift: "shl",
    ast.RShift: "shr",
    ast.BitOr: "or",
    ast.BitAnd: "and",
    ast.BitXor: "xor",
}

AUG_ASSIGN_OPS = {
    ast.Add: ("add", "+="),
    ast.Sub: ("sub", "-="),
    ast.Mult: ("mul", "*="),
    ast.Div: ("div", "/="),
    ast.FloorDiv: ("idiv", "//="),
    ast.Mod: ("emod", "%="),
    ast.Pow: ("pow", "**="),
    ast.LShift: ("shl", "<<="),
    ast.RShift: ("shr", ">>="),
    ast.BitOr: ("or", "|="),
    ast.BitAnd: ("and", "&="),
    ast.BitXor: ("xor", "^="),
}

BITWISE_BIN_OPS = (ast.BitAnd, ast.BitOr, ast.BitXor, ast.LShift, ast.RShift)
MIN_INT64 = -9223372036854775808
MAX_INT64 = 9223372036854775807
# IEEE-754 double safe integer limits (Mindustry runtime uses double for all numbers)
MAX_SAFE_INT = (1 << 53) - 1  # 9007199254740991
MIN_SAFE_INT = -MAX_SAFE_INT   # -9007199254740991


def _extract_const_val(node: ast.AST) -> Tuple[bool, object]:
    """Extract constant literal value from an AST node if it is a pure constant literal.
    Supports ast.Constant, as well as literal signed numbers (ast.UnaryOp with USub/UAdd).
    """
    if isinstance(node, ast.Constant) and (isinstance(node.value, (int, float, str, bool)) or node.value is None):
        return True, node.value
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant):
            val = node.operand.value
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                return True, -val
        elif isinstance(node.op, ast.UAdd) and isinstance(node.operand, ast.Constant):
            val = node.operand.value
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                return True, val
    return False, None


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

OP_METHOD_NAME_MAP = {
    "abs": "abs",
    "sign": "sign",
    "log": "log",
    "log10": "log10",
    "log_10": "log10",
    "floor": "floor",
    "ceil": "ceil",
    "round": "round",
    "sqrt": "sqrt",
    "rand": "rand",
    "sin": "sin",
    "cos": "cos",
    "tan": "tan",
    "asin": "asin",
    "acos": "acos",
    "atan": "atan",
    "add": "add",
    "sub": "sub",
    "mul": "mul",
    "div": "div",
    "idiv": "idiv",
    "mod": "mod",
    "emod": "emod",
    "pow": "pow",
    "equal": "equal",
    "not_equal": "notEqual",
    "notEqual": "notEqual",
    "land": "land",
    "less_than": "lessThan",
    "lessThan": "lessThan",
    "less_than_eq": "lessThanEq",
    "lessThanEq": "lessThanEq",
    "greater_than": "greaterThan",
    "greaterThan": "greaterThan",
    "greater_than_eq": "greaterThanEq",
    "greaterThanEq": "greaterThanEq",
    "strict_equal": "strictEqual",
    "strictEqual": "strictEqual",
    "shl": "shl",
    "shr": "shr",
    "ushr": "ushr",
    "xor": "xor",
    "max": "max",
    "min": "min",
    "angle": "angle",
    "angle_diff": "angleDiff",
    "angleDiff": "angleDiff",
    "len": "len",
    "length": "len",
    "noise": "noise",
    "logn": "logn",
}



def _is_pure_expression(node: ast.AST) -> bool:
    """Return True if node is guaranteed to be pure (no side effects, no potential runtime errors like division by zero)."""
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.Name):
        return True
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, (ast.UAdd, ast.USub, ast.Not, ast.Invert)):
            return _is_pure_expression(node.operand)
        return False
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            if isinstance(node.right, ast.Constant) and isinstance(node.right.value, (int, float)) and node.right.value != 0:
                return _is_pure_expression(node.left)
            return False
        return _is_pure_expression(node.left) and _is_pure_expression(node.right)
    if isinstance(node, ast.Compare):
        if len(node.ops) == 1 and len(node.comparators) == 1:
            return _is_pure_expression(node.left) and _is_pure_expression(node.comparators[0])
        return False
    if isinstance(node, ast.IfExp):
        return _is_pure_expression(node.test) and _is_pure_expression(node.body) and _is_pure_expression(node.orelse)
    return False


def _can_use_select(node: ast.IfExp) -> bool:
    """Check if Python ternary can safely lower to Mindustry select opcode preserving semantics."""
    return (
        _is_pure_expression(node.test)
        and _is_pure_expression(node.body)
        and _is_pure_expression(node.orelse)
    )


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


class ConstantFolder(ast.NodeTransformer):
    """AST transformer that safely folds pure compile-time constant expressions.

    Strictly preserves Python and Mindustry runtime semantics:
    - Arithmetic operations (+, -, *, /, //, %, **) on numbers and + on strings
    - Bitwise operations (&, |, ^, <<, >>) within IEEE-754 safe integer bounds
    - Unary operations (+, not)
    - Comparison operations (==, !=, <, <=, >, >=, is, is not) between literals
    - Boolean operations (and, or)
    - Preserves exact source location on folded nodes
    - Skips folding when operations may divide by zero or exceed IEEE-754 safe integer
      boundaries [-9007199254740991, 9007199254740991].
    - Raises CompileError when modulo by literal zero occurs.
    - Preserves standalone unary minus (-x) and bitwise not (~x) for native instruction lowering.
    - Preserves intrinsic min() and max() function calls for runtime op dispatch.
    - Never modifies control flow or performs dead code elimination.
    """

    def __init__(self, filename: str = "<stdin>"):
        super().__init__()
        self.filename = filename

    def visit_UnaryOp(self, node: ast.UnaryOp):
        self.generic_visit(node)
        if isinstance(node.op, ast.UAdd):
            if isinstance(node.operand, ast.Constant):
                val = node.operand.value
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    return ast.copy_location(ast.Constant(value=val), node)
        elif isinstance(node.op, ast.Not):
            ok, val = _extract_const_val(node.operand)
            # Mindustry strings are non-null objects and always truthy when compared with 0.
            # Only fold 'not' on numeric and boolean literals to prevent truthiness divergence.
            if ok and isinstance(val, (int, float, bool)):
                return ast.copy_location(ast.Constant(value=not val), node)
        return node

    def visit_BinOp(self, node: ast.BinOp):
        self.generic_visit(node)
        ok1, v1 = _extract_const_val(node.left)
        ok2, v2 = _extract_const_val(node.right)
        if not (ok1 and ok2):
            return node

        # Ensure safe integer ranges (IEEE-754 double precision in Mindustry runtime)
        if isinstance(v1, int) and not isinstance(v1, bool):
            if v1 < MIN_SAFE_INT or v1 > MAX_SAFE_INT:
                return node
        if isinstance(v2, int) and not isinstance(v2, bool):
            if v2 < MIN_SAFE_INT or v2 > MAX_SAFE_INT:
                return node

        res = None

        # Arithmetic & String
        if isinstance(node.op, ast.Add):
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)) and not isinstance(v1, bool) and not isinstance(v2, bool):
                res = v1 + v2
            elif isinstance(v1, str) and isinstance(v2, str):
                res = v1 + v2
        elif isinstance(node.op, ast.Sub):
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)) and not isinstance(v1, bool) and not isinstance(v2, bool):
                res = v1 - v2
        elif isinstance(node.op, ast.Mult):
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)) and not isinstance(v1, bool) and not isinstance(v2, bool):
                res = v1 * v2
        elif isinstance(node.op, ast.Div):
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)) and not isinstance(v1, bool) and not isinstance(v2, bool):
                if v2 != 0:
                    res = float(v1) / float(v2)
        elif isinstance(node.op, ast.FloorDiv):
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)) and not isinstance(v1, bool) and not isinstance(v2, bool):
                if v2 != 0:
                    res = v1 // v2
                    if isinstance(v1, int) and isinstance(v2, int):
                        res = int(res)
                    else:
                        res = float(res)
        elif isinstance(node.op, ast.Mod):
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)) and not isinstance(v1, bool) and not isinstance(v2, bool):
                if v2 == 0:
                    raise CompileError("modulo by zero", get_loc(node, self.filename))
                if (isinstance(v1, float) and (math.isnan(v1) or math.isinf(v1))) or (isinstance(v2, float) and (math.isnan(v2) or math.isinf(v2))):
                    return node
                try:
                    if isinstance(v1, int) and isinstance(v2, int):
                        res = int(v1 % v2)
                    else:
                        py_mod = v1 % v2
                        rem1 = math.fmod(v1, v2)
                        sum_val = rem1 + v2
                        engine_mod = math.fmod(sum_val, v2)
                        if (
                            not math.isnan(py_mod)
                            and not math.isnan(engine_mod)
                            and not math.isinf(py_mod)
                            and not math.isinf(engine_mod)
                            and py_mod == engine_mod
                            and math.copysign(1.0, py_mod) == math.copysign(1.0, engine_mod)
                        ):
                            res = float(py_mod)
                        else:
                            return node
                except ZeroDivisionError:
                    raise CompileError("modulo by zero", get_loc(node, self.filename))
                except ValueError:
                    return node
        elif isinstance(node.op, ast.Pow):
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)) and not isinstance(v1, bool) and not isinstance(v2, bool):
                if not (v1 == 0 and v2 <= 0) and not (v1 < 0 and not isinstance(v2, int)) and abs(v2) <= 100:
                    try:
                        calc = v1 ** v2
                        if not isinstance(calc, complex):
                            if isinstance(v1, int) and isinstance(v2, int) and v2 >= 0:
                                res = int(calc)
                            else:
                                res = float(calc)
                    except Exception:
                        pass
        elif isinstance(node.op, ast.BitAnd):
            if isinstance(v1, int) and isinstance(v2, int):
                res = v1 & v2
                if isinstance(v1, bool) and isinstance(v2, bool):
                    res = bool(res)
        elif isinstance(node.op, ast.BitOr):
            if isinstance(v1, int) and isinstance(v2, int):
                res = v1 | v2
                if isinstance(v1, bool) and isinstance(v2, bool):
                    res = bool(res)
        elif isinstance(node.op, ast.BitXor):
            if isinstance(v1, int) and isinstance(v2, int):
                res = v1 ^ v2
                if isinstance(v1, bool) and isinstance(v2, bool):
                    res = bool(res)
        elif isinstance(node.op, ast.LShift):
            if isinstance(v1, int) and isinstance(v2, int) and not isinstance(v1, bool) and not isinstance(v2, bool):
                if 0 <= v2 < 64:
                    res = v1 << v2
        elif isinstance(node.op, ast.RShift):
            if isinstance(v1, int) and isinstance(v2, int) and not isinstance(v1, bool) and not isinstance(v2, bool):
                if 0 <= v2 < 64:
                    res = v1 >> v2

        if res is not None:
            if isinstance(res, int) and not isinstance(res, bool):
                if res < MIN_SAFE_INT or res > MAX_SAFE_INT:
                    return node
            if isinstance(res, float):
                if math.isnan(res) or math.isinf(res):
                    return node
            return ast.copy_location(ast.Constant(value=res), node)
        return node

    def visit_Compare(self, node: ast.Compare):
        self.generic_visit(node)
        if len(node.ops) == 1 and len(node.comparators) == 1:
            ok1, v1 = _extract_const_val(node.left)
            ok2, v2 = _extract_const_val(node.comparators[0])
            if ok1 and ok2:
                if isinstance(v1, int) and not isinstance(v1, bool) and (v1 < MIN_SAFE_INT or v1 > MAX_SAFE_INT):
                    return node
                if isinstance(v2, int) and not isinstance(v2, bool) and (v2 < MIN_SAFE_INT or v2 > MAX_SAFE_INT):
                    return node
                op = node.ops[0]
                res = None
                types_ok = (
                    (isinstance(v1, (int, float)) and isinstance(v2, (int, float)))
                    or (isinstance(v1, str) and isinstance(v2, str))
                    or (isinstance(v1, bool) and isinstance(v2, bool))
                    or ((v1 is None or v2 is None) and isinstance(op, (ast.Is, ast.IsNot)))
                )
                if types_ok:
                    if isinstance(op, ast.Eq): res = (v1 == v2)
                    elif isinstance(op, ast.NotEq): res = (v1 != v2)
                    elif isinstance(op, ast.Lt): res = (v1 < v2)
                    elif isinstance(op, ast.LtE): res = (v1 <= v2)
                    elif isinstance(op, ast.Gt): res = (v1 > v2)
                    elif isinstance(op, ast.GtE): res = (v1 >= v2)
                    elif isinstance(op, ast.Is): res = (v1 is v2)
                    elif isinstance(op, ast.IsNot): res = (v1 is not v2)
                if res is not None:
                    return ast.copy_location(ast.Constant(value=bool(res)), node)
        return node

    def visit_BoolOp(self, node: ast.BoolOp):
        self.generic_visit(node)
        extracted = [_extract_const_val(v) for v in node.values]
        if all(ok for ok, _ in extracted):
            vals = [val for _, val in extracted]
            # Mindustry strings are non-null objects and always truthy when compared with 0 ("" != 0 is true).
            # Skip folding when any operand is a string to allow Mindustry runtime to evaluate it natively.
            if any(isinstance(val, str) for val in vals):
                return node
            if isinstance(node.op, ast.And):
                res = vals[0]
                for v in vals[1:]:
                    if not res:
                        break
                    res = v
                return ast.copy_location(ast.Constant(value=res), node)
            elif isinstance(node.op, ast.Or):
                res = vals[0]
                for v in vals[1:]:
                    if res:
                        break
                    res = v
                return ast.copy_location(ast.Constant(value=res), node)
        return node

    def visit_IfExp(self, node: ast.IfExp):
        self.generic_visit(node)
        ok, test_val = _extract_const_val(node.test)
        if ok and (isinstance(test_val, (int, float, bool)) or test_val is None):
            if test_val:
                return ast.copy_location(node.body, node)
            else:
                return ast.copy_location(node.orelse, node)
        return node


def fold_constants(tree: ast.AST, filename: str = "<stdin>") -> ast.AST:
    """Fold pure compile-time constant expressions in an AST."""
    return ConstantFolder(filename).visit(tree)


class Compiler:
    """Lowers a validated Python AST into a list of IR instructions."""

    def __init__(
        self,
        filename: str = "<stdin>",
        allow_functions: bool = False,
        fold_constants: bool = True,
    ):
        self.filename = filename
        self.allow_functions = allow_functions
        self.fold_constants = fold_constants
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
        """Format an identifier name."""
        if name.startswith("__tmp"):
            self.error(
                f"variable name '{name}' is reserved for compiler temporaries",
                node,
            )
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
            escaped = (
                val.replace("\r\n", "\n")
                .replace("\r", "\n")
                .replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\n", "\\n")
            )
            return f'"{escaped}"'
        elif val is None:
            return "null"
        elif val is Ellipsis:
            raise CompileError(
                "Ellipsis (...) is only supported as a placeholder statement, not as an expression value",
                loc,
            )
        else:
            raise CompileError(f"unsupported constant value: {val!r}", loc)

    def compile_expr(
        self, expr: ast.expr, target_dest: Optional[str] = None, is_statement: bool = False
    ) -> str:
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
            dest = target_dest if target_dest is not None else self.new_temp(loc)
            left_val = self.compile_expr(expr.left)
            right_val = self.compile_expr(expr.comparators[0])

            if cmp_cls is ast.IsNot:
                # Mindustry lacks op strictNotEqual. Emitting op notEqual causes engine bugs when
                # comparing number with null (e.g. 0 not null -> 0 in JVM).
                # To guarantee 100% sound semantics: op strictEqual temp left right followed by op equal dest temp 0.
                tmp = self.new_temp(loc)
                self.instructions.append(
                    IROp(op="strictEqual", dest=tmp, a=left_val, b=right_val, loc=loc)
                )
                self.instructions.append(
                    IROp(op="equal", dest=dest, a=tmp, b="0", loc=loc)
                )
                return dest

            if cmp_cls not in CMP_OP_MAP:
                self.error(
                    f"unsupported comparison operator: {cmp_cls.__name__}", expr
                )
            op_name = CMP_OP_MAP[cmp_cls]
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
            if isinstance(expr.func, ast.Name) and expr.func.id == "raw":
                return self.compile_raw_value(expr, target_dest=target_dest)
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
            return self.compile_call(
                expr, target_dest=target_dest, is_statement=is_statement
            )

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

        elif isinstance(expr, ast.IfExp):
            return self.compile_if_exp(expr, target_dest=target_dest)

        elif isinstance(expr, ast.JoinedStr):
            self.error("f-strings cannot be assigned to variables (Mindustry Logic only supports string formatting via the print buffer)", expr)

        self.error(f"unsupported expression type: {type(expr).__name__}", expr)

    def compile_if_exp(self, node: ast.IfExp, target_dest: Optional[str] = None) -> str:
        """Compile a Python ternary expression (a if cond else b).

        If condition and both branches are pure expressions without side effects,
        lower directly to Mindustry 'select' opcode (select dest op comp0 comp1 a b).
        If any expression may have side effects or runtime risks (calls, variable division, subscripts),
        lower using branching jumps with strict short-circuiting.
        """
        loc = self.loc(node)
        dest = target_dest if target_dest is not None else self.new_temp(loc)

        if _can_use_select(node):
            if isinstance(node.test, ast.Compare) and len(node.test.ops) == 1 and len(node.test.comparators) == 1:
                cmp_cls = type(node.test.ops[0])
                if cmp_cls is ast.IsNot:
                    comp0 = self.compile_expr(node.test.left)
                    comp1 = self.compile_expr(node.test.comparators[0])
                    a_val = self.compile_expr(node.body)
                    b_val = self.compile_expr(node.orelse)
                    # Mindustry lacks strictNotEqual opcode. Inverting strictEqual (comp0 === comp1 ? b : a)
                    # perfectly models 'comp0 is not comp1' without falling into Mindustry's '0 not null' bug.
                    self.instructions.append(
                        IRRaw(opcode="select", args=[dest, "strictEqual", comp0, comp1, b_val, a_val], loc=loc)
                    )
                    return dest
                elif cmp_cls in CMP_OP_MAP:
                    cond_op = CMP_OP_MAP[cmp_cls]
                    comp0 = self.compile_expr(node.test.left)
                    comp1 = self.compile_expr(node.test.comparators[0])
                    a_val = self.compile_expr(node.body)
                    b_val = self.compile_expr(node.orelse)
                    self.instructions.append(
                        IRRaw(opcode="select", args=[dest, cond_op, comp0, comp1, a_val, b_val], loc=loc)
                    )
                    return dest

            if isinstance(node.test, ast.UnaryOp) and isinstance(node.test.op, ast.Not):
                comp0 = self.compile_expr(node.test.operand)
                a_val = self.compile_expr(node.body)
                b_val = self.compile_expr(node.orelse)
                self.instructions.append(
                    IRRaw(opcode="select", args=[dest, "equal", comp0, "0", a_val, b_val], loc=loc)
                )
                return dest

            cond_val = self.compile_expr(node.test)
            a_val = self.compile_expr(node.body)
            b_val = self.compile_expr(node.orelse)
            self.instructions.append(
                IRRaw(opcode="select", args=[dest, "notEqual", cond_val, "0", a_val, b_val], loc=loc)
            )
            return dest

        # Branching ternary with strict short-circuiting
        else_lbl = self.new_label("tern_else")
        end_lbl = self.new_label("tern_end")

        self.compile_condition(node.test, true_label=None, false_label=else_lbl)

        body_val = self.compile_expr(node.body, target_dest=dest)
        if body_val != dest:
            self.instructions.append(IRSet(to=dest, from_=body_val, loc=loc))
        self.instructions.append(
            IRJump(target=end_lbl, cond="always", a="0", b="0", loc=loc)
        )

        self.instructions.append(IRLabel(name=else_lbl, loc=loc))
        orelse_val = self.compile_expr(node.orelse, target_dest=dest)
        if orelse_val != dest:
            self.instructions.append(IRSet(to=dest, from_=orelse_val, loc=loc))
        self.instructions.append(IRLabel(name=end_lbl, loc=loc))

        return dest

    def compile_attribute(self, node: ast.Attribute) -> str:
        """Compile a DSL Enum or Vars attribute access, e.g. SensorProperty.HEALTH or Vars.tick."""
        loc = self.loc(node)
        if isinstance(node.value, ast.Name):
            cls_name = node.value.id
            if cls_name == "Vars":
                token = BUILTIN_VARIABLES_DATA.get(node.attr)
                if token is None:
                    self.error(f"unknown Mindustry built-in variable: 'Vars.{node.attr}'", node)
                return token.token
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

        is_const, const_val = _extract_const_val(arg)
        if is_const and isinstance(const_val, (int, float)) and not isinstance(const_val, bool):
            return str(const_val)

        if isinstance(arg, ast.Constant):
            val = arg.value
            if val is Ellipsis:
                self.error(
                    "Ellipsis (...) is only supported as a placeholder statement, not as an expression value",
                    arg,
                )
            if isinstance(val, str):
                if is_string_literal:
                    escaped = (
                        val.replace("\r\n", "\n")
                        .replace("\r", "\n")
                        .replace("\\", "\\\\")
                        .replace('"', '\\"')
                        .replace("\n", "\\n")
                    )
                    return f'"{escaped}"'
                if is_ident:
                    return val
                escaped = (
                    val.replace("\r\n", "\n")
                    .replace("\r", "\n")
                    .replace("\\", "\\\\")
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

    def compile_raw_value(self, call: ast.Call, target_dest: Optional[str] = None) -> str:
        """Compile raw("<token>") used as a standalone value expression.

        ``raw()`` is the explicit escape hatch for emitting a bare mlog operand token
        that has no registry representation. As an assignment target it must produce a
        single ``set`` instruction; nesting it inside arithmetic is rejected because a
        Mindustry instruction operand cannot hold a compound expression.
        """
        if not isinstance(call, ast.Call):
            self.error("raw() expects exactly 1 string argument", call)
        if len(call.args) != 1 or call.keywords:
            self.error("raw() expects exactly 1 string argument and no keyword arguments", call)
        arg = call.args[0]
        if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
            self.error("raw() expects a string literal, e.g. raw(\"@copper\")", arg)
        token = str(self.format_intrinsic_arg(arg, is_ident=True))
        if target_dest is not None:
            self.instructions.append(IRSet(to=target_dest, from_=token, loc=self.loc(call)))
            return target_dest
        return token

    def compile_call(
        self,
        call: ast.Call,
        target_dest: Optional[str] = None,
        is_statement: bool = False,
    ) -> str:
        """Compile a compiler intrinsic function call."""
        loc = self.loc(call)
        if isinstance(call.func, ast.Attribute):
            if isinstance(call.func.value, ast.Name):
                ns = call.func.value.id
                if ns == "draw":
                    return self.compile_draw_method(call, target_dest=target_dest, is_statement=is_statement)
                elif ns == "ucontrol":
                    return self.compile_ucontrol_method(call, target_dest=target_dest, is_statement=is_statement)
                elif ns == "ulocate":
                    return self.compile_ulocate_method(call, target_dest=target_dest, is_statement=is_statement)
                elif ns == "op":
                    return self.compile_op_method(call, target_dest=target_dest, is_statement=is_statement)
                elif ns == "cutscene":
                    return self.compile_cutscene_method(call, target_dest=target_dest, is_statement=is_statement)
                elif ns == "sound":
                    return self.compile_sound_method(call, target_dest=target_dest, is_statement=is_statement)
                elif ns == "music":
                    return self.compile_music_method(call, target_dest=target_dest, is_statement=is_statement)
                elif ns == "marker":
                    return self.compile_marker_method(call, target_dest=target_dest, is_statement=is_statement)
            self.error(
                f"unsupported method call on '{call.func.value.id if isinstance(call.func.value, ast.Name) else 'object'}'",
                call,
            )

        if not isinstance(call.func, ast.Name):
            self.error("unsupported function call expression", call)

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
            if not args:
                self.error(
                    "invalid arguments for op: expected op(op_name, dest, a, [b]) or dest = op(op_name, a, [b])",
                    call,
                )

            op_arg = self.format_intrinsic_arg(args[0], is_ident=True)
            op_name = self.validate_arg(op_arg, REG_LOGIC_OPS, self.loc(args[0]))
            is_unary = REG_LOGIC_OPS.is_unary(op_name)

            if len(args) == 4:
                dest = str(self.format_intrinsic_arg(args[1], is_ident=True))
                a = str(self.format_intrinsic_arg(args[2], is_ident=False))
                b = str(self.format_intrinsic_arg(args[3], is_ident=False)) if not is_unary else "0"
                self.instructions.append(
                    IROp(op=op_name, dest=dest, a=a, b=b, loc=loc)
                )
                return dest
            elif len(args) == 3:
                if is_unary:
                    dest = str(self.format_intrinsic_arg(args[1], is_ident=True))
                    a = str(self.format_intrinsic_arg(args[2], is_ident=False))
                    self.instructions.append(
                        IROp(op=op_name, dest=dest, a=a, b="0", loc=loc)
                    )
                    return dest
                else:
                    dest = target_dest if target_dest is not None else self.new_temp(loc)
                    a = str(self.format_intrinsic_arg(args[1], is_ident=False))
                    b = str(self.format_intrinsic_arg(args[2], is_ident=False))
                    self.instructions.append(
                        IROp(op=op_name, dest=dest, a=a, b=b, loc=loc)
                    )
                    return dest
            elif len(args) == 2:
                if is_unary:
                    dest = target_dest if target_dest is not None else self.new_temp(loc)
                    a = str(self.format_intrinsic_arg(args[1], is_ident=False))
                    self.instructions.append(
                        IROp(op=op_name, dest=dest, a=a, b="0", loc=loc)
                    )
                    return dest
                else:
                    self.error(
                        f"binary operation '{op_name}' requires 2 operands, got 1",
                        call,
                    )
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
            elif len(args) == 2 and (target_dest is not None or not is_statement):
                dest = target_dest if target_dest is not None else self.new_temp(loc)
                cell = str(self.format_intrinsic_arg(args[0], is_ident=True))
                addr = str(self.format_intrinsic_arg(args[1], is_ident=False))
                self.instructions.append(
                    IRRaw(opcode="read", args=[dest, cell, addr], loc=loc)
                )
                return dest
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
                    if type_str == "print" and i == 3:
                        align_val = self.format_intrinsic_arg(args[i], is_ident=False)
                        raw_str = str(align_val)
                        if raw_str in REG_ALIGN.by_token or raw_str in REG_ALIGN.by_source_name:
                            param_strs.append(REG_ALIGN.get_token(raw_str))
                        elif raw_str.startswith('"') and raw_str.endswith('"'):
                            unquoted = raw_str[1:-1]
                            if unquoted in REG_ALIGN.by_token or unquoted in REG_ALIGN.by_source_name:
                                param_strs.append(REG_ALIGN.get_token(unquoted))
                            else:
                                param_strs.append(raw_str)
                        else:
                            param_strs.append(raw_str)
                    else:
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
            arg0 = args[0]
            if isinstance(arg0, ast.JoinedStr):
                return self.compile_fstring_print(arg0, loc)
            val = str(self.format_intrinsic_arg(
                arg0, is_ident=False, is_string_literal=True
            ))
            self.instructions.append(
                IRRaw(opcode="print", args=[val], loc=loc)
            )
            return "0"

        elif func_name == "printchar":
            if len(args) != 1:
                self.error("invalid arguments for printchar: expected printchar(value)", call)
            arg0 = args[0]
            if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str) and arg0.value.startswith("@"):
                val = arg0.value
            else:
                val = str(self.format_intrinsic_arg(arg0, is_ident=False))
            self.instructions.append(
                IRRaw(opcode="printchar", args=[val], loc=loc)
            )
            return "0"

        elif func_name == "format":
            if len(args) < 1:
                self.error("invalid arguments for format: expected at least 1 value, e.g. format(val) or format(v1, v2, ...)", call)
            for arg in args:
                val = str(self.format_intrinsic_arg(
                    arg, is_ident=False, is_string_literal=True
                ))
                self.instructions.append(
                    IRRaw(opcode="format", args=[val], loc=loc)
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
            elif len(args) == 2 and (target_dest is not None or not is_statement):
                dest = target_dest if target_dest is not None else self.new_temp(loc)
                block = str(self.format_intrinsic_arg(args[0], is_ident=True))
                prop_arg = self.format_intrinsic_arg(args[1], is_ident=True)
                prop = self.validate_arg(prop_arg, REG_SENSOR_PROPERTIES, self.loc(args[1]))
                self.instructions.append(
                    IRRaw(opcode="sensor", args=[dest, block, prop], loc=loc)
                )
                return dest
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
            if len(args) == 6 and (target_dest is not None or not is_statement):
                dest = target_dest if target_dest is not None else self.new_temp(loc)
                t1 = self.validate_arg(self.format_intrinsic_arg(args[0], is_ident=True), REG_RADAR_TARGETS, self.loc(args[0]))
                t2 = self.validate_arg(self.format_intrinsic_arg(args[1], is_ident=True), REG_RADAR_TARGETS, self.loc(args[1]))
                t3 = self.validate_arg(self.format_intrinsic_arg(args[2], is_ident=True), REG_RADAR_TARGETS, self.loc(args[2]))
                sort = self.validate_arg(self.format_intrinsic_arg(args[3], is_ident=True), REG_RADAR_SORTS, self.loc(args[3]))
                turret = str(self.format_intrinsic_arg(args[4], is_ident=True))
                sort_order = str(self.format_intrinsic_arg(args[5], is_ident=False))
                self.instructions.append(
                    IRRaw(
                        opcode="radar",
                        args=[t1, t2, t3, sort, turret, sort_order, dest],
                        loc=loc,
                    )
                )
                return dest
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
            if len(args) == 5 and (target_dest is not None or not is_statement):
                dest = target_dest if target_dest is not None else self.new_temp(loc)
                t1 = self.validate_arg(self.format_intrinsic_arg(args[0], is_ident=True), REG_RADAR_TARGETS, self.loc(args[0]))
                t2 = self.validate_arg(self.format_intrinsic_arg(args[1], is_ident=True), REG_RADAR_TARGETS, self.loc(args[1]))
                t3 = self.validate_arg(self.format_intrinsic_arg(args[2], is_ident=True), REG_RADAR_TARGETS, self.loc(args[2]))
                sort = self.validate_arg(self.format_intrinsic_arg(args[3], is_ident=True), REG_RADAR_SORTS, self.loc(args[3]))
                sort_order = str(self.format_intrinsic_arg(args[4], is_ident=False))
                self.instructions.append(
                    IRRaw(
                        opcode="uradar",
                        args=[t1, t2, t3, sort, "0", sort_order, dest],
                        loc=loc,
                    )
                )
                return dest
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
            elif len(args) == 2 and (target_dest is not None or not is_statement):
                dest = target_dest if target_dest is not None else self.new_temp(loc)
                type_arg = self.format_intrinsic_arg(args[0], is_ident=True)
                type_str = self.validate_arg(type_arg, REG_LOOKUP_TYPES, self.loc(args[0]))
                idx = str(self.format_intrinsic_arg(args[1], is_ident=False))
                self.instructions.append(
                    IRRaw(opcode="lookup", args=[type_str, dest, idx], loc=loc)
                )
                return dest
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
            elif len(args) == 4 and (target_dest is not None or not is_statement):
                dest = target_dest if target_dest is not None else self.new_temp(loc)
                r = str(self.format_intrinsic_arg(args[0], is_ident=False))
                g = str(self.format_intrinsic_arg(args[1], is_ident=False))
                b = str(self.format_intrinsic_arg(args[2], is_ident=False))
                a = str(self.format_intrinsic_arg(args[3], is_ident=False))
                self.instructions.append(
                    IRRaw(opcode="packcolor", args=[dest, r, g, b, a], loc=loc)
                )
                return dest
            else:
                self.error(
                    "invalid arguments for packcolor: expected packcolor(dest, r, g, b, a) or dest = packcolor(r, g, b, a)",
                    call,
                )

        elif func_name == "unpackcolor":
            if len(args) != 5:
                self.error(
                    "invalid arguments for unpackcolor: expected unpackcolor(r, g, b, a, value) or r, g, b, a = unpackcolor(value)",
                    call,
                )
            r = str(self.format_intrinsic_arg(args[0], is_ident=True))
            g = str(self.format_intrinsic_arg(args[1], is_ident=True))
            b = str(self.format_intrinsic_arg(args[2], is_ident=True))
            a = str(self.format_intrinsic_arg(args[3], is_ident=True))
            val = str(self.format_intrinsic_arg(args[4], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="unpackcolor", args=[r, g, b, a, val], loc=loc)
            )
            return "0"

        elif func_name == "getlink":
            if len(args) == 2:
                dest = str(self.format_intrinsic_arg(args[0], is_ident=True))
                idx = str(self.format_intrinsic_arg(args[1], is_ident=False))
                self.instructions.append(
                    IRRaw(opcode="getlink", args=[dest, idx], loc=loc)
                )
                return dest
            elif len(args) == 1 and (target_dest is not None or not is_statement):
                dest = target_dest if target_dest is not None else self.new_temp(loc)
                idx = str(self.format_intrinsic_arg(args[0], is_ident=False))
                self.instructions.append(
                    IRRaw(opcode="getlink", args=[dest, idx], loc=loc)
                )
                return dest
            else:
                self.error(
                    "invalid arguments for getlink: expected getlink(dest, index) or dest = getlink(index)",
                    call,
                )

        elif func_name == "select":
            if len(args) == 6:
                dest = str(self.format_intrinsic_arg(args[0], is_ident=True))
                cond_arg = self.format_intrinsic_arg(args[1], is_ident=True)
                cond = self.validate_arg(cond_arg, REG_CONDITIONS, self.loc(args[1]))
                comp0 = str(self.format_intrinsic_arg(args[2], is_ident=False))
                comp1 = str(self.format_intrinsic_arg(args[3], is_ident=False))
                a = str(self.format_intrinsic_arg(args[4], is_ident=False))
                b = str(self.format_intrinsic_arg(args[5], is_ident=False))
                self.instructions.append(
                    IRRaw(opcode="select", args=[dest, cond, comp0, comp1, a, b], loc=loc)
                )
                return dest
            elif len(args) == 5 and (target_dest is not None or not is_statement):
                dest = target_dest if target_dest is not None else self.new_temp(loc)
                cond_arg = self.format_intrinsic_arg(args[0], is_ident=True)
                cond = self.validate_arg(cond_arg, REG_CONDITIONS, self.loc(args[0]))
                comp0 = str(self.format_intrinsic_arg(args[1], is_ident=False))
                comp1 = str(self.format_intrinsic_arg(args[2], is_ident=False))
                a = str(self.format_intrinsic_arg(args[3], is_ident=False))
                b = str(self.format_intrinsic_arg(args[4], is_ident=False))
                self.instructions.append(
                    IRRaw(opcode="select", args=[dest, cond, comp0, comp1, a, b], loc=loc)
                )
                return dest
            elif len(args) == 4:
                dest = str(self.format_intrinsic_arg(args[0], is_ident=True))
                cond = str(self.format_intrinsic_arg(args[1], is_ident=False))
                a = str(self.format_intrinsic_arg(args[2], is_ident=False))
                b = str(self.format_intrinsic_arg(args[3], is_ident=False))
                self.instructions.append(
                    IRRaw(opcode="select", args=[dest, "notEqual", cond, "0", a, b], loc=loc)
                )
                return dest
            elif len(args) == 3 and (target_dest is not None or not is_statement):
                dest = target_dest if target_dest is not None else self.new_temp(loc)
                cond = str(self.format_intrinsic_arg(args[0], is_ident=False))
                a = str(self.format_intrinsic_arg(args[1], is_ident=False))
                b = str(self.format_intrinsic_arg(args[2], is_ident=False))
                self.instructions.append(
                    IRRaw(opcode="select", args=[dest, "notEqual", cond, "0", a, b], loc=loc)
                )
                return dest
            else:
                self.error(
                    "invalid arguments for select: expected select([dest], [cond_op, comp0, comp1], a, b)",
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

        elif func_name == "setrate":
            if len(args) != 1:
                self.error("invalid arguments for setrate: expected setrate(ipt)", call)
            ipt = str(self.format_intrinsic_arg(args[0], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="setrate", args=[ipt], loc=loc)
            )
            return "0"

        elif func_name == "noop":
            if len(args) != 0:
                self.error("invalid arguments for noop: expected noop()", call)
            self.instructions.append(IRRaw(opcode="noop", args=[], loc=loc))
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

        elif func_name == "query":
            if len(args) != 7:
                self.error(
                    "invalid arguments for query: expected query(shape, type, team, x, y, w, h)",
                    call,
                )
            shape_arg = self.format_intrinsic_arg(args[0], is_ident=True)
            shape = self.validate_arg(shape_arg, REG_QUERY_SHAPES, self.loc(args[0]))
            type_arg = self.format_intrinsic_arg(args[1], is_ident=True)
            type_str = self.validate_arg(type_arg, REG_QUERY_TYPES, self.loc(args[1]))
            team = str(self.format_intrinsic_arg(args[2], is_ident=True))
            x = str(self.format_intrinsic_arg(args[3], is_ident=False))
            y = str(self.format_intrinsic_arg(args[4], is_ident=False))
            w = str(self.format_intrinsic_arg(args[5], is_ident=False))
            h = str(self.format_intrinsic_arg(args[6], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="query", args=[shape, type_str, team, x, y, w, h], loc=loc)
            )
            return "0"

        elif func_name == "getblock":
            if len(args) == 4:
                layer_arg = self.format_intrinsic_arg(args[0], is_ident=True)
                layer = self.validate_arg(layer_arg, REG_TILE_LAYERS, self.loc(args[0]))
                dest = str(self.format_intrinsic_arg(args[1], is_ident=True))
                x = str(self.format_intrinsic_arg(args[2], is_ident=False))
                y = str(self.format_intrinsic_arg(args[3], is_ident=False))
                self.instructions.append(
                    IRRaw(opcode="getblock", args=[layer, dest, x, y], loc=loc)
                )
                return dest
            elif len(args) == 3 and (target_dest is not None or not is_statement):
                dest = target_dest if target_dest is not None else self.new_temp(loc)
                layer_arg = self.format_intrinsic_arg(args[0], is_ident=True)
                layer = self.validate_arg(layer_arg, REG_TILE_LAYERS, self.loc(args[0]))
                x = str(self.format_intrinsic_arg(args[1], is_ident=False))
                y = str(self.format_intrinsic_arg(args[2], is_ident=False))
                self.instructions.append(
                    IRRaw(opcode="getblock", args=[layer, dest, x, y], loc=loc)
                )
                return dest
            else:
                self.error(
                    "invalid arguments for getblock: expected getblock(layer, result, x, y) or result = getblock(layer, x, y)",
                    call,
                )

        elif func_name == "setblock":
            if len(args) < 4 or len(args) > 6:
                self.error(
                    "invalid arguments for setblock: expected setblock(layer, block, x, y, [team, rotation])",
                    call,
                )
            layer_arg = self.format_intrinsic_arg(args[0], is_ident=True)
            layer = self.validate_arg(layer_arg, REG_TILE_LAYERS, self.loc(args[0]))
            block = str(self.format_intrinsic_arg(args[1], is_ident=True))
            x = str(self.format_intrinsic_arg(args[2], is_ident=False))
            y = str(self.format_intrinsic_arg(args[3], is_ident=False))
            team = str(self.format_intrinsic_arg(args[4], is_ident=True)) if len(args) >= 5 else "@derelict"
            rotation = str(self.format_intrinsic_arg(args[5], is_ident=False)) if len(args) == 6 else "0"
            self.instructions.append(
                IRRaw(opcode="setblock", args=[layer, block, x, y, team, rotation], loc=loc)
            )
            return "0"

        elif func_name == "spawn":
            # Statement form: spawn(type, x, y, rotation, team, result, [effect=0]) (6 or 7 args)
            # Assignment form: result = spawn(type, x, y, rotation, team, [effect=0]) (5 or 6 args)
            if is_statement and target_dest is None and len(args) in (6, 7):
                type_arg = self.format_intrinsic_arg(args[0], is_ident=True)
                type_ = self.validate_arg(type_arg, REG_UNIT_TYPES, self.loc(args[0]))
                x = str(self.format_intrinsic_arg(args[1], is_ident=False))
                y = str(self.format_intrinsic_arg(args[2], is_ident=False))
                rotation = str(self.format_intrinsic_arg(args[3], is_ident=False))
                team_arg = self.format_intrinsic_arg(args[4], is_ident=True)
                team = self.validate_arg(team_arg, REG_TEAMS, self.loc(args[4]))
                dest = str(self.format_intrinsic_arg(args[5], is_ident=True))
                effect = str(self.format_intrinsic_arg(args[6], is_ident=False)) if len(args) == 7 else "0"
                if effect in ("True", "true"):
                    effect = "1"
                elif effect in ("False", "false"):
                    effect = "0"
                self.instructions.append(
                    IRRaw(opcode="spawn", args=[type_, x, y, rotation, team, dest, effect], loc=loc)
                )
                return dest
            elif (target_dest is not None or not is_statement) and len(args) in (5, 6):
                dest = target_dest if target_dest is not None else self.new_temp(loc)
                type_arg = self.format_intrinsic_arg(args[0], is_ident=True)
                type_ = self.validate_arg(type_arg, REG_UNIT_TYPES, self.loc(args[0]))
                x = str(self.format_intrinsic_arg(args[1], is_ident=False))
                y = str(self.format_intrinsic_arg(args[2], is_ident=False))
                rotation = str(self.format_intrinsic_arg(args[3], is_ident=False))
                team_arg = self.format_intrinsic_arg(args[4], is_ident=True)
                team = self.validate_arg(team_arg, REG_TEAMS, self.loc(args[4]))
                effect = str(self.format_intrinsic_arg(args[5], is_ident=False)) if len(args) == 6 else "0"
                if effect in ("True", "true"):
                    effect = "1"
                elif effect in ("False", "false"):
                    effect = "0"
                self.instructions.append(
                    IRRaw(opcode="spawn", args=[type_, x, y, rotation, team, dest, effect], loc=loc)
                )
                return dest
            else:
                self.error(
                    "invalid arguments for spawn: expected spawn(type, x, y, rotation, team, [result], [effect])",
                    call,
                )

        elif func_name == "bullet":
            # Statement form: bullet(result, from_, index, x, y, rotation, team, [owner, damage, velocityScl, lifeScl, aimX, aimY]) (7 to 13 args)
            # Assignment form: result = bullet(from_, index, x, y, rotation, team, [owner, damage, velocityScl, lifeScl, aimX, aimY]) (6 to 12 args)
            if 7 <= len(args) <= 13 and is_statement and (target_dest is None):
                dest = str(self.format_intrinsic_arg(args[0], is_ident=True))
                from_ = str(self.format_intrinsic_arg(args[1], is_ident=True))
                index = str(self.format_intrinsic_arg(args[2], is_ident=True))
                x = str(self.format_intrinsic_arg(args[3], is_ident=False))
                y = str(self.format_intrinsic_arg(args[4], is_ident=False))
                rotation = str(self.format_intrinsic_arg(args[5], is_ident=False))
                team_arg = self.format_intrinsic_arg(args[6], is_ident=True)
                team = self.validate_arg(team_arg, REG_TEAMS, self.loc(args[6])) if (team_arg.startswith("@") or team_arg.upper() in REG_TEAMS.by_source_name) else str(team_arg)
                owner = str(self.format_intrinsic_arg(args[7], is_ident=True)) if len(args) >= 8 else "null"
                damage = str(self.format_intrinsic_arg(args[8], is_ident=False)) if len(args) >= 9 else "-1"
                vel = str(self.format_intrinsic_arg(args[9], is_ident=False)) if len(args) >= 10 else "1"
                life = str(self.format_intrinsic_arg(args[10], is_ident=False)) if len(args) >= 11 else "1"
                aim_x = str(self.format_intrinsic_arg(args[11], is_ident=False)) if len(args) >= 12 else "-1"
                aim_y = str(self.format_intrinsic_arg(args[12], is_ident=False)) if len(args) >= 13 else "-1"
                self.instructions.append(
                    IRRaw(
                        opcode="bullet",
                        args=[dest, from_, index, x, y, rotation, team, owner, damage, vel, life, aim_x, aim_y],
                        loc=loc,
                    )
                )
                return dest
            elif 6 <= len(args) <= 12 and (target_dest is not None or not is_statement):
                dest = target_dest if target_dest is not None else self.new_temp(loc)
                from_ = str(self.format_intrinsic_arg(args[0], is_ident=True))
                index = str(self.format_intrinsic_arg(args[1], is_ident=True))
                x = str(self.format_intrinsic_arg(args[2], is_ident=False))
                y = str(self.format_intrinsic_arg(args[3], is_ident=False))
                rotation = str(self.format_intrinsic_arg(args[4], is_ident=False))
                team_arg = self.format_intrinsic_arg(args[5], is_ident=True)
                team = self.validate_arg(team_arg, REG_TEAMS, self.loc(args[5])) if (team_arg.startswith("@") or team_arg.upper() in REG_TEAMS.by_source_name) else str(team_arg)
                owner = str(self.format_intrinsic_arg(args[6], is_ident=True)) if len(args) >= 7 else "null"
                damage = str(self.format_intrinsic_arg(args[7], is_ident=False)) if len(args) >= 8 else "-1"
                vel = str(self.format_intrinsic_arg(args[8], is_ident=False)) if len(args) >= 9 else "1"
                life = str(self.format_intrinsic_arg(args[9], is_ident=False)) if len(args) >= 10 else "1"
                aim_x = str(self.format_intrinsic_arg(args[10], is_ident=False)) if len(args) >= 11 else "-1"
                aim_y = str(self.format_intrinsic_arg(args[11], is_ident=False)) if len(args) >= 12 else "-1"
                self.instructions.append(
                    IRRaw(
                        opcode="bullet",
                        args=[dest, from_, index, x, y, rotation, team, owner, damage, vel, life, aim_x, aim_y],
                        loc=loc,
                    )
                )
                return dest
            else:
                self.error(
                    "invalid arguments for bullet: expected bullet(from, index, x, y, rotation, team, ...) or result = bullet(...)",
                    call,
                )

        elif func_name == "status":
            # status(clear, effect, unit, [duration=0]) (3 or 4 args)
            if len(args) not in (3, 4):
                self.error(
                    "invalid arguments for status: expected status(clear, effect, unit, [duration])",
                    call,
                )
            clear_arg = str(self.format_intrinsic_arg(args[0], is_ident=False))
            if clear_arg in ("True", "true"):
                clear_val = "1"
            elif clear_arg in ("False", "false"):
                clear_val = "0"
            else:
                clear_val = clear_arg
            effect_arg = self.format_intrinsic_arg(args[1], is_ident=True)
            effect = self.validate_arg(effect_arg, REG_STATUS_EFFECTS, self.loc(args[1])) if (effect_arg.startswith("@") or effect_arg.upper().replace("-", "_") in REG_STATUS_EFFECTS.by_source_name) else str(effect_arg)
            unit = str(self.format_intrinsic_arg(args[2], is_ident=True))
            duration = str(self.format_intrinsic_arg(args[3], is_ident=False)) if len(args) == 4 else "0"
            self.instructions.append(
                IRRaw(opcode="status", args=[clear_val, effect, unit, duration], loc=loc)
            )
            return "0"

        elif func_name == "explosion":
            # explosion(team, x, y, radius, damage, [air=1, ground=1, pierce=0, effect=1]) (5 to 9 args)
            if not (5 <= len(args) <= 9):
                self.error(
                    "invalid arguments for explosion: expected explosion(team, x, y, radius, damage, [air, ground, pierce, effect])",
                    call,
                )
            team_arg = self.format_intrinsic_arg(args[0], is_ident=True)
            team = self.validate_arg(team_arg, REG_TEAMS, self.loc(args[0])) if (team_arg.startswith("@") or team_arg.upper() in REG_TEAMS.by_source_name) else str(team_arg)
            x = str(self.format_intrinsic_arg(args[1], is_ident=False))
            y = str(self.format_intrinsic_arg(args[2], is_ident=False))
            radius = str(self.format_intrinsic_arg(args[3], is_ident=False))
            damage = str(self.format_intrinsic_arg(args[4], is_ident=False))
            air = str(self.format_intrinsic_arg(args[5], is_ident=False)) if len(args) >= 6 else "1"
            ground = str(self.format_intrinsic_arg(args[6], is_ident=False)) if len(args) >= 7 else "1"
            pierce = str(self.format_intrinsic_arg(args[7], is_ident=False)) if len(args) >= 8 else "0"
            effect = str(self.format_intrinsic_arg(args[8], is_ident=False)) if len(args) >= 9 else "1"
            air_val = "1" if air in ("True", "true", "1") else ("0" if air in ("False", "false", "0") else air)
            ground_val = "1" if ground in ("True", "true", "1") else ("0" if ground in ("False", "false", "0") else ground)
            pierce_val = "1" if pierce in ("True", "true", "1") else ("0" if pierce in ("False", "false", "0") else pierce)
            effect_val = "1" if effect in ("True", "true", "1") else ("0" if effect in ("False", "false", "0") else effect)
            self.instructions.append(
                IRRaw(
                    opcode="explosion",
                    args=[team, x, y, radius, damage, air_val, ground_val, pierce_val, effect_val],
                    loc=loc,
                )
            )
            return "0"

        elif func_name == "getflag":
            # Statement form: getflag(result, flag) (2 args)
            # Expression form: result = getflag(flag) (1 arg)
            if len(args) == 2 and is_statement and (target_dest is None):
                dest = str(self.format_intrinsic_arg(args[0], is_ident=True))
                flag = str(self.format_intrinsic_arg(args[1], is_ident=False))
                self.instructions.append(
                    IRRaw(opcode="getflag", args=[dest, flag], loc=loc)
                )
                return dest
            elif len(args) == 1 and (target_dest is not None or not is_statement):
                dest = target_dest if target_dest is not None else self.new_temp(loc)
                flag = str(self.format_intrinsic_arg(args[0], is_ident=False))
                self.instructions.append(
                    IRRaw(opcode="getflag", args=[dest, flag], loc=loc)
                )
                return dest
            else:
                self.error(
                    "invalid arguments for getflag: expected getflag(result, flag) or result = getflag(flag)",
                    call,
                )

        elif func_name == "setflag":
            if len(args) != 2:
                self.error("invalid arguments for setflag: expected setflag(flag, value)", call)
            flag = str(self.format_intrinsic_arg(args[0], is_ident=False))
            val_raw = str(self.format_intrinsic_arg(args[1], is_ident=False))
            val = "1" if val_raw in ("True", "true", "1") else ("0" if val_raw in ("False", "false", "0") else val_raw)
            self.instructions.append(
                IRRaw(opcode="setflag", args=[flag, val], loc=loc)
            )
            return "0"

        elif func_name == "setprop":
            if len(args) != 3:
                self.error("invalid arguments for setprop: expected setprop(type, of, value)", call)
            type_arg = self.format_intrinsic_arg(args[0], is_ident=True)
            if type_arg.startswith("@") or type_arg.upper() in REG_SENSOR_PROPERTIES.by_source_name:
                type_ = self.validate_arg(type_arg, REG_SENSOR_PROPERTIES, self.loc(args[0]))
            else:
                type_ = str(type_arg)
            of = str(self.format_intrinsic_arg(args[1], is_ident=True))
            val = str(self.format_intrinsic_arg(args[2], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="setprop", args=[type_, of, val], loc=loc)
            )
            return "0"

        elif func_name == "fetch":
            # Statement form: fetch(type, result, team, [index=0], [extra=0]) (3 to 5 args)
            # Expression form: result = fetch(type, team, [index=0], [extra=0]) (2 to 4 args)
            if 3 <= len(args) <= 5 and is_statement and (target_dest is None):
                type_arg = self.format_intrinsic_arg(args[0], is_ident=True)
                type_ = self.validate_arg(type_arg, REG_FETCH_TYPES, self.loc(args[0]))
                dest = str(self.format_intrinsic_arg(args[1], is_ident=True))
                team_arg = self.format_intrinsic_arg(args[2], is_ident=True)
                team = self.validate_arg(team_arg, REG_TEAMS, self.loc(args[2])) if (team_arg.startswith("@") or team_arg.upper() in REG_TEAMS.by_source_name) else str(team_arg)
                index = str(self.format_intrinsic_arg(args[3], is_ident=False)) if len(args) >= 4 else "0"
                extra = str(self.format_intrinsic_arg(args[4], is_ident=True)) if len(args) >= 5 else "0"
                self.instructions.append(
                    IRRaw(opcode="fetch", args=[type_, dest, team, index, extra], loc=loc)
                )
                return dest
            elif 2 <= len(args) <= 4 and (target_dest is not None or not is_statement):
                dest = target_dest if target_dest is not None else self.new_temp(loc)
                type_arg = self.format_intrinsic_arg(args[0], is_ident=True)
                type_ = self.validate_arg(type_arg, REG_FETCH_TYPES, self.loc(args[0]))
                team_arg = self.format_intrinsic_arg(args[1], is_ident=True)
                team = self.validate_arg(team_arg, REG_TEAMS, self.loc(args[1])) if (team_arg.startswith("@") or team_arg.upper() in REG_TEAMS.by_source_name) else str(team_arg)
                index = str(self.format_intrinsic_arg(args[2], is_ident=False)) if len(args) >= 3 else "0"
                extra = str(self.format_intrinsic_arg(args[3], is_ident=True)) if len(args) >= 4 else "0"
                self.instructions.append(
                    IRRaw(opcode="fetch", args=[type_, dest, team, index, extra], loc=loc)
                )
                return dest
            else:
                self.error(
                    "invalid arguments for fetch: expected fetch(type, result, team, [index], [extra]) or result = fetch(type, team, [index], [extra])",
                    call,
                )

        elif func_name == "sync":
            if len(args) != 1:
                self.error("invalid arguments for sync: expected sync(variable)", call)
            var_name = str(self.format_intrinsic_arg(args[0], is_ident=True))
            self.instructions.append(
                IRRaw(opcode="sync", args=[var_name], loc=loc)
            )
            return "0"

        elif func_name == "setrule":
            if not (2 <= len(args) <= 6):
                self.error(
                    "invalid arguments for setrule: expected setrule(rule, value, [p1, p2, p3, p4])",
                    call,
                )
            rule_arg = self.format_intrinsic_arg(args[0], is_ident=True)
            rule = self.validate_arg(rule_arg, REG_LOGIC_RULES, self.loc(args[0]))
            val = str(self.format_intrinsic_arg(args[1], is_ident=False))
            p1 = str(self.format_intrinsic_arg(args[2], is_ident=True)) if len(args) >= 3 else "0"
            p2 = str(self.format_intrinsic_arg(args[3], is_ident=False)) if len(args) >= 4 else "0"
            p3 = str(self.format_intrinsic_arg(args[4], is_ident=False)) if len(args) >= 5 else "0"
            p4 = str(self.format_intrinsic_arg(args[5], is_ident=False)) if len(args) >= 6 else "0"
            self.instructions.append(
                IRRaw(opcode="setrule", args=[rule, val, p1, p2, p3, p4], loc=loc)
            )
            return "0"

        elif func_name == "weathersense":
            # Statement form: weathersense(to, weather) (2 args)
            # Expression form: to = weathersense(weather) (1 arg)
            if target_dest is not None and len(args) == 1:
                dest = target_dest
                w_arg = self.format_intrinsic_arg(args[0], is_ident=True)
                weather = self.validate_arg(w_arg, REG_WEATHERS, self.loc(args[0])) if (w_arg.startswith("@") or w_arg.upper().replace("-", "_") in REG_WEATHERS.by_source_name) else str(w_arg)
                self.instructions.append(
                    IRRaw(opcode="weathersense", args=[dest, weather], loc=loc)
                )
                return dest
            elif len(args) == 2:
                dest = str(self.format_intrinsic_arg(args[0], is_ident=True))
                w_arg = self.format_intrinsic_arg(args[1], is_ident=True)
                weather = self.validate_arg(w_arg, REG_WEATHERS, self.loc(args[1])) if (w_arg.startswith("@") or w_arg.upper().replace("-", "_") in REG_WEATHERS.by_source_name) else str(w_arg)
                self.instructions.append(
                    IRRaw(opcode="weathersense", args=[dest, weather], loc=loc)
                )
                return dest
            elif target_dest is None and len(args) == 1:
                dest = self.new_temp()
                w_arg = self.format_intrinsic_arg(args[0], is_ident=True)
                weather = self.validate_arg(w_arg, REG_WEATHERS, self.loc(args[0])) if (w_arg.startswith("@") or w_arg.upper().replace("-", "_") in REG_WEATHERS.by_source_name) else str(w_arg)
                self.instructions.append(
                    IRRaw(opcode="weathersense", args=[dest, weather], loc=loc)
                )
                return dest
            else:
                self.error(
                    "invalid arguments for weathersense: expected weathersense(weather) or weathersense(to, weather)",
                    call,
                )

        elif func_name == "weatherset":
            # weatherset(weather, [state=1]) (1 or 2 args)
            if not (1 <= len(args) <= 2):
                self.error(
                    "invalid arguments for weatherset: expected weatherset(weather, [state=1])",
                    call,
                )
            w_arg = self.format_intrinsic_arg(args[0], is_ident=True)
            weather = self.validate_arg(w_arg, REG_WEATHERS, self.loc(args[0])) if (w_arg.startswith("@") or w_arg.upper().replace("-", "_") in REG_WEATHERS.by_source_name) else str(w_arg)
            state = str(self.format_intrinsic_arg(args[1], is_ident=False)) if len(args) == 2 else "1"
            if state in ("True", "true"):
                state = "1"
            elif state in ("False", "false"):
                state = "0"
            self.instructions.append(
                IRRaw(opcode="weatherset", args=[weather, state], loc=loc)
            )
            return "0"

        elif func_name == "spawnwave":
            # spawnwave(x, y, [natural=0]) (2 or 3 args)
            if not (2 <= len(args) <= 3):
                self.error(
                    "invalid arguments for spawnwave: expected spawnwave(x, y, [natural=0])",
                    call,
                )
            x = str(self.format_intrinsic_arg(args[0], is_ident=False))
            y = str(self.format_intrinsic_arg(args[1], is_ident=False))
            natural = str(self.format_intrinsic_arg(args[2], is_ident=False)) if len(args) == 3 else "0"
            if natural in ("True", "true"):
                natural = "1"
            elif natural in ("False", "false"):
                natural = "0"
            self.instructions.append(
                IRRaw(opcode="spawnwave", args=[x, y, natural], loc=loc)
            )
            return "0"

        elif func_name == "effect":
            # effect(type, x, y, [sizerot=0, color=0, data=0]) (3 to 6 args)
            if not (3 <= len(args) <= 6):
                self.error(
                    "invalid arguments for effect: expected effect(type, x, y, [sizerot=0, color=0, data=0])",
                    call,
                )
            fx_arg = self.format_intrinsic_arg(args[0], is_ident=True)
            fx_snake = to_snake(fx_arg).upper() if isinstance(fx_arg, str) else str(fx_arg)
            type_ = self.validate_arg(fx_arg, REG_LOGIC_FX, self.loc(args[0])) if fx_snake in REG_LOGIC_FX.by_source_name else str(fx_arg)
            x = str(self.format_intrinsic_arg(args[1], is_ident=False))
            y = str(self.format_intrinsic_arg(args[2], is_ident=False))
            sizerot = str(self.format_intrinsic_arg(args[3], is_ident=False)) if len(args) >= 4 else "0"
            color = str(self.format_intrinsic_arg(args[4], is_ident=False)) if len(args) >= 5 else "0"
            data = str(self.format_intrinsic_arg(args[5], is_ident=False)) if len(args) >= 6 else "0"
            self.instructions.append(
                IRRaw(opcode="effect", args=[type_, x, y, sizerot, color, data], loc=loc)
            )
            return "0"

        elif func_name == "message":
            # Statement form: message(type, [duration=3], [out_success="@wait"])
            # Expression form: result = message(type, [duration=3])
            kwargs = {kw.arg: kw.value for kw in call.keywords} if call.keywords else {}
            for k in kwargs:
                if k not in ("type", "duration", "out_success", "outSuccess"):
                    self.error(f"unexpected keyword argument '{k}' for message", call)

            # extract type
            if len(args) >= 1:
                type_node = args[0]
            elif "type" in kwargs:
                type_node = kwargs["type"]
            else:
                self.error("missing required argument 'type' for message", call)

            type_arg = self.format_intrinsic_arg(type_node, is_ident=True)
            type_upper = type_arg.upper() if isinstance(type_arg, str) else str(type_arg)
            type_ = self.validate_arg(type_arg, REG_MESSAGE_TYPES, self.loc(type_node)) if type_upper in REG_MESSAGE_TYPES.by_source_name else str(type_arg)

            # extract duration
            if len(args) >= 2:
                duration = str(self.format_intrinsic_arg(args[1], is_ident=False))
            elif "duration" in kwargs:
                duration = str(self.format_intrinsic_arg(kwargs["duration"], is_ident=False))
            else:
                duration = "3"

            # extract out_success
            if len(args) >= 3:
                out_success = str(self.format_intrinsic_arg(args[2], is_ident=True))
                dest = out_success
            elif "out_success" in kwargs:
                out_success = str(self.format_intrinsic_arg(kwargs["out_success"], is_ident=True))
                dest = out_success
            elif "outSuccess" in kwargs:
                out_success = str(self.format_intrinsic_arg(kwargs["outSuccess"], is_ident=True))
                dest = out_success
            elif target_dest is not None or not is_statement:
                dest = target_dest if target_dest is not None else self.new_temp(loc)
                out_success = dest
            else:
                dest = "0"
                out_success = "@wait"

            if len(args) > 3:
                self.error("too many arguments for message: expected message(type, [duration=3], [out_success='@wait'])", call)

            self.instructions.append(
                IRRaw(opcode="message", args=[type_, duration, out_success], loc=loc)
            )
            return dest if (target_dest is not None or not is_statement) else "0"

        elif func_name == "cutscene":
            # cutscene(action, [p1=0, p2=0, p3=0, p4=0]) (1 to 5 args)
            if not (1 <= len(args) <= 5):
                self.error("invalid arguments for cutscene: expected cutscene(action, [p1, p2, p3, p4])", call)
            action_arg = self.format_intrinsic_arg(args[0], is_ident=True)
            action_snake = to_snake(action_arg).upper() if isinstance(action_arg, str) else str(action_arg)
            action = self.validate_arg(action_arg, REG_CUTSCENE_ACTIONS, self.loc(args[0])) if action_snake in REG_CUTSCENE_ACTIONS.by_source_name else str(action_arg)

            if action in ("active", "getHud"):
                if target_dest is not None or not is_statement:
                    dest = target_dest if target_dest is not None else self.new_temp(loc)
                    p1 = dest
                elif len(args) >= 2:
                    p1 = str(self.format_intrinsic_arg(args[1], is_ident=True))
                    dest = p1
                else:
                    self.error(f"cutscene('{action}') requires a destination variable or assignment (e.g. res = cutscene('{action}'))", call)
                p2 = "0"
                p3 = "0"
                p4 = "0"
                self.instructions.append(
                    IRRaw(opcode="cutscene", args=[action, p1, p2, p3, p4], loc=loc)
                )
                return dest

            p1 = str(self.format_intrinsic_arg(args[1], is_ident=False)) if len(args) >= 2 else "0"
            if action == "setHud":
                if p1 in ("True", "true"):
                    p1 = "1"
                elif p1 in ("False", "false"):
                    p1 = "0"
            p2 = str(self.format_intrinsic_arg(args[2], is_ident=False)) if len(args) >= 3 else "0"
            p3 = str(self.format_intrinsic_arg(args[3], is_ident=False)) if len(args) >= 4 else "0"
            p4 = str(self.format_intrinsic_arg(args[4], is_ident=False)) if len(args) >= 5 else "0"

            self.instructions.append(
                IRRaw(opcode="cutscene", args=[action, p1, p2, p3, p4], loc=loc)
            )
            return "0"

        elif func_name == "playsound":
            # playsound(positional, id, [volume=1, pitch=1, pan=0, x=0, y=0, limit=True])
            if not (2 <= len(args) <= 8):
                self.error("invalid arguments for playsound: expected playsound(positional, id, [volume, pitch, pan, x, y, limit])", call)
            pos_arg = str(self.format_intrinsic_arg(args[0], is_ident=False))
            pos = "true" if pos_arg in ("True", "true", "1") else "false"
            id_ = str(self.format_intrinsic_arg(args[1], is_ident=True))
            volume = str(self.format_intrinsic_arg(args[2], is_ident=False)) if len(args) >= 3 else "1"
            pitch = str(self.format_intrinsic_arg(args[3], is_ident=False)) if len(args) >= 4 else "1"
            pan = str(self.format_intrinsic_arg(args[4], is_ident=False)) if len(args) >= 5 else "0"
            x = str(self.format_intrinsic_arg(args[5], is_ident=False)) if len(args) >= 6 else ("@thisx" if pos == "true" else "0")
            y = str(self.format_intrinsic_arg(args[6], is_ident=False)) if len(args) >= 7 else ("@thisy" if pos == "true" else "0")
            limit_arg = str(self.format_intrinsic_arg(args[7], is_ident=False)) if len(args) >= 8 else "true"
            limit = "true" if limit_arg in ("True", "true", "1") else ("false" if limit_arg in ("False", "false", "0") else limit_arg)
            self.instructions.append(
                IRRaw(opcode="playsound", args=[pos, id_, volume, pitch, pan, x, y, limit], loc=loc)
            )
            return "0"

        elif func_name == "playmusic":
            # playmusic(name, [interrupt=True])
            if not (1 <= len(args) <= 2):
                self.error("invalid arguments for playmusic: expected playmusic(name, [interrupt=True])", call)
            name = str(self.format_intrinsic_arg(args[0], is_ident=False))
            intr_arg = str(self.format_intrinsic_arg(args[1], is_ident=False)) if len(args) >= 2 else "true"
            intr = "true" if intr_arg in ("True", "true", "1") else ("false" if intr_arg in ("False", "false", "0") else intr_arg)
            self.instructions.append(
                IRRaw(opcode="playmusic", args=[name, intr], loc=loc)
            )
            return "0"

        elif func_name == "makemarker":
            # makemarker(type, id, x, y, [replace=True])
            if not (4 <= len(args) <= 5):
                self.error("invalid arguments for makemarker: expected makemarker(type, id, x, y, [replace=True])", call)
            type_arg = self.format_intrinsic_arg(args[0], is_ident=True)
            type_snake = to_snake(type_arg).upper() if isinstance(type_arg, str) else str(type_arg)
            type_ = self.validate_arg(type_arg, REG_MARKER_TYPES, self.loc(args[0])) if type_snake in REG_MARKER_TYPES.by_source_name else str(type_arg)
            id_ = str(self.format_intrinsic_arg(args[1], is_ident=True))
            x = str(self.format_intrinsic_arg(args[2], is_ident=False))
            y = str(self.format_intrinsic_arg(args[3], is_ident=False))
            replace_arg = str(self.format_intrinsic_arg(args[4], is_ident=False)) if len(args) >= 5 else "true"
            replace = "true" if replace_arg in ("True", "true", "1") else ("false" if replace_arg in ("False", "false", "0") else replace_arg)
            self.instructions.append(
                IRRaw(opcode="makemarker", args=[type_, id_, x, y, replace], loc=loc)
            )
            return "0"

        elif func_name == "setmarker":
            # setmarker(type, id, [p1=0, p2=0, p3=0])
            if not (2 <= len(args) <= 5):
                self.error("invalid arguments for setmarker: expected setmarker(type, id, [p1, p2, p3])", call)
            type_arg = self.format_intrinsic_arg(args[0], is_ident=True)
            type_snake = to_snake(type_arg).upper() if isinstance(type_arg, str) else str(type_arg)
            type_ = self.validate_arg(type_arg, REG_MARKER_CONTROLS, self.loc(args[0])) if type_snake in REG_MARKER_CONTROLS.by_source_name else str(type_arg)
            id_ = str(self.format_intrinsic_arg(args[1], is_ident=True))
            p1 = str(self.format_intrinsic_arg(args[2], is_ident=False)) if len(args) >= 3 else "0"
            if p1 in ("True", "true"):
                p1 = "1"
            elif p1 in ("False", "false"):
                p1 = "0"
            p2 = str(self.format_intrinsic_arg(args[3], is_ident=False)) if len(args) >= 4 else "0"
            if p2 in ("True", "true"):
                p2 = "1"
            elif p2 in ("False", "false"):
                p2 = "0"
            p3 = str(self.format_intrinsic_arg(args[4], is_ident=False)) if len(args) >= 5 else "0"
            if p3 in ("True", "true"):
                p3 = "1"
            elif p3 in ("False", "false"):
                p3 = "0"
            self.instructions.append(
                IRRaw(opcode="setmarker", args=[type_, id_, p1, p2, p3], loc=loc)
            )
            return "0"

        elif func_name == "localeprint":
            if len(args) != 1:
                self.error("invalid arguments for localeprint: expected localeprint(value)", call)
            val = str(self.format_intrinsic_arg(args[0], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="localeprint", args=[val], loc=loc)
            )
            return "0"

        elif func_name == "clientdata":
            # clientdata(channel, value, [reliable=False])
            if not (2 <= len(args) <= 3):
                self.error("invalid arguments for clientdata: expected clientdata(channel, value, [reliable=False])", call)
            chan = str(self.format_intrinsic_arg(args[0], is_ident=False))
            val = str(self.format_intrinsic_arg(args[1], is_ident=False))
            rel_arg = str(self.format_intrinsic_arg(args[2], is_ident=False)) if len(args) >= 3 else "0"
            rel = "1" if rel_arg in ("True", "true", "1") else "0"
            self.instructions.append(
                IRRaw(opcode="clientdata", args=[chan, val, rel], loc=loc)
            )
            return "0"

        else:
            self.error(f"unknown compiler intrinsic: '{func_name}'", call)

    def compile_draw_method(
        self,
        call: ast.Call,
        target_dest: Optional[str] = None,
        is_statement: bool = False,
    ) -> str:
        """Compile draw.<method>(...) call into Mindustry 'draw' or 'drawflush' instruction."""
        loc = self.loc(call)
        assert isinstance(call.func, ast.Attribute)
        method_name = call.func.attr
        args = call.args

        # Mindustry v160.7 Draw sub-commands mapping
        if method_name == "clear":
            if len(args) != 3 or call.keywords:
                self.error("invalid arguments for draw.clear: expected draw.clear(r, g, b)", call)
            r = str(self.format_intrinsic_arg(args[0], is_ident=False))
            g = str(self.format_intrinsic_arg(args[1], is_ident=False))
            b = str(self.format_intrinsic_arg(args[2], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="draw", args=["clear", r, g, b, "0", "0", "0"], loc=loc)
            )
            return "0"

        elif method_name == "color":
            # color(r, g, b, a=255)
            a_arg = None
            pos_args = list(args)
            for kw in call.keywords:
                if kw.arg == "a":
                    a_arg = kw.value
                else:
                    self.error(f"unexpected keyword argument '{kw.arg}' in draw.color", kw)
            if len(pos_args) == 4 and a_arg is None:
                a_arg = pos_args[3]
                pos_args = pos_args[:3]
            elif len(pos_args) == 3:
                pass
            else:
                self.error("invalid arguments for draw.color: expected draw.color(r, g, b, [a=255])", call)
            r = str(self.format_intrinsic_arg(pos_args[0], is_ident=False))
            g = str(self.format_intrinsic_arg(pos_args[1], is_ident=False))
            b = str(self.format_intrinsic_arg(pos_args[2], is_ident=False))
            a = str(self.format_intrinsic_arg(a_arg, is_ident=False)) if a_arg is not None else "255"
            self.instructions.append(
                IRRaw(opcode="draw", args=["color", r, g, b, a, "0", "0"], loc=loc)
            )
            return "0"

        elif method_name == "col":
            if len(args) != 1 or call.keywords:
                self.error("invalid arguments for draw.col: expected draw.col(color)", call)
            color = str(self.format_intrinsic_arg(args[0], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="draw", args=["col", color, "0", "0", "0", "0", "0"], loc=loc)
            )
            return "0"

        elif method_name == "stroke":
            if len(args) != 1 or call.keywords:
                self.error("invalid arguments for draw.stroke: expected draw.stroke(width)", call)
            width = str(self.format_intrinsic_arg(args[0], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="draw", args=["stroke", width, "0", "0", "0", "0", "0"], loc=loc)
            )
            return "0"

        elif method_name == "line":
            if len(args) != 4 or call.keywords:
                self.error("invalid arguments for draw.line: expected draw.line(x1, y1, x2, y2)", call)
            x1 = str(self.format_intrinsic_arg(args[0], is_ident=False))
            y1 = str(self.format_intrinsic_arg(args[1], is_ident=False))
            x2 = str(self.format_intrinsic_arg(args[2], is_ident=False))
            y2 = str(self.format_intrinsic_arg(args[3], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="draw", args=["line", x1, y1, x2, y2, "0", "0"], loc=loc)
            )
            return "0"

        elif method_name == "rect":
            if len(args) != 4 or call.keywords:
                self.error("invalid arguments for draw.rect: expected draw.rect(x, y, width, height)", call)
            x = str(self.format_intrinsic_arg(args[0], is_ident=False))
            y = str(self.format_intrinsic_arg(args[1], is_ident=False))
            w = str(self.format_intrinsic_arg(args[2], is_ident=False))
            h = str(self.format_intrinsic_arg(args[3], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="draw", args=["rect", x, y, w, h, "0", "0"], loc=loc)
            )
            return "0"

        elif method_name in ("line_rect", "lineRect"):
            if len(args) != 4 or call.keywords:
                self.error(f"invalid arguments for draw.{method_name}: expected draw.{method_name}(x, y, width, height)", call)
            x = str(self.format_intrinsic_arg(args[0], is_ident=False))
            y = str(self.format_intrinsic_arg(args[1], is_ident=False))
            w = str(self.format_intrinsic_arg(args[2], is_ident=False))
            h = str(self.format_intrinsic_arg(args[3], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="draw", args=["lineRect", x, y, w, h, "0", "0"], loc=loc)
            )
            return "0"

        elif method_name == "poly":
            rot_arg = None
            pos_args = list(args)
            for kw in call.keywords:
                if kw.arg == "rotation":
                    rot_arg = kw.value
                else:
                    self.error(f"unexpected keyword argument '{kw.arg}' in draw.poly", kw)
            if len(pos_args) == 5 and rot_arg is None:
                rot_arg = pos_args[4]
                pos_args = pos_args[:4]
            elif len(pos_args) == 4:
                pass
            else:
                self.error("invalid arguments for draw.poly: expected draw.poly(x, y, sides, radius, [rotation=0])", call)
            x = str(self.format_intrinsic_arg(pos_args[0], is_ident=False))
            y = str(self.format_intrinsic_arg(pos_args[1], is_ident=False))
            sides = str(self.format_intrinsic_arg(pos_args[2], is_ident=False))
            radius = str(self.format_intrinsic_arg(pos_args[3], is_ident=False))
            rot = str(self.format_intrinsic_arg(rot_arg, is_ident=False)) if rot_arg is not None else "0"
            self.instructions.append(
                IRRaw(opcode="draw", args=["poly", x, y, sides, radius, rot, "0"], loc=loc)
            )
            return "0"

        elif method_name in ("line_poly", "linePoly"):
            rot_arg = None
            pos_args = list(args)
            for kw in call.keywords:
                if kw.arg == "rotation":
                    rot_arg = kw.value
                else:
                    self.error(f"unexpected keyword argument '{kw.arg}' in draw.{method_name}", kw)
            if len(pos_args) == 5 and rot_arg is None:
                rot_arg = pos_args[4]
                pos_args = pos_args[:4]
            elif len(pos_args) == 4:
                pass
            else:
                self.error(f"invalid arguments for draw.{method_name}: expected draw.{method_name}(x, y, sides, radius, [rotation=0])", call)
            x = str(self.format_intrinsic_arg(pos_args[0], is_ident=False))
            y = str(self.format_intrinsic_arg(pos_args[1], is_ident=False))
            sides = str(self.format_intrinsic_arg(pos_args[2], is_ident=False))
            radius = str(self.format_intrinsic_arg(pos_args[3], is_ident=False))
            rot = str(self.format_intrinsic_arg(rot_arg, is_ident=False)) if rot_arg is not None else "0"
            self.instructions.append(
                IRRaw(opcode="draw", args=["linePoly", x, y, sides, radius, rot, "0"], loc=loc)
            )
            return "0"

        elif method_name == "triangle":
            if len(args) != 6 or call.keywords:
                self.error("invalid arguments for draw.triangle: expected draw.triangle(x1, y1, x2, y2, x3, y3)", call)
            x1 = str(self.format_intrinsic_arg(args[0], is_ident=False))
            y1 = str(self.format_intrinsic_arg(args[1], is_ident=False))
            x2 = str(self.format_intrinsic_arg(args[2], is_ident=False))
            y2 = str(self.format_intrinsic_arg(args[3], is_ident=False))
            x3 = str(self.format_intrinsic_arg(args[4], is_ident=False))
            y3 = str(self.format_intrinsic_arg(args[5], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="draw", args=["triangle", x1, y1, x2, y2, x3, y3], loc=loc)
            )
            return "0"

        elif method_name == "image":
            size_arg = None
            rot_arg = None
            pos_args = list(args)
            for kw in call.keywords:
                if kw.arg == "size":
                    size_arg = kw.value
                elif kw.arg == "rotation":
                    rot_arg = kw.value
                else:
                    self.error(f"unexpected keyword argument '{kw.arg}' in draw.image", kw)
            if len(pos_args) == 5 and size_arg is None and rot_arg is None:
                size_arg = pos_args[3]
                rot_arg = pos_args[4]
                pos_args = pos_args[:3]
            elif len(pos_args) == 4 and size_arg is None:
                size_arg = pos_args[3]
                pos_args = pos_args[:3]
            elif len(pos_args) == 3:
                pass
            else:
                self.error("invalid arguments for draw.image: expected draw.image(x, y, image, [size=32], [rotation=0])", call)
            x = str(self.format_intrinsic_arg(pos_args[0], is_ident=False))
            y = str(self.format_intrinsic_arg(pos_args[1], is_ident=False))
            img = str(self.format_intrinsic_arg(pos_args[2], is_ident=True))
            size = str(self.format_intrinsic_arg(size_arg, is_ident=False)) if size_arg is not None else "32"
            rot = str(self.format_intrinsic_arg(rot_arg, is_ident=False)) if rot_arg is not None else "0"
            self.instructions.append(
                IRRaw(opcode="draw", args=["image", x, y, img, size, rot, "0"], loc=loc)
            )
            return "0"

        elif method_name == "print":
            align_arg = None
            pos_args = list(args)
            for kw in call.keywords:
                if kw.arg == "align":
                    align_arg = kw.value
                else:
                    self.error(f"unexpected keyword argument '{kw.arg}' in draw.print", kw)
            if len(pos_args) == 3 and align_arg is None:
                align_arg = pos_args[2]
                pos_args = pos_args[:2]
            elif len(pos_args) == 2:
                pass
            else:
                self.error("invalid arguments for draw.print: expected draw.print(x, y, [align=0])", call)
            x = str(self.format_intrinsic_arg(pos_args[0], is_ident=False))
            y = str(self.format_intrinsic_arg(pos_args[1], is_ident=False))
            if align_arg is not None:
                align_val = self.format_intrinsic_arg(align_arg, is_ident=False)
                raw_str = str(align_val)
                if raw_str in REG_ALIGN.by_token or raw_str in REG_ALIGN.by_source_name:
                    align = REG_ALIGN.get_token(raw_str)
                elif raw_str.startswith('"') and raw_str.endswith('"'):
                    unquoted = raw_str[1:-1]
                    if unquoted in REG_ALIGN.by_token or unquoted in REG_ALIGN.by_source_name:
                        align = REG_ALIGN.get_token(unquoted)
                    else:
                        self.error(f"unknown align '{unquoted}'", align_arg)
                elif raw_str.isdigit() or (raw_str.startswith("-") and raw_str[1:].isdigit()) or raw_str.isidentifier():
                    align = raw_str
                else:
                    self.error(f"invalid align argument '{raw_str}'", align_arg)
            else:
                align = "0"
            self.instructions.append(
                IRRaw(opcode="draw", args=["print", x, y, align, "0", "0", "0"], loc=loc)
            )
            return "0"

        elif method_name == "translate":
            if len(args) != 2 or call.keywords:
                self.error("invalid arguments for draw.translate: expected draw.translate(x, y)", call)
            x = str(self.format_intrinsic_arg(args[0], is_ident=False))
            y = str(self.format_intrinsic_arg(args[1], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="draw", args=["translate", x, y, "0", "0", "0", "0"], loc=loc)
            )
            return "0"

        elif method_name == "scale":
            if len(args) != 2 or call.keywords:
                self.error("invalid arguments for draw.scale: expected draw.scale(x, y)", call)
            x = str(self.format_intrinsic_arg(args[0], is_ident=False))
            y = str(self.format_intrinsic_arg(args[1], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="draw", args=["scale", x, y, "0", "0", "0", "0"], loc=loc)
            )
            return "0"

        elif method_name == "rotate":
            if len(args) != 1 or call.keywords:
                self.error("invalid arguments for draw.rotate: expected draw.rotate(degrees)", call)
            deg = str(self.format_intrinsic_arg(args[0], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="draw", args=["rotate", "0", "0", deg, "0", "0", "0"], loc=loc)
            )
            return "0"

        elif method_name == "reset":
            if len(args) != 0 or call.keywords:
                self.error("invalid arguments for draw.reset: expected draw.reset()", call)
            self.instructions.append(
                IRRaw(opcode="draw", args=["reset", "0", "0", "0", "0", "0", "0"], loc=loc)
            )
            return "0"

        elif method_name == "flush":
            if len(args) != 1 or call.keywords:
                self.error("invalid arguments for draw.flush: expected draw.flush(display)", call)
            target = str(self.format_intrinsic_arg(args[0], is_ident=True))
            self.instructions.append(
                IRRaw(opcode="drawflush", args=[target], loc=loc)
            )
            return "0"

        else:
            self.error(f"unknown draw method: 'draw.{method_name}'", call)

    def compile_ucontrol_method(
        self,
        call: ast.Call,
        target_dest: Optional[str] = None,
        is_statement: bool = False,
    ) -> str:
        """Compile ucontrol.<method>(...) call into Mindustry 'ucontrol' instruction."""
        loc = self.loc(call)
        assert isinstance(call.func, ast.Attribute)
        method_name = call.func.attr
        args = call.args
        ns = call.func.value.id if isinstance(call.func.value, ast.Name) else "ucontrol"

        # Mindustry v160.7 UnitControl mapping
        if method_name in ("idle", "stop"):
            if len(args) != 0 or call.keywords:
                self.error(f"invalid arguments for {ns}.{method_name}: expected {ns}.{method_name}()", call)
            self.instructions.append(
                IRRaw(opcode="ucontrol", args=[method_name, "0", "0", "0", "0", "0"], loc=loc)
            )
            return "0"

        elif method_name == "move":
            if len(args) != 2 or call.keywords:
                self.error(f"invalid arguments for {ns}.move: expected {ns}.move(x, y)", call)
            x = str(self.format_intrinsic_arg(args[0], is_ident=False))
            y = str(self.format_intrinsic_arg(args[1], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="ucontrol", args=["move", x, y, "0", "0", "0"], loc=loc)
            )
            return "0"

        elif method_name == "approach":
            if len(args) != 3 or call.keywords:
                self.error(f"invalid arguments for {ns}.approach: expected {ns}.approach(x, y, radius)", call)
            x = str(self.format_intrinsic_arg(args[0], is_ident=False))
            y = str(self.format_intrinsic_arg(args[1], is_ident=False))
            r = str(self.format_intrinsic_arg(args[2], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="ucontrol", args=["approach", x, y, r, "0", "0"], loc=loc)
            )
            return "0"

        elif method_name == "pathfind":
            if len(args) != 2 or call.keywords:
                self.error(f"invalid arguments for {ns}.pathfind: expected {ns}.pathfind(x, y)", call)
            x = str(self.format_intrinsic_arg(args[0], is_ident=False))
            y = str(self.format_intrinsic_arg(args[1], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="ucontrol", args=["pathfind", x, y, "0", "0", "0"], loc=loc)
            )
            return "0"

        elif method_name in ("auto_pathfind", "autoPathfind"):
            if len(args) != 0 or call.keywords:
                self.error(f"invalid arguments for {ns}.{method_name}: expected {ns}.{method_name}()", call)
            self.instructions.append(
                IRRaw(opcode="ucontrol", args=["autoPathfind", "0", "0", "0", "0", "0"], loc=loc)
            )
            return "0"

        elif method_name == "boost":
            if len(args) != 1 or call.keywords:
                self.error(f"invalid arguments for {ns}.boost: expected {ns}.boost(enable)", call)
            enable = str(self.format_intrinsic_arg(args[0], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="ucontrol", args=["boost", enable, "0", "0", "0", "0"], loc=loc)
            )
            return "0"

        elif method_name == "target":
            if len(args) != 3 or call.keywords:
                self.error(f"invalid arguments for {ns}.target: expected {ns}.target(x, y, shoot)", call)
            x = str(self.format_intrinsic_arg(args[0], is_ident=False))
            y = str(self.format_intrinsic_arg(args[1], is_ident=False))
            shoot = str(self.format_intrinsic_arg(args[2], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="ucontrol", args=["target", x, y, shoot, "0", "0"], loc=loc)
            )
            return "0"

        elif method_name == "targetp":
            if len(args) != 2 or call.keywords:
                self.error(f"invalid arguments for {ns}.targetp: expected {ns}.targetp(unit, shoot)", call)
            unit = str(self.format_intrinsic_arg(args[0], is_ident=True))
            shoot = str(self.format_intrinsic_arg(args[1], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="ucontrol", args=["targetp", unit, shoot, "0", "0", "0"], loc=loc)
            )
            return "0"

        elif method_name in ("item_drop", "itemDrop"):
            if len(args) != 2 or call.keywords:
                self.error(f"invalid arguments for {ns}.{method_name}: expected {ns}.{method_name}(to, amount)", call)
            to = str(self.format_intrinsic_arg(args[0], is_ident=True))
            amount = str(self.format_intrinsic_arg(args[1], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="ucontrol", args=["itemDrop", to, amount, "0", "0", "0"], loc=loc)
            )
            return "0"

        elif method_name in ("item_take", "itemTake"):
            if len(args) != 3 or call.keywords:
                self.error(f"invalid arguments for {ns}.{method_name}: expected {ns}.{method_name}(from_, item, amount)", call)
            from_ = str(self.format_intrinsic_arg(args[0], is_ident=True))
            item = str(self.format_intrinsic_arg(args[1], is_ident=True))
            amount = str(self.format_intrinsic_arg(args[2], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="ucontrol", args=["itemTake", from_, item, amount, "0", "0"], loc=loc)
            )
            return "0"

        elif method_name in ("pay_drop", "payDrop"):
            if len(args) != 0 or call.keywords:
                self.error(f"invalid arguments for {ns}.{method_name}: expected {ns}.{method_name}()", call)
            self.instructions.append(
                IRRaw(opcode="ucontrol", args=["payDrop", "0", "0", "0", "0", "0"], loc=loc)
            )
            return "0"

        elif method_name in ("pay_take", "payTake"):
            if len(args) != 1 or call.keywords:
                self.error(f"invalid arguments for {ns}.{method_name}: expected {ns}.{method_name}(take_units)", call)
            take_units = str(self.format_intrinsic_arg(args[0], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="ucontrol", args=["payTake", take_units, "0", "0", "0", "0"], loc=loc)
            )
            return "0"

        elif method_name in ("pay_enter", "payEnter"):
            if len(args) != 0 or call.keywords:
                self.error(f"invalid arguments for {ns}.{method_name}: expected {ns}.{method_name}()", call)
            self.instructions.append(
                IRRaw(opcode="ucontrol", args=["payEnter", "0", "0", "0", "0", "0"], loc=loc)
            )
            return "0"

        elif method_name == "mine":
            if len(args) != 2 or call.keywords:
                self.error(f"invalid arguments for {ns}.mine: expected {ns}.mine(x, y)", call)
            x = str(self.format_intrinsic_arg(args[0], is_ident=False))
            y = str(self.format_intrinsic_arg(args[1], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="ucontrol", args=["mine", x, y, "0", "0", "0"], loc=loc)
            )
            return "0"

        elif method_name == "flag":
            if len(args) != 1 or call.keywords:
                self.error(f"invalid arguments for {ns}.flag: expected {ns}.flag(value)", call)
            val = str(self.format_intrinsic_arg(args[0], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="ucontrol", args=["flag", val, "0", "0", "0", "0"], loc=loc)
            )
            return "0"

        elif method_name == "build":
            if len(args) != 5 or call.keywords:
                self.error(f"invalid arguments for {ns}.build: expected {ns}.build(x, y, block, rotation, config)", call)
            x = str(self.format_intrinsic_arg(args[0], is_ident=False))
            y = str(self.format_intrinsic_arg(args[1], is_ident=False))
            block = str(self.format_intrinsic_arg(args[2], is_ident=True))
            rot = str(self.format_intrinsic_arg(args[3], is_ident=False))
            config = str(self.format_intrinsic_arg(args[4], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="ucontrol", args=["build", x, y, block, rot, config], loc=loc)
            )
            return "0"

        elif method_name == "deconstruct":
            if len(args) != 2 or call.keywords:
                self.error(f"invalid arguments for {ns}.deconstruct: expected {ns}.deconstruct(x, y)", call)
            x = str(self.format_intrinsic_arg(args[0], is_ident=False))
            y = str(self.format_intrinsic_arg(args[1], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="ucontrol", args=["deconstruct", x, y, "0", "0", "0"], loc=loc)
            )
            return "0"

        elif method_name in ("get_block", "getBlock"):
            if len(args) != 5 or call.keywords:
                self.error(f"invalid arguments for {ns}.{method_name}: expected {ns}.{method_name}(x, y, out_type, out_building, out_floor)", call)
            x = str(self.format_intrinsic_arg(args[0], is_ident=False))
            y = str(self.format_intrinsic_arg(args[1], is_ident=False))
            out_t = str(self.format_intrinsic_arg(args[2], is_ident=True))
            out_b = str(self.format_intrinsic_arg(args[3], is_ident=True))
            out_f = str(self.format_intrinsic_arg(args[4], is_ident=True))
            self.instructions.append(
                IRRaw(opcode="ucontrol", args=["getBlock", x, y, out_t, out_b, out_f], loc=loc)
            )
            return "0"

        elif method_name == "within":
            if len(args) != 4 or call.keywords:
                self.error(f"invalid arguments for {ns}.within: expected {ns}.within(x, y, radius, out_result)", call)
            x = str(self.format_intrinsic_arg(args[0], is_ident=False))
            y = str(self.format_intrinsic_arg(args[1], is_ident=False))
            r = str(self.format_intrinsic_arg(args[2], is_ident=False))
            out_res = str(self.format_intrinsic_arg(args[3], is_ident=True))
            self.instructions.append(
                IRRaw(opcode="ucontrol", args=["within", x, y, r, out_res, "0"], loc=loc)
            )
            return "0"

        elif method_name == "unbind":
            if len(args) != 0 or call.keywords:
                self.error(f"invalid arguments for {ns}.unbind: expected {ns}.unbind()", call)
            self.instructions.append(
                IRRaw(opcode="ucontrol", args=["unbind", "0", "0", "0", "0", "0"], loc=loc)
            )
            return "0"

        else:
            self.error(f"unknown ucontrol method: '{ns}.{method_name}'", call)

    def compile_ulocate_method(
        self,
        call: ast.Call,
        target_dest: Optional[str] = None,
        is_statement: bool = False,
    ) -> str:
        """Compile ulocate.<method>(...) call into Mindustry 'ulocate' instruction."""
        loc = self.loc(call)
        assert isinstance(call.func, ast.Attribute)
        method_name = call.func.attr
        args = call.args
        ns = call.func.value.id if isinstance(call.func.value, ast.Name) else "ulocate"

        # Mindustry v160.7 UnitLocate mapping
        if method_name == "ore":
            if len(args) == 1 and not call.keywords:
                self.error(f"invalid arguments for {ns}.ore: for statement calls expected {ns}.ore(ore, out_x, out_y, out_found, [out_build]); for tuple unpacking use: out_x, out_y, out_found = {ns}.ore(ore)", call)
            elif len(args) == 4 and not call.keywords:
                ore = str(self.format_intrinsic_arg(args[0], is_ident=True))
                out_x = str(self.format_intrinsic_arg(args[1], is_ident=True))
                out_y = str(self.format_intrinsic_arg(args[2], is_ident=True))
                out_found = str(self.format_intrinsic_arg(args[3], is_ident=True))
                out_build = self.new_temp(loc)
            elif len(args) == 5 and not call.keywords:
                ore = str(self.format_intrinsic_arg(args[0], is_ident=True))
                out_x = str(self.format_intrinsic_arg(args[1], is_ident=True))
                out_y = str(self.format_intrinsic_arg(args[2], is_ident=True))
                out_found = str(self.format_intrinsic_arg(args[3], is_ident=True))
                out_build = str(self.format_intrinsic_arg(args[4], is_ident=True))
            else:
                self.error(f"invalid arguments for {ns}.ore: expected {ns}.ore(ore, out_x, out_y, out_found, [out_build]) or tuple unpacking", call)
            self.instructions.append(
                IRRaw(opcode="ulocate", args=["ore", "core", "true", ore, out_x, out_y, out_found, out_build], loc=loc)
            )
            return "0"

        elif method_name == "building":
            if len(args) == 2 and not call.keywords:
                self.error(f"invalid arguments for {ns}.building: for statement calls expected {ns}.building(group, enemy, out_x, out_y, out_found, out_building); for tuple unpacking use: core_x, core_y, found, building = {ns}.building(group, enemy)", call)
            elif len(args) != 6 or call.keywords:
                self.error(f"invalid arguments for {ns}.building: expected {ns}.building(group, enemy, out_x, out_y, out_found, out_building) or tuple unpacking", call)
            group = str(self.format_intrinsic_arg(args[0], is_ident=True))
            enemy = str(self.format_intrinsic_arg(args[1], is_ident=False))
            out_x = str(self.format_intrinsic_arg(args[2], is_ident=True))
            out_y = str(self.format_intrinsic_arg(args[3], is_ident=True))
            out_found = str(self.format_intrinsic_arg(args[4], is_ident=True))
            out_build = str(self.format_intrinsic_arg(args[5], is_ident=True))
            self.instructions.append(
                IRRaw(opcode="ulocate", args=["building", group, enemy, "@copper", out_x, out_y, out_found, out_build], loc=loc)
            )
            return "0"

        elif method_name == "spawn":
            if len(args) == 0 and not call.keywords:
                self.error(f"invalid arguments for {ns}.spawn: for statement calls expected {ns}.spawn(out_x, out_y, out_found, [out_build]); for tuple unpacking use: out_x, out_y, out_found, out_build = {ns}.spawn()", call)
            elif len(args) == 3 and not call.keywords:
                out_x = str(self.format_intrinsic_arg(args[0], is_ident=True))
                out_y = str(self.format_intrinsic_arg(args[1], is_ident=True))
                out_found = str(self.format_intrinsic_arg(args[2], is_ident=True))
                out_build = self.new_temp(loc)
            elif len(args) == 4 and not call.keywords:
                out_x = str(self.format_intrinsic_arg(args[0], is_ident=True))
                out_y = str(self.format_intrinsic_arg(args[1], is_ident=True))
                out_found = str(self.format_intrinsic_arg(args[2], is_ident=True))
                out_build = str(self.format_intrinsic_arg(args[3], is_ident=True))
            else:
                self.error(f"invalid arguments for {ns}.spawn: expected {ns}.spawn(out_x, out_y, out_found, [out_build]) or tuple unpacking", call)
            self.instructions.append(
                IRRaw(opcode="ulocate", args=["spawn", "core", "true", "@copper", out_x, out_y, out_found, out_build], loc=loc)
            )
            return "0"

        elif method_name == "damaged":
            if len(args) == 0 and not call.keywords:
                self.error(f"invalid arguments for {ns}.damaged: for statement calls expected {ns}.damaged(out_x, out_y, out_found, out_building); for tuple unpacking use: out_x, out_y, out_found, out_build = {ns}.damaged()", call)
            elif len(args) != 4 or call.keywords:
                self.error(f"invalid arguments for {ns}.damaged: expected {ns}.damaged(out_x, out_y, out_found, out_building) or tuple unpacking", call)
            out_x = str(self.format_intrinsic_arg(args[0], is_ident=True))
            out_y = str(self.format_intrinsic_arg(args[1], is_ident=True))
            out_found = str(self.format_intrinsic_arg(args[2], is_ident=True))
            out_build = str(self.format_intrinsic_arg(args[3], is_ident=True))
            self.instructions.append(
                IRRaw(opcode="ulocate", args=["damaged", "core", "true", "@copper", out_x, out_y, out_found, out_build], loc=loc)
            )
            return "0"

        else:
            self.error(f"unknown ulocate method: '{ns}.{method_name}'", call)

    def compile_op_method(
        self,
        call: ast.Call,
        target_dest: Optional[str] = None,
        is_statement: bool = False,
    ) -> str:
        """Compile op.<method>(...) call into Mindustry 'op' instruction."""
        loc = self.loc(call)
        assert isinstance(call.func, ast.Attribute)
        method_name = call.func.attr
        args = call.args

        if call.keywords:
            self.error(f"keyword arguments are not supported in op.{method_name}()", call)

        op_name = OP_METHOD_NAME_MAP.get(method_name)
        if op_name is None:
            self.error(f"unknown op method: 'op.{method_name}'", call)

        is_unary = REG_LOGIC_OPS.is_unary(op_name)

        if is_unary:
            if len(args) == 2:
                # Statement form: op.<method>(dest, a)
                dest = str(self.format_intrinsic_arg(args[0], is_ident=True))
                a = str(self.format_intrinsic_arg(args[1], is_ident=False))
                self.instructions.append(
                    IROp(op=op_name, dest=dest, a=a, b="0", loc=loc)
                )
                if target_dest is not None and target_dest != dest:
                    self.instructions.append(IRSet(to=target_dest, from_=dest, loc=loc))
                    return target_dest
                return dest
            elif len(args) == 1:
                # Expression form: dest = op.<method>(a)
                dest = target_dest if target_dest is not None else self.new_temp(loc)
                a = str(self.format_intrinsic_arg(args[0], is_ident=False))
                self.instructions.append(
                    IROp(op=op_name, dest=dest, a=a, b="0", loc=loc)
                )
                return dest
            elif len(args) == 0:
                self.error(
                    f"unary operation 'op.{method_name}' requires 1 operand (expression form: op.{method_name}(a)) or 2 arguments (statement form: op.{method_name}(dest, a)), got 0",
                    call,
                )
            else:
                self.error(
                    f"unary operation 'op.{method_name}' takes at most 2 arguments (dest, a), got {len(args)}",
                    call,
                )
        else:
            # Binary operation
            if len(args) == 3:
                # Statement form: op.<method>(dest, a, b)
                dest = str(self.format_intrinsic_arg(args[0], is_ident=True))
                a = str(self.format_intrinsic_arg(args[1], is_ident=False))
                b = str(self.format_intrinsic_arg(args[2], is_ident=False))
                self.instructions.append(
                    IROp(op=op_name, dest=dest, a=a, b=b, loc=loc)
                )
                if target_dest is not None and target_dest != dest:
                    self.instructions.append(IRSet(to=target_dest, from_=dest, loc=loc))
                    return target_dest
                return dest
            elif len(args) == 2:
                # Expression form: dest = op.<method>(a, b)
                dest = target_dest if target_dest is not None else self.new_temp(loc)
                a = str(self.format_intrinsic_arg(args[0], is_ident=False))
                b = str(self.format_intrinsic_arg(args[1], is_ident=False))
                self.instructions.append(
                    IROp(op=op_name, dest=dest, a=a, b=b, loc=loc)
                )
                return dest
            elif len(args) < 2:
                self.error(
                    f"binary operation 'op.{method_name}' requires 2 operands (expression form: op.{method_name}(a, b)) or 3 arguments (statement form: op.{method_name}(dest, a, b)), got {len(args)}",
                    call,
                )
            else:
                self.error(
                    f"binary operation 'op.{method_name}' takes at most 3 arguments (dest, a, b), got {len(args)}",
                    call,
                )

    def compile_cutscene_method(
        self,
        call: ast.Call,
        target_dest: Optional[str] = None,
        is_statement: bool = False,
    ) -> str:
        """Compile cutscene.<method>(...) call into Mindustry 'cutscene' instruction."""
        loc = self.loc(call)
        assert isinstance(call.func, ast.Attribute)
        method_name = call.func.attr
        args = call.args

        if method_name == "active":
            if call.keywords:
                self.error("cutscene.active does not support keyword arguments", call)
            if target_dest is not None or not is_statement:
                dest = target_dest if target_dest is not None else self.new_temp(loc)
            elif len(args) == 1:
                dest = str(self.format_intrinsic_arg(args[0], is_ident=True))
            else:
                self.error("cutscene.active requires a destination variable or assignment (e.g. res = cutscene.active())", call)
            self.instructions.append(
                IRRaw(opcode="cutscene", args=["active", dest, "0", "0", "0"], loc=loc)
            )
            return dest

        elif method_name in ("get_hud", "getHud"):
            if call.keywords:
                self.error(f"cutscene.{method_name} does not support keyword arguments", call)
            if target_dest is not None or not is_statement:
                dest = target_dest if target_dest is not None else self.new_temp(loc)
            elif len(args) == 1:
                dest = str(self.format_intrinsic_arg(args[0], is_ident=True))
            else:
                self.error(f"cutscene.{method_name} requires a destination variable or assignment (e.g. res = cutscene.{method_name}())", call)
            self.instructions.append(
                IRRaw(opcode="cutscene", args=["getHud", dest, "0", "0", "0"], loc=loc)
            )
            return dest

        elif method_name == "pan":
            if not (2 <= len(args) <= 3) or call.keywords:
                self.error("invalid arguments for cutscene.pan: expected cutscene.pan(x, y, [speed=0.06])", call)
            x = str(self.format_intrinsic_arg(args[0], is_ident=False))
            y = str(self.format_intrinsic_arg(args[1], is_ident=False))
            speed = str(self.format_intrinsic_arg(args[2], is_ident=False)) if len(args) == 3 else "0.06"
            self.instructions.append(
                IRRaw(opcode="cutscene", args=["pan", x, y, speed, "0"], loc=loc)
            )
            return "0"

        elif method_name == "zoom":
            if len(args) != 1 or call.keywords:
                self.error("invalid arguments for cutscene.zoom: expected cutscene.zoom(level)", call)
            level = str(self.format_intrinsic_arg(args[0], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="cutscene", args=["zoom", level, "0", "0", "0"], loc=loc)
            )
            return "0"

        elif method_name == "stop":
            if len(args) != 0 or call.keywords:
                self.error("invalid arguments for cutscene.stop: expected cutscene.stop()", call)
            self.instructions.append(
                IRRaw(opcode="cutscene", args=["stop", "0", "0", "0", "0"], loc=loc)
            )
            return "0"

        elif method_name == "shake":
            if len(args) != 2 or call.keywords:
                self.error("invalid arguments for cutscene.shake: expected cutscene.shake(amount, duration)", call)
            amount = str(self.format_intrinsic_arg(args[0], is_ident=False))
            duration = str(self.format_intrinsic_arg(args[1], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="cutscene", args=["shake", amount, duration, "0", "0"], loc=loc)
            )
            return "0"

        elif method_name in ("set_hud", "setHud"):
            if len(args) != 1 or call.keywords:
                self.error(f"invalid arguments for cutscene.{method_name}: expected cutscene.{method_name}(shown)", call)
            shown_arg = str(self.format_intrinsic_arg(args[0], is_ident=False))
            if shown_arg in ("True", "true"):
                shown = "1"
            elif shown_arg in ("False", "false"):
                shown = "0"
            else:
                shown = shown_arg
            self.instructions.append(
                IRRaw(opcode="cutscene", args=["setHud", shown, "0", "0", "0"], loc=loc)
            )
            return "0"

        else:
            self.error(f"unknown cutscene method: 'cutscene.{method_name}'", call)

    def compile_sound_method(
        self,
        call: ast.Call,
        target_dest: Optional[str] = None,
        is_statement: bool = False,
    ) -> str:
        loc = self.loc(call)
        assert isinstance(call.func, ast.Attribute)
        method_name = call.func.attr
        args = call.args

        if method_name == "play":
            # sound.play(id, [volume=1, pitch=1, pan=0, limit=True])
            if not (1 <= len(args) <= 5):
                self.error("invalid arguments for sound.play: expected sound.play(id, [volume=1, pitch=1, pan=0, limit=True])", call)
            id_ = str(self.format_intrinsic_arg(args[0], is_ident=True))
            volume = str(self.format_intrinsic_arg(args[1], is_ident=False)) if len(args) >= 2 else "1"
            pitch = str(self.format_intrinsic_arg(args[2], is_ident=False)) if len(args) >= 3 else "1"
            pan = str(self.format_intrinsic_arg(args[3], is_ident=False)) if len(args) >= 4 else "0"
            limit_arg = str(self.format_intrinsic_arg(args[4], is_ident=False)) if len(args) >= 5 else "true"
            limit = "true" if limit_arg in ("True", "true", "1") else ("false" if limit_arg in ("False", "false", "0") else limit_arg)
            self.instructions.append(
                IRRaw(opcode="playsound", args=["false", id_, volume, pitch, pan, "0", "0", limit], loc=loc)
            )
            return "0"

        elif method_name in ("play_at", "playAt"):
            # sound.play_at(id, x, y, [volume=1, pitch=1, limit=True])
            if not (3 <= len(args) <= 6):
                self.error(f"invalid arguments for sound.{method_name}: expected sound.{method_name}(id, x, y, [volume=1, pitch=1, limit=True])", call)
            id_ = str(self.format_intrinsic_arg(args[0], is_ident=True))
            x = str(self.format_intrinsic_arg(args[1], is_ident=False))
            y = str(self.format_intrinsic_arg(args[2], is_ident=False))
            volume = str(self.format_intrinsic_arg(args[3], is_ident=False)) if len(args) >= 4 else "1"
            pitch = str(self.format_intrinsic_arg(args[4], is_ident=False)) if len(args) >= 5 else "1"
            limit_arg = str(self.format_intrinsic_arg(args[5], is_ident=False)) if len(args) >= 6 else "true"
            limit = "true" if limit_arg in ("True", "true", "1") else ("false" if limit_arg in ("False", "false", "0") else limit_arg)
            self.instructions.append(
                IRRaw(opcode="playsound", args=["true", id_, volume, pitch, "0", x, y, limit], loc=loc)
            )
            return "0"

        else:
            self.error(f"unknown sound method: 'sound.{method_name}'", call)

    def compile_music_method(
        self,
        call: ast.Call,
        target_dest: Optional[str] = None,
        is_statement: bool = False,
    ) -> str:
        loc = self.loc(call)
        assert isinstance(call.func, ast.Attribute)
        method_name = call.func.attr
        args = call.args

        if method_name == "play":
            # music.play(name, [interrupt=True])
            if not (1 <= len(args) <= 2):
                self.error("invalid arguments for music.play: expected music.play(name, [interrupt=True])", call)
            name = str(self.format_intrinsic_arg(args[0], is_ident=False))
            intr_arg = str(self.format_intrinsic_arg(args[1], is_ident=False)) if len(args) >= 2 else "true"
            intr = "true" if intr_arg in ("True", "true", "1") else ("false" if intr_arg in ("False", "false", "0") else intr_arg)
            self.instructions.append(
                IRRaw(opcode="playmusic", args=[name, intr], loc=loc)
            )
            return "0"

        elif method_name == "stop":
            # music.stop() -> playmusic null false
            if len(args) != 0:
                self.error("invalid arguments for music.stop: expected music.stop()", call)
            self.instructions.append(
                IRRaw(opcode="playmusic", args=["null", "false"], loc=loc)
            )
            return "0"

        else:
            self.error(f"unknown music method: 'music.{method_name}'", call)

    def compile_marker_method(
        self,
        call: ast.Call,
        target_dest: Optional[str] = None,
        is_statement: bool = False,
    ) -> str:
        loc = self.loc(call)
        assert isinstance(call.func, ast.Attribute)
        method_name = call.func.attr
        args = call.args

        if method_name == "make":
            # marker.make(type, id, x, y, [replace=True])
            if not (4 <= len(args) <= 5):
                self.error("invalid arguments for marker.make: expected marker.make(type, id, x, y, [replace=True])", call)
            type_arg = self.format_intrinsic_arg(args[0], is_ident=True)
            type_snake = to_snake(type_arg).upper() if isinstance(type_arg, str) else str(type_arg)
            type_ = self.validate_arg(type_arg, REG_MARKER_TYPES, self.loc(args[0])) if type_snake in REG_MARKER_TYPES.by_source_name else str(type_arg)
            id_ = str(self.format_intrinsic_arg(args[1], is_ident=True))
            x = str(self.format_intrinsic_arg(args[2], is_ident=False))
            y = str(self.format_intrinsic_arg(args[3], is_ident=False))
            replace_arg = str(self.format_intrinsic_arg(args[4], is_ident=False)) if len(args) >= 5 else "true"
            replace = "true" if replace_arg in ("True", "true", "1") else ("false" if replace_arg in ("False", "false", "0") else replace_arg)
            self.instructions.append(
                IRRaw(opcode="makemarker", args=[type_, id_, x, y, replace], loc=loc)
            )
            return "0"

        ctrl_map = {
            "remove": ("remove", 0),
            "world": ("world", 1),
            "minimap": ("minimap", 1),
            "light": ("light", 1),
            "autoscale": ("autoscale", 1),
            "pos": ("pos", 2),
            "end_pos": ("endPos", 2),
            "endPos": ("endPos", 2),
            "draw_layer": ("drawLayer", 1),
            "drawLayer": ("drawLayer", 1),
            "color": ("color", 1),
            "radius": ("radius", 1),
            "stroke": ("stroke", 1),
            "outline": ("outline", 1),
            "rotation": ("rotation", 1),
            "shape": ("shape", 3),
            "arc": ("arc", 2),
            "flush_text": ("flushText", 1),
            "flushText": ("flushText", 1),
            "font_size": ("fontSize", 1),
            "fontSize": ("fontSize", 1),
            "text_height": ("textHeight", 1),
            "textHeight": ("textHeight", 1),
            "text_align": ("textAlign", 1),
            "textAlign": ("textAlign", 1),
            "line_align": ("lineAlign", 1),
            "lineAlign": ("lineAlign", 1),
            "label_flags": ("labelFlags", 2),
            "labelFlags": ("labelFlags", 2),
            "texture": ("texture", 2),
            "texture_size": ("textureSize", 2),
            "textureSize": ("textureSize", 2),
            "posi": ("posi", 3),
            "uvi": ("uvi", 3),
            "colori": ("colori", 2),
        }

        if method_name in ctrl_map:
            ctrl_type, expected_params = ctrl_map[method_name]
            if len(args) < 1:
                self.error(f"marker.{method_name} requires at least an id argument", call)
            id_ = str(self.format_intrinsic_arg(args[0], is_ident=True))
            p_args = args[1:]
            p1 = "0"
            p2 = "0"
            p3 = "0"
            if len(p_args) >= 1:
                p1_val = str(self.format_intrinsic_arg(p_args[0], is_ident=False))
                p1 = "1" if p1_val in ("True", "true") else ("0" if p1_val in ("False", "false") else p1_val)
            if len(p_args) >= 2:
                p2_val = str(self.format_intrinsic_arg(p_args[1], is_ident=False))
                p2 = "1" if p2_val in ("True", "true") else ("0" if p2_val in ("False", "false") else p2_val)
            if len(p_args) >= 3:
                p3_val = str(self.format_intrinsic_arg(p_args[2], is_ident=False))
                p3 = "1" if p3_val in ("True", "true") else ("0" if p3_val in ("False", "false") else p3_val)
            self.instructions.append(
                IRRaw(opcode="setmarker", args=[ctrl_type, id_, p1, p2, p3], loc=loc)
            )
            return "0"

        self.error(f"unknown marker method: 'marker.{method_name}'", call)


    def compile_fstring_print(self, node: ast.JoinedStr, loc: SourceLocation) -> str:
        """Compile a print(f"...") f-string call into MLog print and format opcodes."""
        formatted_values = [v for v in node.values if isinstance(v, ast.FormattedValue)]
        if len(formatted_values) > 10:
            self.error(
                "f-string supports at most 10 expressions (Mindustry format opcode supports placeholders {0} through {9})",
                node,
            )

        # 1. Left-to-right evaluation order of formatted expressions
        def _may_have_side_effects(expr_node: ast.AST) -> bool:
            for child in ast.walk(expr_node):
                if isinstance(child, ast.Call):
                    return True
            return False

        evaluated_args = []
        for idx, fv in enumerate(formatted_values):
            val = self.compile_expr(fv.value)
            val_loc = self.loc(fv.value)
            has_later_side_effects = any(
                _may_have_side_effects(later_fv.value)
                for later_fv in formatted_values[idx + 1:]
            )
            if has_later_side_effects and not isinstance(fv.value, ast.Constant):
                dest = self.new_temp(val_loc)
                self.instructions.append(IRSet(to=dest, from_=val, loc=val_loc))
                val = dest
            evaluated_args.append((val, val_loc))

        # 2. Build template string
        template_parts = []
        placeholder_idx = 0
        for part in node.values:
            if isinstance(part, ast.Constant):
                template_parts.append(str(part.value))
            elif isinstance(part, ast.FormattedValue):
                template_parts.append(f"{{{placeholder_idx}}}")
                placeholder_idx += 1
            else:
                self.error(f"unsupported f-string component: {type(part).__name__}", part)

        template_str = "".join(template_parts)
        template_mlog = self.format_constant(template_str, loc)

        # 3. Emit print "template"
        self.instructions.append(IRRaw(opcode="print", args=[template_mlog], loc=loc))

        # 4. Emit format for each evaluated argument in order
        for val, val_loc in evaluated_args:
            self.instructions.append(IRRaw(opcode="format", args=[val], loc=val_loc))

        return "0"

    def compile_unpacking_assignment(self, node: ast.Assign, target: Union[ast.Tuple, ast.List]) -> None:
        loc = self.loc(node)
        call = node.value
        assert isinstance(call, ast.Call)

        target_names = [self.format_name(elt.id, elt) for elt in target.elts]

        if isinstance(call.func, ast.Name) and call.func.id == "unpackcolor":
            args = call.args
            if call.keywords:
                self.error("unpackcolor does not support keyword arguments", call)
            if len(args) != 1:
                self.error(
                    f"invalid arguments for unpackcolor unpacking: expected unpackcolor(value), got {len(args)} arguments",
                    call,
                )
            if len(target_names) != 4:
                self.error(
                    f"unpackcolor unpacking expects exactly 4 target variables (out_r, out_g, out_b, out_a), got {len(target_names)}",
                    target,
                )
            value = str(self.format_intrinsic_arg(args[0], is_ident=False))
            self.instructions.append(
                IRRaw(opcode="unpackcolor", args=list(target_names) + [value], loc=loc)
            )
            return

        if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) and call.func.value.id == "ulocate":
            method_name = call.func.attr
            args = call.args

            if method_name == "building":
                if len(args) != 2 or call.keywords:
                    self.error("invalid arguments for ulocate.building unpacking: expected ulocate.building(group, enemy)", call)
                if len(target_names) not in (3, 4):
                    self.error(f"ulocate.building unpacking expects 3 or 4 target variables (out_x, out_y, out_found[, out_building]), got {len(target_names)}", target)
                group = str(self.format_intrinsic_arg(args[0], is_ident=True))
                enemy = str(self.format_intrinsic_arg(args[1], is_ident=False))
                out_x = target_names[0]
                out_y = target_names[1]
                out_found = target_names[2]
                out_build = target_names[3] if len(target_names) == 4 else self.new_temp(loc)
                self.instructions.append(
                    IRRaw(opcode="ulocate", args=["building", group, enemy, "@copper", out_x, out_y, out_found, out_build], loc=loc)
                )
                return

            elif method_name == "ore":
                if len(args) != 1 or call.keywords:
                    self.error("invalid arguments for ulocate.ore unpacking: expected ulocate.ore(ore)", call)
                if len(target_names) not in (3, 4):
                    self.error(f"ulocate.ore unpacking expects 3 or 4 target variables (out_x, out_y, out_found[, out_building]), got {len(target_names)}", target)
                ore = str(self.format_intrinsic_arg(args[0], is_ident=True))
                out_x = target_names[0]
                out_y = target_names[1]
                out_found = target_names[2]
                out_build = target_names[3] if len(target_names) == 4 else self.new_temp(loc)
                self.instructions.append(
                    IRRaw(opcode="ulocate", args=["ore", "core", "true", ore, out_x, out_y, out_found, out_build], loc=loc)
                )
                return

            elif method_name == "spawn":
                if len(args) != 0 or call.keywords:
                    self.error("invalid arguments for ulocate.spawn unpacking: expected ulocate.spawn()", call)
                if len(target_names) not in (3, 4):
                    self.error(f"ulocate.spawn unpacking expects 3 or 4 target variables (out_x, out_y, out_found[, out_building]), got {len(target_names)}", target)
                out_x = target_names[0]
                out_y = target_names[1]
                out_found = target_names[2]
                out_build = target_names[3] if len(target_names) == 4 else self.new_temp(loc)
                self.instructions.append(
                    IRRaw(opcode="ulocate", args=["spawn", "core", "true", "@copper", out_x, out_y, out_found, out_build], loc=loc)
                )
                return

            elif method_name == "damaged":
                if len(args) != 0 or call.keywords:
                    self.error("invalid arguments for ulocate.damaged unpacking: expected ulocate.damaged()", call)
                if len(target_names) not in (3, 4):
                    self.error(f"ulocate.damaged unpacking expects 3 or 4 target variables (out_x, out_y, out_found[, out_building]), got {len(target_names)}", target)
                out_x = target_names[0]
                out_y = target_names[1]
                out_found = target_names[2]
                out_build = target_names[3] if len(target_names) == 4 else self.new_temp(loc)
                self.instructions.append(
                    IRRaw(opcode="ulocate", args=["damaged", "core", "true", "@copper", out_x, out_y, out_found, out_build], loc=loc)
                )
                return
            else:
                self.error(f"unknown ulocate method: 'ulocate.{method_name}'", call)

        elif isinstance(call.func, ast.Name) and call.func.id == "ulocate":
            if not call.args:
                self.error("ulocate requires at least locate type argument", call)
            loc_type = str(self.format_intrinsic_arg(call.args[0], is_ident=True))
            if loc_type == "building":
                if len(call.args) != 3:
                    self.error("invalid arguments for ulocate('building', group, enemy)", call)
                if len(target_names) != 4:
                    self.error(f"ulocate('building', ...) unpacking expects exactly 4 target variables, got {len(target_names)}", target)
                group = str(self.format_intrinsic_arg(call.args[1], is_ident=True))
                enemy = str(self.format_intrinsic_arg(call.args[2], is_ident=False))
                out_x, out_y, out_found, out_build = target_names
                self.instructions.append(
                    IRRaw(opcode="ulocate", args=["building", group, enemy, "@copper", out_x, out_y, out_found, out_build], loc=loc)
                )
                return
            elif loc_type == "ore":
                if len(call.args) != 2:
                    self.error("invalid arguments for ulocate('ore', ore)", call)
                if len(target_names) != 3:
                    self.error(f"ulocate('ore', ...) unpacking expects exactly 3 target variables, got {len(target_names)}", target)
                ore = str(self.format_intrinsic_arg(call.args[1], is_ident=True))
                out_x, out_y, out_found = target_names
                self.instructions.append(
                    IRRaw(opcode="ulocate", args=["ore", "core", "true", ore, out_x, out_y, out_found, "building"], loc=loc)
                )
                return
            else:
                self.error(f"unsupported ulocate type for unpacking: '{loc_type}'", call)
        else:
            self.error("tuple unpacking is only supported for 'ulocate' and 'unpackcolor' operations", call)

    def compile_assignment(self, node: ast.Assign):
        """Compile an assignment statement: target = value"""
        target = node.targets[0]
        loc = self.loc(node)

        # Case 0: Tuple / List unpacking: core_x, core_y, found_core, core_build = ulocate.building(...)
        if isinstance(target, (ast.Tuple, ast.List)):
            self.compile_unpacking_assignment(node, target)
            return

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

        # Case 2: Target is Vars attribute: Vars.counter = value
        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "Vars":
            token = BUILTIN_VARIABLES_DATA.get(target.attr)
            if token is None:
                self.error(f"unknown Mindustry built-in variable: 'Vars.{target.attr}'", target)
            if token.readonly:
                self.error(f"cannot assign to read-only built-in variable 'Vars.{target.attr}' ('{token.token}')", target)
            self.compile_expr(node.value, target_dest=token.token)
            return

        # Case 3: Target is a simple Name
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

    def compile_aug_assign(self, node: ast.AugAssign):
        """Compile an augmented assignment statement: target op= value"""
        loc = self.loc(node)
        target = node.target
        op_cls = type(node.op)

        if op_cls not in AUG_ASSIGN_OPS:
            op_sym = "@=" if op_cls is ast.MatMult else f"{op_cls.__name__}="
            self.error(f"unsupported augmented assignment operator: '{op_sym}'", node)
        mlog_op, op_sym = AUG_ASSIGN_OPS[op_cls]

        # Case 1: Array element augmented assignment: arr[i] op= value
        if isinstance(target, ast.Subscript):
            if not isinstance(target.value, ast.Name):
                self.error("subscript augmented assignment is only supported on simple array names", target.value)
            arr_name = target.value.id
            arr = self.allocator.get_array(arr_name)
            if arr is None:
                self.error(f"'{arr_name}' is not an Array", target.value)

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

            # Type checking and semantic validation based on array dtype and operator
            if arr.dtype == "int":
                if _is_literal_float(node.value):
                    self.error("Array only stores integers; float literal is not supported", node.value)
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    self.error("Array only stores integers; string literal is not supported", node.value)
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, bool):
                    self.error("Array only stores integers; boolean literal is not supported", node.value)
                if op_cls in (ast.LShift, ast.RShift):
                    shift_val = _get_literal_int(node.value)
                    if shift_val is not None:
                        if shift_val < 0:
                            self.error("negative shift count is not supported", node.value)
                        elif shift_val >= 64:
                            self.error(
                                f"shift count {shift_val} >= 64 exceeds 64-bit integer width",
                                node.value,
                            )
            elif arr.dtype == "float":
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    self.error("Array of type 'float' only stores numbers; string literal is not supported", node.value)
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, bool):
                    self.error("Array of type 'float' only stores numbers; boolean literal is not supported", node.value)
                if op_cls in BITWISE_BIN_OPS:
                    self.error(f"unsupported operand type for bitwise operator {op_cls.__name__}: float Array", node)
                if _is_literal_float(node.value) and op_cls in BITWISE_BIN_OPS:
                    self.error(f"unsupported operand type for bitwise operator {op_cls.__name__}: float literal", node.value)
            elif arr.dtype == "bool":
                if op_cls not in (ast.BitAnd, ast.BitOr, ast.BitXor):
                    self.error(
                        f"unsupported augmented assignment operator '{op_sym}' for Array of type 'bool'; only '&=', '|=', '^=' are supported",
                        node,
                    )
                if _get_literal_int(node.value) is not None:
                    self.error("Array of type 'bool' only stores booleans; integer literal is not supported", node.value)
                if _is_literal_float(node.value):
                    self.error("Array of type 'bool' only stores booleans; float literal is not supported", node.value)
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    self.error("Array of type 'bool' only stores booleans; string literal is not supported", node.value)

            # Compute address / offset EXACTLY ONCE
            if literal_idx is not None:
                addr = str(arr.base_offset + literal_idx)
            else:
                idx_expr = self.compile_expr(target.slice)
                if arr.base_offset == 0:
                    addr = idx_expr
                else:
                    addr = self.new_temp(loc)
                    self.instructions.append(
                        IROp(op="add", dest=addr, a=idx_expr, b=str(arr.base_offset), loc=loc)
                    )

            # Read current value from array at addr
            cur_val = self.new_temp(loc)
            self.instructions.append(
                IRRaw(opcode="read", args=[cur_val, arr.block, addr], loc=loc)
            )

            # Evaluate RHS value
            target_tmp = self.new_temp(loc) if isinstance(node.value, ast.Call) else None
            val = self.compile_expr(node.value, target_dest=target_tmp)

            if arr.dtype == "bool":
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

            # Compute new value
            res = self.new_temp(loc)
            self.instructions.append(
                IROp(op=mlog_op, dest=res, a=cur_val, b=val, loc=loc)
            )

            # Write updated value back to array at addr
            self.instructions.append(
                IRRaw(opcode="write", args=[res, arr.block, addr], loc=loc)
            )
            return

        # Case 2: Target is Vars attribute: Vars.counter op= value
        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "Vars":
            token = BUILTIN_VARIABLES_DATA.get(target.attr)
            if token is None:
                self.error(f"unknown Mindustry built-in variable: 'Vars.{target.attr}'", target)
            if token.readonly:
                self.error(f"cannot assign to read-only built-in variable 'Vars.{target.attr}' ('{token.token}')", target)
            val = self.compile_expr(node.value)
            self.instructions.append(
                IROp(op=mlog_op, dest=token.token, a=token.token, b=val, loc=loc)
            )
            return

        # Case 3: Simple variable target: x op= value
        if not isinstance(target, ast.Name):
            self.error("augmented assignment target must be a simple variable name or array index (unpacking not supported)", target)

        target_name = target.id
        if target_name in self.allocator.arrays:
            self.error(f"cannot perform augmented assignment on Array variable '{target_name}'", target)

        # Bitwise operator checks on literal operands
        if op_cls in BITWISE_BIN_OPS:
            if _is_literal_float(node.value):
                self.error(
                    f"unsupported operand type for bitwise operator {op_cls.__name__}: float literal",
                    node.value,
                )
            if op_cls in (ast.LShift, ast.RShift):
                shift_val = _get_literal_int(node.value)
                if shift_val is not None:
                    if shift_val < 0:
                        self.error("negative shift count is not supported", node.value)
                    elif shift_val >= 64:
                        self.error(
                            f"shift count {shift_val} >= 64 exceeds 64-bit integer width",
                            node.value,
                        )

        formatted_target = self.format_name(target_name, target)
        val = self.compile_expr(node.value)
        self.instructions.append(
            IROp(op=mlog_op, dest=formatted_target, a=formatted_target, b=val, loc=loc)
        )

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

            if cmp_cls is ast.IsNot:
                # 'left is not right' is TRUE when left !== right, and FALSE when left === right.
                if false_label is not None and true_label is None:
                    # Jump to false_label when condition is FALSE (i.e. left === right).
                    self.instructions.append(
                        IRJump(
                            target=false_label,
                            cond="strictEqual",
                            a=left_val,
                            b=right_val,
                            loc=loc,
                        )
                    )
                elif true_label is not None and false_label is None:
                    # Jump to true_label when condition is TRUE (i.e. left !== right).
                    # Mindustry lacks strictNotEqual condition. Invert via skip jump.
                    skip_lbl = self.new_label("is_not_skip")
                    self.instructions.append(
                        IRJump(
                            target=skip_lbl,
                            cond="strictEqual",
                            a=left_val,
                            b=right_val,
                            loc=loc,
                        )
                    )
                    self.instructions.append(
                        IRJump(
                            target=true_label,
                            cond="always",
                            a="0",
                            b="0",
                            loc=loc,
                        )
                    )
                    self.instructions.append(IRLabel(name=skip_lbl, loc=loc))
                elif true_label is not None and false_label is not None:
                    self.instructions.append(
                        IRJump(
                            target=false_label,
                            cond="strictEqual",
                            a=left_val,
                            b=right_val,
                            loc=loc,
                        )
                    )
                    self.instructions.append(
                        IRJump(
                            target=true_label,
                            cond="always",
                            a="0",
                            b="0",
                            loc=loc,
                        )
                    )
                return

            if cmp_cls is ast.Is:
                # 'left is right' is TRUE when left === right, and FALSE when left !== right.
                if true_label is not None and false_label is None:
                    # Jump to true_label when condition is TRUE (i.e. left === right).
                    self.instructions.append(
                        IRJump(
                            target=true_label,
                            cond="strictEqual",
                            a=left_val,
                            b=right_val,
                            loc=loc,
                        )
                    )
                elif false_label is not None and true_label is None:
                    # Jump to false_label when condition is FALSE (i.e. left !== right).
                    # Mindustry lacks strictNotEqual condition. Invert via skip jump:
                    # If left === right, skip the jump to false_label!
                    skip_lbl = self.new_label("is_skip")
                    self.instructions.append(
                        IRJump(
                            target=skip_lbl,
                            cond="strictEqual",
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
                    self.instructions.append(IRLabel(name=skip_lbl, loc=loc))
                elif true_label is not None and false_label is not None:
                    self.instructions.append(
                        IRJump(
                            target=true_label,
                            cond="strictEqual",
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
        elif isinstance(stmt, ast.AugAssign):
            self.compile_aug_assign(stmt)
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
            if (isinstance(stmt.value, ast.Constant) and stmt.value.value is Ellipsis) or (
                hasattr(ast, "Ellipsis") and isinstance(stmt.value, ast.Ellipsis)
            ):
                pass
            else:
                if isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name) and stmt.value.func.id == "Array":
                    self.error("Array declaration must be assigned to a variable, e.g. 'a = Array(...)'", stmt)
                self.compile_expr(stmt.value, is_statement=True)
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
        if self.fold_constants:
            tree = fold_constants(tree, self.filename)

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
    fold_constants: bool = True,
) -> List[IRNode]:
    """Parse, validate, and compile Python source code into IR."""
    tree = parse_and_validate(source, filename, allow_functions=allow_functions)
    compiler = Compiler(filename, allow_functions=allow_functions, fold_constants=fold_constants)
    return compiler.compile(tree)

