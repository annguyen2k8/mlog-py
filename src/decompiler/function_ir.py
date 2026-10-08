"""Function and Program-level Intermediate Representation (IR).

Represents functions (FunctionDef), call statements (CallNode), return statements (ReturnNode),
formal parameters (Parameter), return values (ReturnValue), and program-level collections
(FunctionProgram) for Phase 4 Function Recovery.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union

from .expression import Expr
from .structured_ir import StructuredNode, StructuredProgram


@dataclass
class Parameter:
    """Represents a formal function parameter."""
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass
class ReturnValue:
    """Represents a returned expression wrapper."""
    value: Optional[Expr] = None

    def to_python(self) -> str:
        return self.value.to_python() if self.value is not None else ""


@dataclass
class ReturnNode(StructuredNode):
    """Represents a 'return' statement in a function body."""
    value: Optional[Expr] = None
    source_addresses: List[int] = field(default_factory=list)

    def to_python(self, indent: int = 0) -> str:
        prefix = "    " * indent
        if self.value is not None:
            return f"{prefix}return {self.value.to_python()}"
        return f"{prefix}return"


@dataclass
class CallNode(StructuredNode):
    """Represents a function call statement: [target = ] func(arg1, arg2, ...)."""
    func_name: str
    args: List[Expr] = field(default_factory=list)
    target: Optional[str] = None
    source_addresses: List[int] = field(default_factory=list)

    def to_python(self, indent: int = 0) -> str:
        prefix = "    " * indent
        args_str = ", ".join(a.to_python() for a in self.args)
        if self.target is not None:
            return f"{prefix}{self.target} = {self.func_name}({args_str})"
        return f"{prefix}{self.func_name}({args_str})"


@dataclass
class FunctionDef(StructuredNode):
    """Represents a recovered function definition: def name(params): ..."""
    name: str
    parameters: List[Union[str, Parameter]] = field(default_factory=list)
    body: List[StructuredNode] = field(default_factory=list)
    return_var: Optional[str] = None
    retval_var: Optional[str] = None
    entry_address: int = 0
    source_addresses: List[int] = field(default_factory=list)

    @property
    def param_names(self) -> List[str]:
        return [p.name if isinstance(p, Parameter) else str(p) for p in self.parameters]

    def to_python(self, indent: int = 0) -> str:
        prefix = "    " * indent
        params_str = ", ".join(self.param_names)
        lines = [f"{prefix}def {self.name}({params_str}):"]

        if not self.body:
            lines.append(f"{prefix}    pass")
        else:
            for node in self.body:
                lines.append(node.to_python(indent + 1))

        return "\n".join(lines)


@dataclass
class FunctionProgram(StructuredProgram):
    """Represents the complete program containing recovered functions and global statements."""
    functions: List[FunctionDef] = field(default_factory=list)
    global_statements: List[StructuredNode] = field(default_factory=list)
    is_fully_structured: bool = True
    unstructured_reasons: List[str] = field(default_factory=list)
    instruction_by_address: Dict[int, MlogInstruction] = field(default_factory=dict)

    @property
    def body(self) -> List[StructuredNode]:
        """Return combined functions and global statements for StructuredProgram compatibility."""
        return list(self.functions) + list(self.global_statements)

    @body.setter
    def body(self, value: List[StructuredNode]):
        self.global_statements = list(value)

    def to_python(self, debug: bool = False) -> str:
        """Render the complete program with functions followed by top-level statements."""
        if debug:
            from .sourcemap import SourceMapEmitter
            code, _ = SourceMapEmitter(self.instruction_by_address, debug=True).emit_program(self)
            return code

        from .dsl_symbols import format_import_header, get_required_dsl_imports

        chunks: List[str] = []

        # Render functions separated by double newlines
        for func in self.functions:
            chunks.append(func.to_python(0))

        # Render top-level global statements
        global_lines: List[str] = []
        for stmt in self.global_statements:
            global_lines.append(stmt.to_python(0))

        if global_lines:
            chunks.append("\n".join(global_lines))

        if not chunks:
            return "pass\n"

        body = "\n\n".join(chunks)

        symbols = get_required_dsl_imports(self, rendered_body=body)
        header = format_import_header(symbols)
        if header:
            return f"{header}\n\n{body}\n"
        return f"{body}\n"

    def generate_source_map(self, debug: bool = False) -> Tuple[str, Any]:
        """Render Python DSL code and return associated SourceMap."""
        from .sourcemap import SourceMapEmitter
        return SourceMapEmitter(self.instruction_by_address, debug=debug).emit_program(self)
