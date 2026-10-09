"""Python AST parser and validator for the controlled Mindustry Logic subset."""

import ast
from typing import Set

from .errors import CompileError, SourceLocation
from .metadata import ALLOWED_INTRINSICS, MLOG_EXPORTS


# Mapping of ast node types to human-readable names for error reporting
UNSUPPORTED_NAMES = {
    ast.FunctionDef: "function definition",
    ast.AsyncFunctionDef: "async function definition",
    ast.ClassDef: "class definition",
    ast.Return: "return statement",
    ast.Delete: "del statement",
    ast.AugAssign: "augmented assignment (e.g. +=)",
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
    ast.Subscript: "subscript indexing ([...])",
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

    def error(self, msg: str, node: ast.AST):
        loc = get_loc(node, self.filename)
        raise CompileError(msg, loc)

    def visit_Module(self, node: ast.Module):
        if self.allow_functions:
            for stmt in node.body:
                if isinstance(stmt, ast.FunctionDef):
                    self.defined_functions.add(stmt.name)
        self.generic_visit(node)

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
            else:
                name = UNSUPPORTED_NAMES[node_type]
                self.error(f"unsupported Python feature: {name}", node)

        # Disallow any node that is not in the whitelist
        allowed_nodes = (
            ast.Module,
            ast.Assign,
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
            # Expressions
            ast.Constant,
            ast.Name,
            ast.BinOp,
            ast.UnaryOp,
            ast.Compare,
            ast.BoolOp,
            ast.Call,
            ast.Attribute,
            # Operators
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,
            ast.Pow, ast.LShift, ast.RShift, ast.BitOr, ast.BitAnd, ast.BitXor,
            ast.USub, ast.UAdd, ast.Invert, ast.Not,
            ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
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
            if alias.name not in ("mlog", "src.mlog", "mlog_registry", "src.mlog_registry"):
                self.error("unsupported Python feature: import statement", node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
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
        from .mlog_registry import ENUM_CLASS_TO_REGISTRY
        if not isinstance(node.value, ast.Name) or node.value.id not in ENUM_CLASS_TO_REGISTRY:
            self.error(
                f"attribute access is only supported on DSL enum types ({', '.join(sorted(ENUM_CLASS_TO_REGISTRY.keys()))})",
                node,
            )

    def visit_Assign(self, node: ast.Assign):
        if len(node.targets) != 1:
            self.error("multiple/chained assignment targets are not supported", node)
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            self.error("assignment target must be a simple variable name (unpacking not supported)", target)
        self.visit(node.value)

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
        if not isinstance(node.func, ast.Name):
            self.error("only compiler intrinsic calls are supported", node)
        func_name = node.func.id
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
        for arg in node.args:
            self.visit(arg)


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
    return tree
