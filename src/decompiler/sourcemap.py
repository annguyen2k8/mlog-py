"""Source Mapping and Provenance Tracking for Mindustry Logic Decompiler.

Tracks provenance across the decompilation pipeline:
MLog source -> MlogInstruction -> CFG -> Structured IR -> Expression IR -> Function IR -> Python DSL source.
Provides bidirectional lookup (Python <-> MLog), debug mode formatting, and deterministic JSON export.
"""

from dataclasses import dataclass, field
import json
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from .instruction import MlogInstruction


def format_mlog_address_comment(addresses: List[int]) -> str:
    """Format a list of mlog instruction addresses into a clean debug comment.

    Examples:
        [12] -> "# mlog[12]"
        [15, 16, 17, 18] -> "# mlog[15-18]"
        [10, 11, 14, 15] -> "# mlog[10-11, 14-15]"
    """
    if not addresses:
        return ""
    sorted_addrs = sorted(set(addresses))
    ranges: List[str] = []
    start = sorted_addrs[0]
    end = start

    for a in sorted_addrs[1:]:
        if a == end + 1:
            end = a
        else:
            ranges.append(f"{start}-{end}" if start != end else f"{start}")
            start = a
            end = a
    ranges.append(f"{start}-{end}" if start != end else f"{start}")
    return f"# mlog[{', '.join(ranges)}]"


@dataclass(frozen=True)
class MlogSourceLocation:
    """Source location of an Mlog instruction in original source text."""
    address: int
    line: int
    column: int = 1
    raw_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "address": self.address,
            "line": self.line,
            "column": self.column,
            "raw_text": self.raw_text,
        }


@dataclass
class SourceMapping:
    """Represents a provenance mapping from a generated Python statement to MLog instructions."""
    python_line: int
    python_end_line: int
    node_type: str
    mlog_addresses: List[int] = field(default_factory=list)
    instructions: List[str] = field(default_factory=list)
    source_lines: List[int] = field(default_factory=list)
    description: Optional[str] = None
    ir_node: Optional[Any] = None

    @property
    def address_range(self) -> Optional[Tuple[int, int]]:
        """Return (min_addr, max_addr) if addresses exist, else None."""
        if not self.mlog_addresses:
            return None
        return (min(self.mlog_addresses), max(self.mlog_addresses))

    def to_dict(self) -> Dict[str, Any]:
        """Convert mapping to JSON-serializable dictionary."""
        res: Dict[str, Any] = {
            "python_line": self.python_line,
            "python_end_line": self.python_end_line,
            "node_type": self.node_type,
            "mlog_addresses": sorted(list(set(self.mlog_addresses))),
            "instructions": list(self.instructions),
        }
        if self.source_lines:
            res["source_lines"] = sorted(list(set(self.source_lines)))
        if self.address_range is not None:
            res["address_range"] = [self.address_range[0], self.address_range[1]]
        if self.description:
            res["description"] = self.description
        return res


@dataclass
class SourceMap:
    """Bidirectional provenance mapping between generated Python code and original MLog instructions."""
    version: str = "1.0"
    mappings: List[SourceMapping] = field(default_factory=list)
    instruction_by_address: Dict[int, MlogInstruction] = field(default_factory=dict)

    def add_mapping(self, mapping: SourceMapping):
        """Register a new statement mapping."""
        self.mappings.append(mapping)

    def python_to_mlog(self, python_line: int) -> List[int]:
        """Return sorted unique mlog instruction addresses for the given Python line number."""
        addrs: Set[int] = set()
        for m in self.mappings:
            if m.python_line <= python_line <= m.python_end_line:
                addrs.update(m.mlog_addresses)
        return sorted(addrs)

    def mlog_to_python(self, mlog_address: int) -> Optional[int]:
        """Return primary Python line number (most specific statement) corresponding to an mlog address."""
        matching = [m for m in self.mappings if mlog_address in m.mlog_addresses]
        if not matching:
            return None
        # Prefer specific statement over container FunctionDef
        stmt_matching = [m for m in matching if m.node_type != "FunctionDef"]
        if stmt_matching:
            return min(stmt_matching, key=lambda m: len(m.mlog_addresses)).python_line
        return matching[0].python_line

    def mlog_to_python_lines(self, mlog_address: int) -> List[int]:
        """Return all Python line numbers associated with an mlog instruction address."""
        lines: Set[int] = set()
        for m in self.mappings:
            if mlog_address in m.mlog_addresses:
                lines.add(m.python_line)
        return sorted(lines)

    def get_mapping_by_python_line(self, python_line: int) -> Optional[SourceMapping]:
        """Get the mapping containing the specified Python line."""
        for m in self.mappings:
            if m.python_line <= python_line <= m.python_end_line:
                return m
        return None

    def get_mappings_by_mlog_address(self, mlog_address: int) -> List[SourceMapping]:
        """Get all mappings referencing the specified mlog instruction address."""
        return [m for m in self.mappings if mlog_address in m.mlog_addresses]

    def get_instructions_for_python_line(self, python_line: int) -> List[MlogInstruction]:
        """Get original MlogInstruction objects associated with a Python line."""
        addrs = self.python_to_mlog(python_line)
        return [self.instruction_by_address[a] for a in addrs if a in self.instruction_by_address]

    def to_dict(self) -> Dict[str, Any]:
        """Export source map as deterministic, serializable dictionary."""
        p_to_m: Dict[str, List[int]] = {}
        m_to_p: Dict[str, int] = {}

        # Sort mappings by python_line
        sorted_mappings = sorted(self.mappings, key=lambda m: (m.python_line, m.python_end_line))

        for m in sorted_mappings:
            p_to_m[str(m.python_line)] = sorted(list(set(m.mlog_addresses)))
            for addr in m.mlog_addresses:
                if str(addr) not in m_to_p:
                    m_to_p[str(addr)] = m.python_line

        return {
            "version": self.version,
            "mappings": [m.to_dict() for m in sorted_mappings],
            "python_to_mlog": p_to_m,
            "mlog_to_python": m_to_p,
        }

    def to_json(self, indent: Optional[int] = 2) -> str:
        """Export source map as a deterministic JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        instruction_by_address: Optional[Dict[int, MlogInstruction]] = None,
    ) -> "SourceMap":
        """Reconstruct a SourceMap from a dictionary."""
        sm = cls(
            version=data.get("version", "1.0"),
            instruction_by_address=instruction_by_address or {},
        )
        for m_data in data.get("mappings", []):
            mapping = SourceMapping(
                python_line=m_data["python_line"],
                python_end_line=m_data["python_end_line"],
                node_type=m_data["node_type"],
                mlog_addresses=m_data.get("mlog_addresses", []),
                instructions=m_data.get("instructions", []),
                source_lines=m_data.get("source_lines", []),
                description=m_data.get("description"),
            )
            sm.add_mapping(mapping)
        return sm

    @classmethod
    def from_json(
        cls,
        json_str: str,
        instruction_by_address: Optional[Dict[int, MlogInstruction]] = None,
    ) -> "SourceMap":
        """Reconstruct a SourceMap from a JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data, instruction_by_address=instruction_by_address)


class SourceMapEmitter:
    """Emits Python DSL source code while constructing a SourceMap with statement-level provenance."""

    def __init__(
        self,
        instruction_by_address: Optional[Dict[int, MlogInstruction]] = None,
        debug: bool = False,
    ):
        self.instruction_by_address = instruction_by_address or {}
        self.debug = debug
        self.lines: List[str] = []
        self.mappings: List[SourceMapping] = []

    def current_line(self) -> int:
        return len(self.lines) + 1

    def emit_line(self, line: str):
        self.lines.append(line)

    def _get_instructions_text(self, addrs: List[int]) -> List[str]:
        return [
            self.instruction_by_address[a].raw_text
            for a in sorted(set(addrs))
            if a in self.instruction_by_address and hasattr(self.instruction_by_address[a], "raw_text")
        ]

    def _get_source_lines(self, addrs: List[int]) -> List[int]:
        res: List[int] = []
        for a in sorted(set(addrs)):
            if a in self.instruction_by_address:
                inst = self.instruction_by_address[a]
                if hasattr(inst, "loc") and inst.loc and hasattr(inst.loc, "line"):
                    res.append(inst.loc.line)
        return res

    def _record_mapping(
        self,
        start_line: int,
        end_line: int,
        node_type: str,
        node: Any,
        explicit_addrs: Optional[List[int]] = None,
    ):
        addrs = explicit_addrs if explicit_addrs is not None else getattr(node, "source_addresses", [])
        mapping = SourceMapping(
            python_line=start_line,
            python_end_line=end_line,
            node_type=node_type,
            mlog_addresses=sorted(list(set(addrs))),
            instructions=self._get_instructions_text(addrs),
            source_lines=self._get_source_lines(addrs),
            ir_node=node,
        )
        self.mappings.append(mapping)

    def emit_node(self, node: Any, indent: int = 0):
        prefix = "    " * indent
        from .structured_ir import (
            AssignNode,
            BreakNode,
            ContinueNode,
            ExprStmtNode,
            IfNode,
            InstructionNode,
            PassNode,
            UnstructuredNode,
            WhileNode,
            instruction_to_python,
        )
        from .function_ir import CallNode, FunctionDef, ReturnNode

        addrs = getattr(node, "source_addresses", [])

        if isinstance(node, AssignNode):
            if self.debug and addrs:
                c = format_mlog_address_comment(addrs)
                if c:
                    self.emit_line(f"{prefix}{c}")
            line_no = self.current_line()
            self.emit_line(node.to_python(indent))
            self._record_mapping(line_no, line_no, "Assign", node)

        elif isinstance(node, ExprStmtNode):
            if self.debug and addrs:
                c = format_mlog_address_comment(addrs)
                if c:
                    self.emit_line(f"{prefix}{c}")
            line_no = self.current_line()
            self.emit_line(node.to_python(indent))
            self._record_mapping(line_no, line_no, "ExprStmt", node)

        elif isinstance(node, CallNode):
            if self.debug and addrs:
                c = format_mlog_address_comment(addrs)
                if c:
                    self.emit_line(f"{prefix}{c}")
            line_no = self.current_line()
            self.emit_line(node.to_python(indent))
            self._record_mapping(line_no, line_no, "Call", node)

        elif isinstance(node, ReturnNode):
            if self.debug and addrs:
                c = format_mlog_address_comment(addrs)
                if c:
                    self.emit_line(f"{prefix}{c}")
            line_no = self.current_line()
            self.emit_line(node.to_python(indent))
            self._record_mapping(line_no, line_no, "Return", node)

        elif isinstance(node, BreakNode):
            if self.debug and addrs:
                c = format_mlog_address_comment(addrs)
                if c:
                    self.emit_line(f"{prefix}{c}")
            line_no = self.current_line()
            self.emit_line(f"{prefix}break")
            self._record_mapping(line_no, line_no, "Break", node)

        elif isinstance(node, ContinueNode):
            if self.debug and addrs:
                c = format_mlog_address_comment(addrs)
                if c:
                    self.emit_line(f"{prefix}{c}")
            line_no = self.current_line()
            self.emit_line(f"{prefix}continue")
            self._record_mapping(line_no, line_no, "Continue", node)

        elif isinstance(node, PassNode):
            line_no = self.current_line()
            self.emit_line(f"{prefix}pass")
            self._record_mapping(line_no, line_no, "Pass", node)

        elif isinstance(node, InstructionNode):
            if self.debug and addrs:
                c = format_mlog_address_comment(addrs)
                if c:
                    self.emit_line(f"{prefix}{c}")
            line_no = self.current_line()
            self.emit_line(node.to_python(indent))
            self._record_mapping(line_no, line_no, "Instruction", node)

        elif isinstance(node, UnstructuredNode):
            self.emit_line(f"{prefix}# [UNSTRUCTURED REGION]: {node.reason}")
            for instr in node.instructions:
                if self.debug:
                    self.emit_line(f"{prefix}# mlog[{instr.address}]")
                line_no = self.current_line()
                if instr.is_jump:
                    args_repr = ", ".join(repr(a) for a in instr.args)
                    self.emit_line(f"{prefix}jump({args_repr})  # addr {instr.address}")
                else:
                    self.emit_line(f"{prefix}{instruction_to_python(instr, getattr(node, 'defined_variables', None))}")
                self._record_mapping(line_no, line_no, "Unstructured", node, [instr.address])

        elif isinstance(node, IfNode):
            if self.debug and addrs:
                c = format_mlog_address_comment(addrs)
                if c:
                    self.emit_line(f"{prefix}{c}")
            header_line = self.current_line()
            keyword = "elif" if node.is_elif else "if"
            self.emit_line(f"{prefix}{keyword} {node.condition_text}:")
            self._record_mapping(header_line, header_line, "Elif" if node.is_elif else "If", node)

            if not node.then_body:
                p_line = self.current_line()
                self.emit_line(f"{prefix}    pass")
                self._record_mapping(p_line, p_line, "Pass", PassNode())
            else:
                for child in node.then_body:
                    self.emit_node(child, indent + 1)

            if node.else_body:
                if (
                    len(node.else_body) == 1
                    and isinstance(node.else_body[0], IfNode)
                    and node.else_body[0].is_elif
                ):
                    self.emit_node(node.else_body[0], indent)
                else:
                    self.emit_line(f"{prefix}else:")
                    for child in node.else_body:
                        self.emit_node(child, indent + 1)

        elif isinstance(node, WhileNode):
            if self.debug and addrs:
                c = format_mlog_address_comment(addrs)
                if c:
                    self.emit_line(f"{prefix}{c}")
            header_line = self.current_line()
            self.emit_line(f"{prefix}while {node.condition_text}:")
            self._record_mapping(header_line, header_line, "While", node)

            if not node.body:
                p_line = self.current_line()
                self.emit_line(f"{prefix}    pass")
                self._record_mapping(p_line, p_line, "Pass", PassNode())
            else:
                for child in node.body:
                    self.emit_node(child, indent + 1)

        elif isinstance(node, FunctionDef):
            if self.debug and addrs:
                c = format_mlog_address_comment(addrs)
                if c:
                    self.emit_line(f"{prefix}{c}")
            header_line = self.current_line()
            params_str = ", ".join(node.param_names)
            self.emit_line(f"{prefix}def {node.name}({params_str}):")
            self._record_mapping(header_line, header_line, "FunctionDef", node)

            if not node.body:
                p_line = self.current_line()
                self.emit_line(f"{prefix}    pass")
                self._record_mapping(p_line, p_line, "Pass", PassNode())
            else:
                for child in node.body:
                    self.emit_node(child, indent + 1)

        else:
            line_no = self.current_line()
            if hasattr(node, "to_python"):
                self.emit_line(node.to_python(indent))
            else:
                self.emit_line(f"{prefix}{str(node)}")
            self._record_mapping(line_no, line_no, node.__class__.__name__, node)

    def emit_program(self, program: Any) -> Tuple[str, SourceMap]:
        """Emit complete program with source mappings."""
        from .function_ir import FunctionProgram

        if isinstance(program, FunctionProgram) and program.functions:
            for idx, func in enumerate(program.functions):
                if idx > 0:
                    self.emit_line("")
                self.emit_node(func, indent=0)

            if program.global_statements:
                self.emit_line("")
                for stmt in program.global_statements:
                    self.emit_node(stmt, indent=0)
        else:
            body = getattr(program, "body", [])
            if not body:
                line_no = self.current_line()
                self.emit_line("pass")
                self._record_mapping(line_no, line_no, "Pass", None)
            else:
                for stmt in body:
                    self.emit_node(stmt, indent=0)

        code = "\n".join(self.lines) + "\n"
        source_map = SourceMap(
            version="1.0",
            mappings=self.mappings,
            instruction_by_address=self.instruction_by_address,
        )
        return code, source_map
