"""Structured Control Flow Intermediate Representation (IR).

Represents recovered structured program constructs (If, While, Break, Continue, Pass,
Instruction, Unstructured) independent of high-level expression synthesis or variable analysis.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

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
    "strictEqual": "==",
}

CMP_INVERSE_TO_PY = {
    "equal": "!=",
    "notEqual": "==",
    "lessThan": ">=",
    "lessThanEq": ">",
    "greaterThan": "<=",
    "greaterThanEq": "<",
    "strictEqual": "!=",
}


def is_float(s: str) -> bool:
    try:
        float(s)
        return "." in s or "e" in s.lower()
    except ValueError:
        return False


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


def instruction_to_python(
    instr: MlogInstruction,
    defined_variables: Optional[Set[str]] = None,
) -> str:
    """Convert an MlogInstruction into a Python DSL statement string without expression synthesis."""
    op = instr.opcode
    args = instr.args

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


    if op == "stop":
        return "stop()"

    if op == "end":
        return "end()"

    if op == "wait":
        arg = format_operand(args[0]) if args else "0.5"
        return f"wait({arg})"

    # Format arguments using semantic roles from SSOT metadata
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
                args_repr = ", ".join(repr(a) for a in instr.args)
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
