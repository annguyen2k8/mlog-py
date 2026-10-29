"""Python AST parser and validator for the controlled Mindustry Logic subset."""

import ast
from typing import Set, Union

from .errors import CompileError, SourceLocation
from .metadata import ALLOWED_INTRINSICS, MLOG_EXPORTS


# Mapping of ast node types to human-readable names for error reporting
UNSUPPORTED_NAMES = {
    ast.FunctionDef: "function definition",
    ast.AsyncFunctionDef: "async function definition",
    ast.ClassDef: "class definition",
    ast.Return: "return statement",
    ast.Delete: "del statement",
    ast.AnnAssign: "annotated assignment",
    ast.AsyncFor: "async for loop",
    ast.With: "with statement",
    ast.AsyncWith: "async with statement",
    ast.Match: "match statement",
    ast.Raise: "raise statement",
    ast.Try: "try/except statement",
    ast.TryStar: "try/except* statement",
    ast.Assert: "assert statement",
    ast.Global: "global statement",
    ast.Nonlocal: "nonlocal statement",

    ast.Yield: "yield expression",
    ast.YieldFrom: "yield from expression",
    ast.Lambda: "lambda expression",
    ast.NamedExpr: "walrus operator (:=)",
    ast.Dict: "dict literal",
    ast.Set: "set literal",
    ast.List: "list literal",
    ast.Tuple: "tuple literal",
    ast.ListComp: "list comprehension",
    ast.SetComp: "set comprehension",
    ast.DictComp: "dict comprehension",
    ast.GeneratorExp: "generator expression",
    ast.Await: "await expression",
    ast.Starred: "starred expression (*args)",
    ast.Slice: "slice",
}


def get_loc(node: ast.AST, filename: str) -> SourceLocation:
    """Extract SourceLocation from an AST node."""
    line = getattr(node, "lineno", 1)
    col = getattr(node, "col_offset", 0) + 1
    end_line = getattr(node, "end_lineno", None)
    end_col = getattr(node, "end_col_offset", None)
    if end_col is not None:
        end_col += 1
    return SourceLocation(
        filename=filename,
        line=line,
        col=col,
        end_line=end_line,
        end_col=end_col,
    )


class ASTValidator(ast.NodeVisitor):
    """Validates that a Python AST contains only the allowed subset for mlog."""

    def __init__(self, filename: str, allow_functions: bool = False):
        self.filename = filename
        self.allow_functions = allow_functions
        self.defined_functions: Set[str] = set()
        from .constants import NamedConstantRegistry
        self.constant_registry = NamedConstantRegistry()
        self._module_classes: Set[ast.ClassDef] = set()

    def error(self, msg: str, node: ast.AST):
        loc = get_loc(node, self.filename)
        raise CompileError(msg, loc)

    def visit_Module(self, node: ast.Module):
        from .constants import extract_int_enums
        for stmt in node.body:
            if isinstance(stmt, ast.ClassDef):
                self._module_classes.add(stmt)
        extract_int_enums(node, self.filename, registry=self.constant_registry)
        if self.allow_functions:
            for stmt in node.body:
                if isinstance(stmt, ast.FunctionDef):
                    self.defined_functions.add(stmt.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        if node not in self._module_classes:
            self.error("IntEnum class definitions are only allowed at module level", node)
        # ClassDef has already been validated and registered by extract_int_enums at module level

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if not self.allow_functions:
            self.error("unsupported Python feature: function definition", node)
        self.defined_functions.add(node.name)
        if node.args.vararg is not None:
            self.error("*args is not supported in function definitions", node)
        if node.args.kwarg is not None:
            self.error("**kwargs is not supported in function definitions", node)
        if node.args.defaults or node.args.kw_defaults:
            self.error("default argument values are not supported", node)
        if node.args.posonlyargs or node.args.kwonlyargs:
            self.error("positional-only/keyword-only arguments are not supported", node)
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return):
        if not self.allow_functions:
            self.error("unsupported Python feature: return statement", node)
        self.generic_visit(node)

    def generic_visit(self, node: ast.AST):
        # Check against explicitly known unsupported nodes
        node_type = type(node)
        if node_type in UNSUPPORTED_NAMES:
            if self.allow_functions and node_type in (ast.FunctionDef, ast.Return):
                pass
            elif node_type is ast.ClassDef:
                pass
            else:
                name = UNSUPPORTED_NAMES[node_type]
                self.error(f"unsupported Python feature: {name}", node)

        # Disallow any node that is not in the whitelist
        allowed_nodes = (
            ast.Module,
            ast.Assign,
            ast.AugAssign,
            ast.Expr,
            ast.If,
            ast.While,
            ast.For,
            ast.Break,
            ast.Continue,
            ast.Pass,
            ast.Import,
            ast.ImportFrom,
            ast.alias,
            ast.ClassDef,
            # Expressions
            ast.Constant,
            ast.Name,
            ast.BinOp,
            ast.UnaryOp,
            ast.Compare,
            ast.BoolOp,
            ast.Call,
            ast.Attribute,
            ast.Subscript,
            ast.IfExp,
            ast.JoinedStr,
            ast.FormattedValue,
            # Operators
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,
            ast.Pow, ast.LShift, ast.RShift, ast.BitOr, ast.BitAnd, ast.BitXor,
            ast.USub, ast.UAdd, ast.Invert, ast.Not,
            ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
            ast.Is, ast.IsNot,
            ast.And, ast.Or,
            # Contexts
            ast.Load, ast.Store,
        )
        if self.allow_functions:
            allowed_nodes = allowed_nodes + (ast.FunctionDef, ast.Return, ast.arguments, ast.arg)

        if not isinstance(node, allowed_nodes):
            self.error(
                f"unsupported Python feature: {node_type.__name__}", node
            )

        super().generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            if alias.name == "enum":
                if alias.asname is not None and alias.asname != alias.name:
                    self.error(f"import aliasing ('as {alias.asname}') is not supported", node)
                continue
            if alias.name not in ("mlog", "src.mlog", "mlog_registry", "src.mlog_registry"):
                self.error("unsupported Python feature: import statement", node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module == "enum":
            for alias in node.names:
                if alias.name not in ("IntEnum", "*"):
                    self.error(f"cannot import name '{alias.name}' from 'enum': only 'IntEnum' is supported in MVP", node)
                if alias.asname is not None and alias.asname != alias.name:
                    self.error(f"import aliasing ('as {alias.asname}') is not supported", node)
            return

        if node.module not in ("mlog", "src.mlog", "mlog_registry", "src.mlog_registry"):
            self.error("unsupported Python feature: from ... import statement", node)

        for alias in node.names:
            if alias.name == "*":
                continue
            if alias.asname is not None and alias.asname != alias.name:
                self.error(f"import aliasing ('as {alias.asname}') is not supported", node)
            if node.module in ("mlog", "src.mlog"):
                if alias.name not in MLOG_EXPORTS:
                    self.error(f"cannot import name '{alias.name}' from '{node.module}'", node)
            elif node.module in ("mlog_registry", "src.mlog_registry"):
                from .mlog_registry import ENUM_CLASS_TO_REGISTRY
                if alias.name not in ENUM_CLASS_TO_REGISTRY and not alias.name.startswith("REG_"):
                    self.error(f"cannot import name '{alias.name}' from '{node.module}'", node)

    def visit_Attribute(self, node: ast.Attribute):
        from .mlog_registry import ENUM_CLASS_TO_REGISTRY, BUILTIN_VARIABLES_DATA
        if isinstance(node.value, ast.Name):
            if node.value.id == "Vars":
                if node.attr not in BUILTIN_VARIABLES_DATA:
                    self.error(f"unknown Mindustry built-in variable: 'Vars.{node.attr}'", node)
                return
            if node.value.id == "draw":
                DRAW_METHODS = {
                    "clear", "color", "col", "stroke", "line", "rect",
                    "line_rect", "lineRect", "poly", "line_poly", "linePoly",
                    "triangle", "image", "print", "translate", "scale", "rotate", "reset", "flush",
                }
                if node.attr not in DRAW_METHODS:
                    self.error(f"unknown draw method: 'draw.{node.attr}'", node)
                return
            if node.value.id == "control":
                CONTROL_METHODS = {"enabled", "shoot", "shootp", "config", "color"}
                if node.attr not in CONTROL_METHODS:
                    self.error(f"unknown control method: 'control.{node.attr}'", node)
                return
            if node.value.id == "ucontrol":
                UCONTROL_METHODS = {
                    "idle", "stop", "move", "approach", "pathfind", "auto_pathfind", "autoPathfind",
                    "boost", "target", "targetp", "item_drop", "itemDrop", "item_take", "itemTake",
                    "pay_drop", "payDrop", "pay_take", "payTake", "pay_enter", "payEnter",
                    "mine", "flag", "build", "deconstruct", "get_block", "getBlock", "within", "unbind",
                }
                if node.attr not in UCONTROL_METHODS:
                    self.error(f"unknown ucontrol method: '{node.value.id}.{node.attr}'", node)
                return
            if node.value.id == "ulocate":
                ULOCATE_METHODS = {"ore", "building", "spawn", "damaged"}
                if node.attr not in ULOCATE_METHODS:
                    self.error(f"unknown ulocate method: '{node.value.id}.{node.attr}'", node)
                return
            if node.value.id == "op":
                OP_METHODS = {
                    "abs", "sign", "log", "log10", "log_10", "floor", "ceil",
                    "round", "sqrt", "rand", "sin", "cos", "tan", "asin", "acos", "atan",
                    "add", "sub", "mul", "div", "idiv", "mod", "emod", "pow",
                    "equal", "not_equal", "notEqual", "land", "less_than", "lessThan",
                    "less_than_eq", "lessThanEq", "greater_than", "greaterThan",
                    "greater_than_eq", "greaterThanEq", "strict_equal", "strictEqual",
                    "shl", "shr", "ushr", "xor",
                    "max", "min", "angle", "angle_diff", "angleDiff", "len", "length",
                    "noise", "logn",
                }
                if node.attr not in OP_METHODS:
                    self.error(f"unknown op method: 'op.{node.attr}'", node)
                return
            if node.value.id == "cutscene":
                CUTSCENE_METHODS = {
                    "active", "pan", "zoom", "stop", "shake", "get_hud", "getHud", "set_hud", "setHud",
                }
                if node.attr not in CUTSCENE_METHODS:
                    self.error(f"unknown cutscene method: 'cutscene.{node.attr}'", node)
                return
            if node.value.id == "sound":
                SOUND_METHODS = {"play", "play_at", "playAt"}
                if node.attr not in SOUND_METHODS:
                    self.error(f"unknown sound method: 'sound.{node.attr}'", node)
                return
            if node.value.id == "music":
                MUSIC_METHODS = {"play", "stop"}
                if node.attr not in MUSIC_METHODS:
                    self.error(f"unknown music method: 'music.{node.attr}'", node)
                return
            if node.value.id == "marker":
                MARKER_METHODS = {
                    "make", "remove", "world", "minimap", "light", "autoscale",
                    "pos", "end_pos", "endPos", "draw_layer", "drawLayer", "color",
                    "radius", "stroke", "outline", "rotation", "shape", "arc",
                    "flush_text", "flushText", "font_size", "fontSize",
                    "text_height", "textHeight", "text_align", "textAlign",
                    "line_align", "lineAlign", "label_flags", "labelFlags",
                    "texture", "texture_size", "textureSize", "posi", "uvi", "colori",
                }
                if node.attr not in MARKER_METHODS:
                    self.error(f"unknown marker method: 'marker.{node.attr}'", node)
                return
            if node.value.id in ENUM_CLASS_TO_REGISTRY:
                return
            if self.constant_registry.has_namespace(node.value.id):
                if not self.constant_registry.has_member(node.value.id, node.attr):
                    self.error(f"enum '{node.value.id}' has no member '{node.attr}'", node)
                return
        self.error(
            f"attribute access is only supported on DSL enum types ({', '.join(sorted(ENUM_CLASS_TO_REGISTRY.keys()))}), user-defined IntEnums, 'Vars', 'draw', 'control', 'ucontrol', 'ulocate', 'cutscene', 'sound', 'music', 'marker', and 'op'",
            node,
        )

    def visit_Name(self, node: ast.Name):
        if self.constant_registry.has_namespace(node.id):
            self.error(f"enum '{node.id}' cannot be used as a standalone value", node)
        self.generic_visit(node)

    def _check_single_target_ulocate_call(self, node: ast.Assign, target: ast.Name) -> None:
        call = node.value
        if not isinstance(call, ast.Call):
            return
        if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) and call.func.value.id == "ulocate":
            m = call.func.attr
            if m == "building" and len(call.args) == 2:
                self.error("ulocate.building produces 4 outputs and must be unpacked into a tuple: core_x, core_y, found, building = ulocate.building(group, enemy)", node)
            elif m == "ore" and len(call.args) == 1:
                self.error("ulocate.ore produces 3 outputs and must be unpacked into a tuple: ore_x, ore_y, found = ulocate.ore(ore)", node)
            elif m == "spawn" and len(call.args) == 0:
                self.error("ulocate.spawn produces 4 outputs and must be unpacked into a tuple: spawn_x, spawn_y, found, building = ulocate.spawn()", node)
            elif m == "damaged" and len(call.args) == 0:
                self.error("ulocate.damaged produces 4 outputs and must be unpacked into a tuple: dmg_x, dmg_y, found, building = ulocate.damaged()", node)

    def _validate_unpacking_assign(self, node: ast.Assign, target: Union[ast.Tuple, ast.List]) -> None:
        if not target.elts:
            self.error("cannot unpack into an empty tuple", target)
        seen_names = set()
        for elt in target.elts:
            if not isinstance(elt, ast.Name):
                self.error("unpacking target elements must be simple variable names", elt)
            if elt.id == "Vars":
                self.error("cannot unpack into 'Vars'", elt)
            if elt.id in seen_names:
                self.error(f"duplicate variable name '{elt.id}' in tuple unpacking targets", elt)
            seen_names.add(elt.id)

        call = node.value
        if not isinstance(call, ast.Call):
            self.error("assignment target must be a simple variable name: tuple unpacking is only supported for 'ulocate' operations (e.g., core_x, core_y, found, building = ulocate.building(...)) and 'unpackcolor' (e.g., r, g, b, a = unpackcolor(color))", node.value)

        is_ulocate_method = (
            isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id == "ulocate"
        )
        is_ulocate_call = (
            isinstance(call.func, ast.Name)
            and call.func.id == "ulocate"
        )
        is_unpackcolor_call = (
            isinstance(call.func, ast.Name)
            and call.func.id == "unpackcolor"
        )

        if is_unpackcolor_call:
            if call.keywords:
                self.error("unpackcolor does not support keyword arguments", call)
            if len(call.args) != 1:
                self.error(
                    f"invalid arguments for unpackcolor unpacking: expected unpackcolor(value), got {len(call.args)} arguments",
                    call,
                )
            target_count = len(target.elts)
            if target_count != 4:
                self.error(
                    f"unpackcolor unpacking expects exactly 4 target variables (out_r, out_g, out_b, out_a), got {target_count}",
                    target,
                )
            return

        if not (is_ulocate_method or is_ulocate_call):
            self.error("assignment target must be a simple variable name: tuple unpacking is only supported for 'ulocate' operations (e.g., core_x, core_y, found, building = ulocate.building(...)) and 'unpackcolor' (e.g., r, g, b, a = unpackcolor(color))", node.value)

        target_count = len(target.elts)
        if is_ulocate_method:
            method_name = call.func.attr
            if method_name == "building":
                if len(call.args) != 2 or call.keywords:
                    self.error("invalid arguments for ulocate.building unpacking: expected ulocate.building(group, enemy)", call)
                if target_count not in (3, 4):
                    self.error(f"ulocate.building unpacking expects 3 or 4 target variables (out_x, out_y, out_found[, out_building]), got {target_count}", target)
            elif method_name == "ore":
                if len(call.args) != 1 or call.keywords:
                    self.error("invalid arguments for ulocate.ore unpacking: expected ulocate.ore(ore)", call)
                if target_count not in (3, 4):
                    self.error(f"ulocate.ore unpacking expects 3 or 4 target variables (out_x, out_y, out_found[, out_building]), got {target_count}", target)
            elif method_name == "spawn":
                if len(call.args) != 0 or call.keywords:
                    self.error("invalid arguments for ulocate.spawn unpacking: expected ulocate.spawn()", call)
                if target_count not in (3, 4):
                    self.error(f"ulocate.spawn unpacking expects 3 or 4 target variables (out_x, out_y, out_found[, out_building]), got {target_count}", target)
            elif method_name == "damaged":
                if len(call.args) != 0 or call.keywords:
                    self.error("invalid arguments for ulocate.damaged unpacking: expected ulocate.damaged()", call)
                if target_count not in (3, 4):
                    self.error(f"ulocate.damaged unpacking expects 3 or 4 target variables (out_x, out_y, out_found[, out_building]), got {target_count}", target)
            else:
                self.error(f"unknown ulocate method: 'ulocate.{method_name}'", call)

    def visit_Assign(self, node: ast.Assign):
        if len(node.targets) != 1:
            self.error("multiple/chained assignment targets are not supported", node)
        target = node.targets[0]
        if isinstance(target, ast.Subscript):
            self.visit_Subscript(target)
        elif isinstance(target, ast.Name):
            self._check_single_target_ulocate_call(node, target)
        elif isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "Vars":
            from .mlog_registry import BUILTIN_VARIABLES_DATA
            token = BUILTIN_VARIABLES_DATA.get(target.attr)
            if token is None:
                self.error(f"unknown Mindustry built-in variable: 'Vars.{target.attr}'", target)
            if token.readonly:
                self.error(f"cannot assign to read-only built-in variable 'Vars.{target.attr}' ('{token.token}')", target)
        elif isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and self.constant_registry.has_namespace(target.value.id):
            self.error(f"cannot assign to enum member '{target.value.id}.{target.attr}'", target)
        elif isinstance(target, (ast.Tuple, ast.List)):
            self._validate_unpacking_assign(node, target)
        else:
            self.error("assignment target must be a simple variable name, array index, or ulocate unpacking tuple", target)
        if isinstance(node.value, ast.JoinedStr):
            self.error("f-strings cannot be assigned to variables (Mindustry Logic only supports string formatting via the print buffer)", node.value)
        self.visit(node.value)

    def visit_AugAssign(self, node: ast.AugAssign):
        if isinstance(node.target, ast.Subscript):
            self.visit_Subscript(node.target)
        elif isinstance(node.target, ast.Name):
            pass
        elif isinstance(node.target, ast.Attribute) and isinstance(node.target.value, ast.Name) and node.target.value.id == "Vars":
            from .mlog_registry import BUILTIN_VARIABLES_DATA
            token = BUILTIN_VARIABLES_DATA.get(node.target.attr)
            if token is None:
                self.error(f"unknown Mindustry built-in variable: 'Vars.{node.target.attr}'", node.target)
            if token.readonly:
                self.error(f"cannot assign to read-only built-in variable 'Vars.{node.target.attr}' ('{token.token}')", node.target)
        elif isinstance(node.target, ast.Attribute) and isinstance(node.target.value, ast.Name) and self.constant_registry.has_namespace(node.target.value.id):
            self.error(f"cannot assign to enum member '{node.target.value.id}.{node.target.attr}'", node.target)
        else:
            self.error(
                "augmented assignment target must be a simple variable name or array index (unpacking not supported)",
                node.target,
            )
        op_cls = type(node.op)
        if op_cls not in (
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,
            ast.Pow, ast.LShift, ast.RShift, ast.BitOr, ast.BitAnd, ast.BitXor,
        ):
            op_name = "@=" if op_cls is ast.MatMult else f"{op_cls.__name__}="
            self.error(f"unsupported augmented assignment operator: '{op_name}'", node)
        if isinstance(node.value, ast.JoinedStr):
            self.error("f-strings cannot be assigned to variables (Mindustry Logic only supports string formatting via the print buffer)", node.value)
        self.visit(node.value)

    def visit_Subscript(self, node: ast.Subscript):
        if not isinstance(node.value, ast.Name):
            self.error("subscript indexing is only supported on simple array names (e.g. a[i])", node)
        if isinstance(node.slice, ast.Slice):
            self.error("slicing is not supported on arrays", node)
        self.visit(node.slice)

    def visit_For(self, node: ast.For):
        if not isinstance(node.target, ast.Name):
            self.error("for loop target must be a simple variable name", node.target)
        if not isinstance(node.iter, ast.Call) or not isinstance(node.iter.func, ast.Name) or node.iter.func.id != "range":
            self.error("for loop only supports 'range(...)' as iterator", node.iter)
        if len(node.iter.args) not in (1, 2, 3):
            self.error("range() expects 1 to 3 arguments in for loop", node.iter)
        if node.iter.keywords:
            self.error("range() does not support keyword arguments", node.iter)
        for arg in node.iter.args:
            self.visit(arg)
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)

    def visit_Call(self, node: ast.Call):
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in ("draw", "control", "ucontrol", "ulocate", "op", "cutscene", "sound", "music", "marker")
        ):
            self.visit(node.func)
            for arg in node.args:
                if isinstance(arg, ast.JoinedStr):
                    self.error(f"f-strings are not supported in '{node.func.value.id}.{node.func.attr}()'; use print(f\"...\") instead", arg)
                self.visit(arg)
            for kw in node.keywords:
                if isinstance(kw.value, ast.JoinedStr):
                    self.error(f"f-strings are not supported in '{node.func.value.id}.{node.func.attr}()'; use print(f\"...\") instead", kw.value)
                self.visit(kw.value)
            return

        if not isinstance(node.func, ast.Name):
            self.error("only compiler intrinsic calls are supported", node)
        func_name = node.func.id
        if func_name == "Array":
            for kw in node.keywords:
                if kw.arg not in ("size", "block", "dtype"):
                    self.error(f"unexpected keyword argument '{kw.arg}' in Array()", kw)
            for arg in node.args:
                self.visit(arg)
            for kw in node.keywords:
                self.visit(kw.value)
            return
        if func_name == "len":
            if len(node.args) != 1 or node.keywords:
                self.error("len() expects exactly 1 argument and no keyword arguments", node)
            self.visit(node.args[0])
            return
        if func_name not in ALLOWED_INTRINSICS:
            if self.allow_functions and func_name in self.defined_functions:
                pass
            else:
                self.error(
                    f"unsupported function call: '{func_name}'. "
                    f"Allowed intrinsics: {', '.join(sorted(ALLOWED_INTRINSICS))}",
                    node,
                )
        if node.keywords:
            self.error("keyword arguments are not supported in intrinsics", node)
        if func_name != "print":
            for arg in node.args:
                if isinstance(arg, ast.JoinedStr):
                    self.error(f"f-strings are not supported in '{func_name}()'; use print(f\"...\") instead", arg)
        for arg in node.args:
            self.visit(arg)

    def visit_Expr(self, node: ast.Expr):
        if isinstance(node.value, ast.JoinedStr):
            self.error("f-strings cannot be used as standalone statements; use print(f\"...\") instead", node.value)
        if isinstance(node.value, ast.Constant) and node.value.value is Ellipsis:
            # Standalone placeholder statement '...' is allowed
            return
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant):
        if node.value is Ellipsis:
            self.error(
                "Ellipsis (...) is only supported as a placeholder statement, not as an expression value",
                node,
            )
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp):
        if isinstance(node.left, ast.JoinedStr) or isinstance(node.right, ast.JoinedStr):
            self.error("f-strings do not support binary operations (Mindustry Logic only supports string formatting via the print buffer)", node)
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare):
        if isinstance(node.left, ast.JoinedStr) or any(isinstance(c, ast.JoinedStr) for c in node.comparators):
            self.error("f-strings cannot be compared (Mindustry Logic only supports string formatting via the print buffer)", node)
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return):
        if node.value is not None and isinstance(node.value, ast.JoinedStr):
            self.error("f-strings cannot be returned from functions (Mindustry Logic only supports string formatting via the print buffer)", node.value)
        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr):
        import re
        formatted_count = sum(1 for v in node.values if isinstance(v, ast.FormattedValue))
        if formatted_count > 10:
            self.error(
                "f-string supports at most 10 expressions (Mindustry format opcode supports placeholders {0} through {9})",
                node,
            )
        if formatted_count > 0:
            for part in node.values:
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    if re.search(r'\{[0-9]\}', part.value):
                        self.error(
                            "literal '{...}' matching placeholder syntax '{0}'-'{9}' is not supported inside f-strings in Mindustry Logic",
                            part,
                        )
        for v in node.values:
            self.visit(v)

    def visit_FormattedValue(self, node: ast.FormattedValue):
        if node.format_spec is not None:
            self.error(
                "f-string format specifiers (e.g. ':.2f') are not supported in Mindustry Logic",
                node,
            )
        if node.conversion != -1:
            self.error(
                "f-string conversions (!s, !r, !a) are not supported in Mindustry Logic",
                node,
            )
        self.visit(node.value)


def parse_and_validate(
    source: str,
    filename: str = "<stdin>",
    allow_functions: bool = False,
) -> ast.Module:
    """Parse Python source code and validate that it conforms to the mlog subset."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as e:
        loc = SourceLocation(
            filename=filename,
            line=e.lineno or 1,
            col=(e.offset or 0),
        )
        raise CompileError(f"syntax error: {e.msg}", loc)

    validator = ASTValidator(filename, allow_functions=allow_functions)
    validator.visit(tree)
    tree.constant_registry = validator.constant_registry
    return tree
