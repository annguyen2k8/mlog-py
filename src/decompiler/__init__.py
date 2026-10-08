"""Mindustry Logic (mlog) to Python DSL Decompiler.

Phase 1 provides:
- Canonical mlog instruction parsing with source tracking and error reporting
- Strongly-typed MlogInstruction IR with jump and terminal classification
- Control Flow Graph (CFG) reconstruction with formal basic block leader splitting

Phase 2 provides:
- Structured Control Flow IR (IfNode, WhileNode, BreakNode, ContinueNode, PassNode, UnstructuredNode)
- Dominator tree and natural loop identification
- Recovery of structured control flow (if, if/else, elif, while, break, continue, nested structures)
- Fallback to unstructured control flow on irreducible CFGs or unstructured jumps without guessing

Phase 3 provides:
- Dedicated Expression IR (ConstantExpr, VariableExpr, UnaryExpr, BinaryExpr, CallExpr, UnknownExpr)
- Scoped Dataflow and Use-Def analysis across structured blocks
- Recovery of assignments (AssignNode) and binary/unary arithmetic/bitwise/comparison expression trees
- Safe constant and copy propagation
- Temporary variable identification and safe single-use inlining without side-effects or overwrite violation
- Condition expression recovery for IfNode and WhileNode

Phase 4 provides:
- Dedicated Function IR (FunctionDef, CallNode, ReturnNode, Parameter, ReturnValue, FunctionProgram)
- Program-level CFG analysis to discover function boundaries, call sites, and return paths
- Calling convention verification: link-register (@counter), direct jump, and terminal procedure returns
- Parameter and return value recovery with Zero Guessing
- Support for multiple functions, nested control flow inside functions, and global variable preservation
- Seamless integration with Phase 3 expression and dataflow recovery
"""

from .cfg import (
    BasicBlock,
    CFGBuilder,
    CFGEdge,
    ControlFlowGraph,
    EdgeType,
    build_cfg,
)
from .dataflow import (
    DataflowTransformer,
    condition_to_expr,
    is_compiler_temporary,
    substitute_variable,
)
from .errors import CFGError, DecompileError, MlogParseError
from .expression import (
    BinaryExpr,
    CallExpr,
    ConstantExpr,
    Expr,
    UnaryExpr,
    UnknownExpr,
    VariableExpr,
    parse_operand_to_expr,
)
from .function_analyzer import CallSiteInfo, FunctionAnalyzer, FunctionCandidate
from .function_ir import (
    CallNode,
    FunctionDef,
    FunctionProgram,
    Parameter,
    ReturnNode,
    ReturnValue,
)
from .instruction import JumpType, MlogInstruction
from .parser import MlogParser, parse_mlog
from .structured_ir import (
    AssignNode,
    BreakNode,
    ContinueNode,
    ExprStmtNode,
    IfNode,
    InstructionNode,
    PassNode,
    StructuredNode,
    StructuredProgram,
    UnstructuredNode,
    WhileNode,
    condition_to_python,
    instruction_to_python,
)
from .structurer import (
    CFGStructurer,
    LoopInfo,
    decompile_to_structured,
    recover_expressions,
    structure_cfg,
)


from .sourcemap import (
    MlogSourceLocation,
    SourceMap,
    SourceMapEmitter,
    SourceMapping,
    format_mlog_address_comment,
)
from .semantics import (
    ArgumentSemanticRole,
    collect_program_defined_variables,
    format_semantic_argument,
    get_argument_semantic_role,
    get_instruction_dest_vars,
    get_instruction_read_vars,
)
from .dsl_symbols import (
    collect_used_dsl_symbols,
    extract_dsl_symbols_from_ast,
    format_import_header,
    get_required_dsl_imports,
)
from typing import Tuple, Union


def decompile_program(mlog_text: str, filename: str = "<stdin>") -> FunctionProgram:
    """Full Phase 1-4 pipeline: parses mlog, builds CFG, analyzes functions & expressions."""
    cfg = build_cfg(mlog_text, filename=filename)
    analyzer = FunctionAnalyzer(cfg)
    return analyzer.analyze()


def decompile(
    mlog_text: str,
    filename: str = "<stdin>",
    *,
    debug: bool = False,
    return_source_map: bool = False,
) -> Union[str, Tuple[str, SourceMap]]:
    """Decompile mlog text directly to Python DSL source code (full Phase 1-4.5 pipeline).

    Args:
        mlog_text: Mindustry Logic text source.
        filename: Source filename for error reporting.
        debug: When True, includes '# mlog[...]' address comments above statements.
        return_source_map: When True, returns a (python_code, source_map) tuple.
    """
    program = decompile_program(mlog_text, filename=filename)
    if return_source_map:
        return program.generate_source_map(debug=debug)
    return program.to_python(debug=debug)


def decompile_with_source_map(
    mlog_text: str,
    filename: str = "<stdin>",
    *,
    debug: bool = False,
) -> Tuple[str, SourceMap]:
    """Decompile mlog text and return both Python DSL source code and bidirectional SourceMap."""
    program = decompile_program(mlog_text, filename=filename)
    return program.generate_source_map(debug=debug)


__all__ = [
    # Phase 1
    "BasicBlock",
    "CFGBuilder",
    "CFGEdge",
    "CFGError",
    "ControlFlowGraph",
    "DecompileError",
    "EdgeType",
    "JumpType",
    "MlogInstruction",
    "MlogParseError",
    "MlogParser",
    "build_cfg",
    "parse_mlog",
    # Phase 2
    "BreakNode",
    "CFGStructurer",
    "ContinueNode",
    "IfNode",
    "InstructionNode",
    "LoopInfo",
    "PassNode",
    "StructuredNode",
    "StructuredProgram",
    "UnstructuredNode",
    "WhileNode",
    "condition_to_python",
    "decompile_to_structured",
    "instruction_to_python",
    "structure_cfg",
    # Phase 3
    "AssignNode",
    "BinaryExpr",
    "CallExpr",
    "ConstantExpr",
    "DataflowTransformer",
    "Expr",
    "ExprStmtNode",
    "UnaryExpr",
    "UnknownExpr",
    "VariableExpr",
    "condition_to_expr",
    "decompile",
    "is_compiler_temporary",
    "parse_operand_to_expr",
    "recover_expressions",
    "substitute_variable",
    # Phase 4
    "CallNode",
    "CallSiteInfo",
    "FunctionAnalyzer",
    "FunctionCandidate",
    "FunctionDef",
    "FunctionProgram",
    "Parameter",
    "ReturnNode",
    "ReturnValue",
    "decompile_program",
    # Phase 4.5
    "MlogSourceLocation",
    "SourceMap",
    "SourceMapEmitter",
    "SourceMapping",
    "decompile_with_source_map",
    "format_mlog_address_comment",
    # Semantics
    "ArgumentSemanticRole",
    "collect_program_defined_variables",
    "format_semantic_argument",
    "get_argument_semantic_role",
    "get_instruction_dest_vars",
    "get_instruction_read_vars",
    # DSL Symbols & Imports
    "collect_used_dsl_symbols",
    "extract_dsl_symbols_from_ast",
    "format_import_header",
    "get_required_dsl_imports",
]
