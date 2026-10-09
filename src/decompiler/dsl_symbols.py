"""DSL symbol detection and automatic import generation for Mindustry Logic decompiler.

Extracts all Mindustry Logic DSL symbols (intrinsics, enums, constants) actually used
in a decompiled program to produce self-contained Python DSL code with minimal imports.
SSOT: src.metadata.MLOG_EXPORTS and src.metadata.ALL_REGISTRY_ENUMS.
"""

import ast
from typing import Any, Iterable, Optional, Set

from src.metadata import ALL_REGISTRY_ENUMS, MLOG_EXPORTS


def _collect_expr_symbols(expr: Any, symbols: Set[str]) -> None:
    """Recursively collect DSL symbols from an Expression IR node."""
    if expr is None:
        return

    cls_name = expr.__class__.__name__

    if cls_name == "CallExpr":
        func = getattr(expr, "func", "")
        if func in MLOG_EXPORTS:
            symbols.add(func)
        for arg in getattr(expr, "args", []):
            _collect_expr_symbols(arg, symbols)

    elif cls_name == "BinaryExpr":
        _collect_expr_symbols(getattr(expr, "left", None), symbols)
        _collect_expr_symbols(getattr(expr, "right", None), symbols)

    elif cls_name == "UnaryExpr":
        _collect_expr_symbols(getattr(expr, "operand", None), symbols)

    elif cls_name == "VariableExpr":
        name = getattr(expr, "name", "")
        if name in ALL_REGISTRY_ENUMS or name in ("raw", "null"):
            symbols.add(name)

    elif cls_name == "UnknownExpr":
        raw = getattr(expr, "raw_text", "")
        if raw in MLOG_EXPORTS:
            symbols.add(raw)


def _collect_node_symbols(node: Any, symbols: Set[str]) -> None:
    """Collect DSL symbols from a StructuredNode or FunctionDef."""
    if node is None:
        return

    cls_name = node.__class__.__name__

    if cls_name == "AssignNode":
        target = getattr(node, "target", "")
        if not target.isidentifier() or target.startswith("@"):
            symbols.add("set")
        _collect_expr_symbols(getattr(node, "value", None), symbols)

    elif cls_name == "ExprStmtNode":
        _collect_expr_symbols(getattr(node, "expr", None), symbols)

    elif cls_name == "CallNode":
        func_name = getattr(node, "func_name", "")
        if func_name in MLOG_EXPORTS:
            symbols.add(func_name)
        for arg in getattr(node, "args", []):
            _collect_expr_symbols(arg, symbols)

    elif cls_name == "ReturnNode":
        _collect_expr_symbols(getattr(node, "value", None), symbols)

    elif cls_name == "IfNode":
        _collect_expr_symbols(getattr(node, "condition_expr", None), symbols)
        for child in getattr(node, "then_body", []):
            _collect_node_symbols(child, symbols)
        for child in getattr(node, "else_body", []):
            _collect_node_symbols(child, symbols)

    elif cls_name == "WhileNode":
        _collect_expr_symbols(getattr(node, "condition_expr", None), symbols)
        for child in getattr(node, "body", []):
            _collect_node_symbols(child, symbols)

    elif cls_name == "FunctionDef":
        for child in getattr(node, "body", []):
            _collect_node_symbols(child, symbols)

    elif cls_name == "InstructionNode":
        instr = getattr(node, "instruction", None)
        if instr is not None:
            op = getattr(instr, "opcode", "")
            args = getattr(instr, "args", ())
            if op == "set":
                if len(args) == 2:
                    dest = args[0]
                    if not (dest.isidentifier() and not dest.startswith("@")):
                        symbols.add("set")
                else:
                    symbols.add("set")
            elif op == "op":
                symbols.add("op")
            elif op == "stop":
                symbols.add("stop")
            elif op == "end":
                symbols.add("end")
            elif op == "wait":
                symbols.add("wait")
            elif op in MLOG_EXPORTS:
                symbols.add(op)

    elif cls_name == "UnstructuredNode":
        for instr in getattr(node, "instructions", []):
            if getattr(instr, "is_jump", False):
                symbols.add("jump")
            else:
                op = getattr(instr, "opcode", "")
                args = getattr(instr, "args", ())
                if op == "set":
                    if len(args) == 2:
                        dest = args[0]
                        if not (dest.isidentifier() and not dest.startswith("@")):
                            symbols.add("set")
                    else:
                        symbols.add("set")
                elif op == "op":
                    symbols.add("op")
                elif op == "stop":
                    symbols.add("stop")
                elif op == "end":
                    symbols.add("end")
                elif op == "wait":
                    symbols.add("wait")
                elif op in MLOG_EXPORTS:
                    symbols.add(op)


def collect_used_dsl_symbols(program: Any) -> Set[str]:
    """Collect all DSL symbols referenced in a StructuredProgram or FunctionProgram IR."""
    symbols: Set[str] = set()

    if hasattr(program, "functions"):
        for func in getattr(program, "functions", []):
            _collect_node_symbols(func, symbols)

    stmts = getattr(program, "global_statements", None)
    if stmts is None:
        stmts = getattr(program, "body", [])

    for stmt in stmts:
        _collect_node_symbols(stmt, symbols)

    return symbols


class _DSLSymbolASTVisitor(ast.NodeVisitor):
    def __init__(self):
        self.used_names: Set[str] = set()
        self.defined_names: Set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.defined_names.add(node.name)
        for arg in node.args.args:
            self.defined_names.add(arg.arg)
        if node.args.vararg:
            self.defined_names.add(node.args.vararg.arg)
        if node.args.kwarg:
            self.defined_names.add(node.args.kwarg.arg)
        for arg in node.args.kwonlyargs:
            self.defined_names.add(arg.arg)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            self.defined_names.add(node.id)
        elif isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)


def extract_dsl_symbols_from_ast(code: str) -> Set[str]:
    """Parse generated Python code and extract all free DSL symbols from AST."""
    try:
        tree = ast.parse(code)
    except Exception:
        return set()

    visitor = _DSLSymbolASTVisitor()
    visitor.visit(tree)
    free_names = (visitor.used_names - visitor.defined_names) & MLOG_EXPORTS
    return free_names


def get_required_dsl_imports(program: Any, rendered_body: Optional[str] = None) -> Set[str]:
    """Get complete, verified set of DSL symbols that need to be imported.

    Derives symbols from program IR and optionally verifies/augments via AST analysis
    of rendered Python body code.
    """
    symbols = collect_used_dsl_symbols(program)
    if rendered_body:
        ast_symbols = extract_dsl_symbols_from_ast(rendered_body)
        symbols.update(ast_symbols)
    return symbols


def format_import_header(symbols: Iterable[str]) -> str:
    """Format minimal canonical 'from mlog import ...' header string.

    Returns empty string if symbols is empty.
    """
    sorted_syms = sorted(set(symbols))
    if not sorted_syms:
        return ""
    return f"from mlog import {', '.join(sorted_syms)}"
