"""Reserved-identifier normalization for decompiler output.

The compiler allocates scratch registers named ``__tmp0``, ``__tmp1``, ... and the
parser rejects those names in user source (``Compiler.format_name``). When the
expression optimizer cannot prove a temporary is safe to fold -- for example a
``read`` feeding a ``write`` inside a loop -- the decompiler must keep it as an
explicit assignment. Emitting the raw ``__tmpN`` name would then produce Python
that the compiler refuses to recompile, breaking the MLog -> Python -> MLog
round-trip.

This pass renames every surviving compiler temporary to a valid Mindustry Logic
DSL identifier. It is a pure 1:1 renaming:

* no assignment, use, or instruction operand is ever added, removed, or reordered;
* the mapping is built once from the whole program and applied to every occurrence,
  so all reads and writes of a temporary keep pointing at the same variable;
* names that are not compiler temporaries are never touched;
* temporaries that exist only as a discardable output slot of a multi-destination
  opcode are left alone, because ``instruction_to_python`` already elides them and
  the compiler regenerates the scratch register on its own.
"""

import ast
from typing import Dict, List, Optional, Set, Tuple

from .dataflow import substitute_variable
from .expression import Expr, VariableExpr
from .function_ir import CallNode, FunctionProgram, ReturnNode
from .instruction import MlogInstruction
from .semantics import (
    ArgumentSemanticRole,
    get_argument_semantic_role,
    is_safe_inline_expression,
)
from .structured_ir import (
    AssignNode,
    ExprStmtNode,
    IfNode,
    InstructionNode,
    UnstructuredNode,
    WhileNode,
    is_compiler_temporary,
)


# Prefix for decompiler-generated names. Deliberately outside every pattern
# is_compiler_temporary() matches, so a renamed temporary is never re-classified
# as a temporary by a later phase.
RENAMED_TEMPORARY_PREFIX = "tmp_val_"

# Multi-destination opcodes whose trailing outputs may be scratch registers that
# the Python renderer elides. This mirrors ``instruction_to_python`` exactly: the
# ulocate branch is the only place that consults is_compiler_temporary() to drop an
# operand. A temporary in one of these slots must keep its original name so the
# renderer can still drop it and the compiler regenerates the same scratch register.
_DISCARDABLE_OUTPUT_INDICES: Dict[str, Tuple[int, ...]] = {
    "ulocate": (4, 5, 6, 7),
}

_LITERAL_TOKENS = frozenset({"true", "false", "null"})


def _identifier_names_in_operand(text: str) -> List[str]:
    """Return identifier names referenced by an operand token, if it is a safe expression."""
    if text in _LITERAL_TOKENS:
        return []
    if text.isidentifier():
        return [text]
    if not is_safe_inline_expression(text):
        return []
    try:
        tree = ast.parse(text, mode="eval")
    except (SyntaxError, ValueError, MemoryError, RecursionError):
        return []
    return [n.id for n in ast.walk(tree) if isinstance(n, ast.Name)]


def _is_discardable_output_slot(opcode: str, arg_idx: int) -> bool:
    """True when the renderer may elide this destination operand for a temporary."""
    if arg_idx not in _DISCARDABLE_OUTPUT_INDICES.get(opcode, ()):
        return False
    return True


def _rename_identifiers(text: str, mapping: Dict[str, str]) -> str:
    """Rename identifiers inside a pure arithmetic operand expression."""
    if not mapping or not is_safe_inline_expression(text):
        return text

    tree = ast.parse(text, mode="eval")
    changed = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in mapping:
            node.id = mapping[node.id]
            changed = True
    return ast.unparse(tree) if changed else text


class _TempScan:
    """Collects every identifier occurrence in a program, split by position class."""

    def __init__(self) -> None:
        self.mentions: List[str] = []
        self.reads: Set[str] = set()
        self.writes: Set[str] = set()
        # Names observed at least once outside an elidable output slot. A temporary
        # missing from this set is pure scratch sitting in a slot the renderer drops.
        self.non_discardable: Set[str] = set()

    def mention(self, name: str) -> None:
        self.mentions.append(name)

    def read(self, name: str) -> None:
        self.mention(name)
        self.reads.add(name)
        self.non_discardable.add(name)

    def write(self, name: str, *, discardable: bool = False) -> None:
        self.mention(name)
        self.writes.add(name)
        if not discardable:
            self.non_discardable.add(name)

    def visit_expr(self, expr: Optional[Expr]) -> None:
        if expr is None:
            return
        for name in sorted(expr.variables_used):
            self.read(name)

    def visit_instruction(self, instr: MlogInstruction) -> None:
        for idx, arg in enumerate(instr.args):
            discardable = _is_discardable_output_slot(instr.opcode, idx)
            role = get_argument_semantic_role(instr.opcode, idx, instr.args)
            if role is ArgumentSemanticRole.VARIABLE_DEF:
                self.write(arg, discardable=discardable)
                continue
            if discardable:
                # Elidable slot holding a read-position operand: never elided in practice,
                # but treat it as ordinary so the name still gets normalized.
                pass
            for name in _identifier_names_in_operand(arg):
                self.read(name)

    def visit_nodes(self, nodes: List) -> None:
        for node in nodes:
            if isinstance(node, AssignNode):
                self.write(node.target)
                self.visit_expr(node.value)
            elif isinstance(node, ExprStmtNode):
                self.visit_expr(node.expr)
            elif isinstance(node, InstructionNode):
                self.visit_instruction(node.instruction)
            elif isinstance(node, UnstructuredNode):
                for instr in node.instructions:
                    self.visit_instruction(instr)
            elif isinstance(node, IfNode):
                self.visit_expr(node.condition_expr)
                self.visit_nodes(node.then_body)
                self.visit_nodes(node.else_body)
            elif isinstance(node, WhileNode):
                self.visit_expr(node.condition_expr)
                self.visit_nodes(node.body)
            elif isinstance(node, ReturnNode):
                self.visit_expr(node.value)
            elif isinstance(node, CallNode):
                if node.target is not None:
                    self.write(node.target)
                for arg in node.args:
                    self.visit_expr(arg)


def _scan_program(program: FunctionProgram) -> _TempScan:
    scan = _TempScan()
    for func in program.functions:
        for name in func.param_names:
            scan.write(name)
        if func.return_var:
            scan.write(func.return_var)
        if func.retval_var:
            scan.write(func.retval_var)
        scan.visit_nodes(func.body)
    scan.visit_nodes(program.global_statements)
    return scan


def _build_mapping(scan: _TempScan, existing: Set[str]) -> Dict[str, str]:
    """Build a deterministic temp -> valid-name mapping in first-appearance order.

    Temporaries that appear *only* in elidable output slots keep their original name
    so the renderer still drops them; every other temporary is normalized.
    """
    slotted_only = {n for n in scan.mentions if n not in scan.non_discardable}

    mapping: Dict[str, str] = {}
    used: Set[str] = set()
    counter = 0
    for name in scan.mentions:
        if not is_compiler_temporary(name) or name in mapping:
            continue
        if name in slotted_only:
            continue
        while True:
            candidate = f"{RENAMED_TEMPORARY_PREFIX}{counter}"
            counter += 1
            if candidate not in existing and candidate not in used:
                break
        mapping[name] = candidate
        used.add(candidate)

    return mapping


class _TempRenamer:
    """Applies a temp -> valid-name mapping across a structured program tree."""

    def __init__(self, mapping: Dict[str, str]) -> None:
        self.mapping = mapping

    def _rename_expr(self, expr: Optional[Expr]) -> Optional[Expr]:
        if expr is None or not self.mapping:
            return expr
        for old, new in self.mapping.items():
            if old in expr.variables_used:
                expr = substitute_variable(expr, old, VariableExpr(new))
        return expr

    def _rename_target(self, name: Optional[str]) -> Optional[str]:
        if name is None:
            return None
        return self.mapping.get(name, name)

    def _rename_operand(self, opcode: str, arg: str, arg_idx: int) -> str:
        if arg in self.mapping:
            if _is_discardable_output_slot(opcode, arg_idx):
                return arg
            return self.mapping[arg]
        return _rename_identifiers(arg, self.mapping)

    def _rewrite_instruction(self, instr: MlogInstruction) -> MlogInstruction:
        new_args = tuple(
            self._rename_operand(instr.opcode, arg, idx)
            for idx, arg in enumerate(instr.args)
        )
        if new_args == instr.args:
            return instr
        return MlogInstruction(
            address=instr.address,
            opcode=instr.opcode,
            args=new_args,
            loc=instr.loc,
            raw_text=instr.raw_text,
        )

    def visit_nodes(self, nodes: List) -> None:
        for node in nodes:
            if isinstance(node, AssignNode):
                node.target = self._rename_target(node.target)
                node.value = self._rename_expr(node.value)
            elif isinstance(node, ExprStmtNode):
                node.expr = self._rename_expr(node.expr)
            elif isinstance(node, InstructionNode):
                node.instruction = self._rewrite_instruction(node.instruction)
            elif isinstance(node, UnstructuredNode):
                node.instructions = [
                    self._rewrite_instruction(i) for i in node.instructions
                ]
            elif isinstance(node, IfNode):
                node.condition_expr = self._rename_expr(node.condition_expr)
                self.visit_nodes(node.then_body)
                self.visit_nodes(node.else_body)
            elif isinstance(node, WhileNode):
                node.condition_expr = self._rename_expr(node.condition_expr)
                self.visit_nodes(node.body)
            elif isinstance(node, ReturnNode):
                node.value = self._rename_expr(node.value)
            elif isinstance(node, CallNode):
                node.target = self._rename_target(node.target)
                node.args = [self._rename_expr(a) for a in node.args]

    def visit_program(self, program: FunctionProgram) -> None:
        for func in program.functions:
            func.return_var = self._rename_target(func.return_var)
            func.retval_var = self._rename_target(func.retval_var)
            self.visit_nodes(func.body)
        self.visit_nodes(program.global_statements)


def rename_reserved_temporaries(program: FunctionProgram) -> FunctionProgram:
    """Rename surviving compiler temporaries in ``program`` to valid DSL identifiers.

    Mutates and returns the program in place. Programs without surviving
    temporaries are left untouched.
    """
    scan = _scan_program(program)
    existing = {name for name in scan.mentions if not is_compiler_temporary(name)}
    existing.update(f.name for f in program.functions)

    mapping = _build_mapping(scan, existing)
    if not mapping:
        return program

    _TempRenamer(mapping).visit_program(program)
    return program