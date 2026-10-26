"""Dataflow and Use-Def Analysis for Expression Recovery.

Analyzes definition-use chains across Structured Control Flow IR, recovers
Python expression trees from flat mlog instructions (set, op, jump conditions),
performs safe copy/constant propagation, and eliminates compiler temporaries
strictly following the Zero Guessing principle.
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from .expression import (
    MLOG_TO_PY_BINARY_OPS,
    BinaryExpr,
    CallExpr,
    ConstantExpr,
    Expr,
    FormattedStringExpr,
    IfExpExpr,
    UnaryExpr,
    VariableExpr,
    parse_operand_to_expr,
)
from .semantics import (
    ArgumentSemanticRole,
    UNARY_LOGIC_OPS,
    get_argument_semantic_role,
    get_instruction_dest_vars,
    get_instruction_read_vars,
    is_safe_inline_expression,
)
from .instruction import MlogInstruction
from .structured_ir import (
    AssignNode,
    ExprStmtNode,
    IfNode,
    InstructionNode,
    StructuredNode,
    StructuredProgram,
    WhileNode,
    is_compiler_temporary,
)
from .function_ir import CallNode, ReturnNode


def condition_to_expr(cond: str, a: str, b: str, invert: bool = False) -> Expr:
    """Construct an initial Expr for a jump condition."""
    if cond == "always":
        return ConstantExpr(value=False if invert else True)

    # Truthiness / boolean constant checks
    if cond == "equal" and a == "true" and b == "0":
        return ConstantExpr(value=True if invert else False)
    if cond == "notEqual" and a == "true" and b == "0":
        return ConstantExpr(value=False if invert else True)

    a_expr = parse_operand_to_expr(a)
    b_expr = parse_operand_to_expr(b)

    cmp_map = {
        "equal": "!=" if invert else "==",
        "notEqual": "==" if invert else "!=",
        "lessThan": ">=" if invert else "<",
        "lessThanEq": ">" if invert else "<=",
        "greaterThan": "<=" if invert else ">",
        "greaterThanEq": "<" if invert else ">=",
        "strictEqual": "is not" if invert else "is",
    }
    py_op = cmp_map.get(cond, "==")
    return BinaryExpr(op=py_op, left=a_expr, right=b_expr)


def semantic_argument_to_expr(
    opcode: str,
    arg_idx: int,
    arg: str,
    defined_variables: Optional[Set[str]],
    all_args: Tuple[str, ...],
) -> Expr:
    """Convert an instruction argument to an Expr node respecting semantic roles and SSOT."""
    if arg == "true":
        return ConstantExpr(value=True, raw_str=arg)
    if arg == "false":
        return ConstantExpr(value=False, raw_str=arg)
    if arg == "null":
        return ConstantExpr(value=None, raw_str=arg)
    if arg.startswith('"') and arg.endswith('"'):
        return ConstantExpr(value=arg[1:-1], raw_str=arg)
    if opcode in ("printchar", "format") and arg_idx == 0:
        from ..mlog_registry import to_snake, REG_ITEMS, REG_LIQUIDS, REG_UNIT_TYPES
        if arg in REG_ITEMS.by_token:
            entry = REG_ITEMS.by_token[arg]
            return VariableExpr(name=f"Items.{to_snake(entry.source_name)}")
        if arg in REG_LIQUIDS.by_token:
            entry = REG_LIQUIDS.by_token[arg]
            return VariableExpr(name=f"Liquids.{to_snake(entry.source_name)}")
        if arg in REG_UNIT_TYPES.by_token:
            entry = REG_UNIT_TYPES.by_token[arg]
            return VariableExpr(name=f"Units.{to_snake(entry.source_name)}")
    if arg.startswith("@"):
        return ConstantExpr(value=arg, raw_str=arg)
    if arg.isdigit() or (arg.startswith("-") and arg[1:].isdigit()):
        try:
            return ConstantExpr(value=int(arg), raw_str=arg)
        except ValueError:
            pass
    try:
        val = float(arg)
        return ConstantExpr(value=val, raw_str=arg)
    except ValueError:
        pass

    role = get_argument_semantic_role(opcode, arg_idx, all_args)
    if role == ArgumentSemanticRole.BLOCK_OR_DEVICE:
        if defined_variables is not None and arg in defined_variables:
            return VariableExpr(name=arg)
        return ConstantExpr(value=arg, raw_str=arg)

    if role == ArgumentSemanticRole.KEYWORD_OR_ENUM:
        return ConstantExpr(value=arg, raw_str=arg)

    if role == ArgumentSemanticRole.VARIABLE_DEF:
        return VariableExpr(name=arg)

    if arg.isidentifier() and not arg.startswith("@"):
        return VariableExpr(name=arg)

    return ConstantExpr(value=arg, raw_str=arg)



def substitute_variable(expr: Expr, var_name: str, replacement: Expr) -> Expr:
    """Recursively replace occurrences of var_name with replacement expression."""
    if isinstance(expr, VariableExpr):
        if expr.name == var_name:
            return replacement
        return expr

    if isinstance(expr, UnaryExpr):
        new_operand = substitute_variable(expr.operand, var_name, replacement)
        if expr.op == "not" and isinstance(new_operand, BinaryExpr) and new_operand.op == "is":
            return BinaryExpr(op="is not", left=new_operand.left, right=new_operand.right)
        return UnaryExpr(
            op=expr.op,
            operand=new_operand,
        )

    if isinstance(expr, BinaryExpr):
        return BinaryExpr(
            op=expr.op,
            left=substitute_variable(expr.left, var_name, replacement),
            right=substitute_variable(expr.right, var_name, replacement),
        )

    if isinstance(expr, CallExpr):
        return CallExpr(
            func=expr.func,
            args=[substitute_variable(a, var_name, replacement) for a in expr.args],
        )

    if isinstance(expr, FormattedStringExpr):
        return FormattedStringExpr(
            parts=[
                substitute_variable(p, var_name, replacement) if isinstance(p, Expr) else p
                for p in expr.parts
            ]
        )

    if isinstance(expr, IfExpExpr):
        return IfExpExpr(
            test=substitute_variable(expr.test, var_name, replacement),
            body=substitute_variable(expr.body, var_name, replacement),
            orelse=substitute_variable(expr.orelse, var_name, replacement),
        )

    return expr


def get_expr_variables(expr: Optional[Expr]) -> Set[str]:
    """Return all variable names referenced in expr."""
    return expr.variables_used if expr is not None else set()


def get_node_defs(node: StructuredNode) -> Set[str]:
    """Return set of variables defined (written to) by this node."""
    if isinstance(node, AssignNode):
        return {node.target}

    if isinstance(node, InstructionNode):
        return set(get_instruction_dest_vars(node.instruction))

    if isinstance(node, IfNode):
        defs = set()
        for n in node.then_body:
            defs.update(get_node_defs(n))
        for n in node.else_body:
            defs.update(get_node_defs(n))
        return defs

    if isinstance(node, WhileNode):
        defs = set()
        for n in node.body:
            defs.update(get_node_defs(n))
        return defs

    if isinstance(node, CallNode):
        return {node.target} if node.target is not None else set()

    if isinstance(node, ReturnNode):
        return set()

    return set()


def get_node_uses(node: StructuredNode) -> Set[str]:
    """Return set of variables referenced (read from) by this node directly."""
    if isinstance(node, AssignNode):
        return get_expr_variables(node.value)

    if isinstance(node, ExprStmtNode):
        return get_expr_variables(node.expr)

    if isinstance(node, ReturnNode):
        return get_expr_variables(node.value) if node.value is not None else set()

    if isinstance(node, CallNode):
        uses = set()
        for arg in node.args:
            uses.update(get_expr_variables(arg))
        return uses

    if isinstance(node, IfNode):
        uses = get_expr_variables(node.condition_expr)
        for n in node.then_body:
            uses.update(get_node_uses(n))
        for n in node.else_body:
            uses.update(get_node_uses(n))
        return uses

    if isinstance(node, WhileNode):
        uses = get_expr_variables(node.condition_expr)
        for n in node.body:
            uses.update(get_node_uses(n))
        return uses

    if isinstance(node, InstructionNode):
        return set(get_instruction_read_vars(node.instruction, getattr(node, "defined_variables", None)))

    return set()


def fold_constants(expr: Expr) -> Expr:
    """Evaluate compile-time constant sub-expressions while preserving Mindustry semantics."""
    import math

    if isinstance(expr, BinaryExpr):
        left = fold_constants(expr.left)
        right = fold_constants(expr.right)
        if isinstance(left, ConstantExpr) and isinstance(right, ConstantExpr):
            v1, v2 = left.value, right.value
            # Only fold pure numbers, never booleans as ints, never strings/builtins
            if (
                isinstance(v1, (int, float))
                and isinstance(v2, (int, float))
                and not isinstance(v1, bool)
                and not isinstance(v2, bool)
            ):
                op = expr.op
                res = None
                if op == "+":
                    res = v1 + v2
                elif op == "-":
                    res = v1 - v2
                elif op == "*":
                    res = v1 * v2
                elif op == "//" and v2 != 0:
                    res = v1 // v2
                elif op == "%" and v2 != 0:
                    res = v1 % v2
                elif op == "**" and 0 <= v2 <= 32:
                    try:
                        res = v1 ** v2
                    except OverflowError:
                        res = None
                elif op == "<<" and isinstance(v1, int) and isinstance(v2, int) and 0 <= v2 <= 64:
                    res = v1 << v2
                elif op == ">>" and isinstance(v1, int) and isinstance(v2, int) and 0 <= v2 <= 64:
                    res = v1 >> v2
                elif op == "&" and isinstance(v1, int) and isinstance(v2, int):
                    res = v1 & v2
                elif op == "|" and isinstance(v1, int) and isinstance(v2, int):
                    res = v1 | v2
                elif op == "^" and isinstance(v1, int) and isinstance(v2, int):
                    res = v1 ^ v2
                elif op == "/" and v2 != 0:
                    div_res = v1 / v2
                    if v1 % v2 == 0:
                        res = int(v1 // v2) if isinstance(v1, int) and isinstance(v2, int) else div_res
                    elif round(div_res, 6) == div_res:
                        res = div_res
                elif op in ("==", "!=", "<", "<=", ">", ">="):
                    if op == "==":
                        return ConstantExpr(v1 == v2)
                    elif op == "!=":
                        return ConstantExpr(v1 != v2)
                    elif op == "<":
                        return ConstantExpr(v1 < v2)
                    elif op == "<=":
                        return ConstantExpr(v1 <= v2)
                    elif op == ">":
                        return ConstantExpr(v1 > v2)
                    elif op == ">=":
                        return ConstantExpr(v1 >= v2)

                if res is not None and not (math.isnan(res) or math.isinf(res)):
                    if isinstance(v1, int) and isinstance(v2, int) and op != "/" and isinstance(res, (int, float)):
                        res = int(res)
                    return ConstantExpr(res)
        return BinaryExpr(expr.op, left, right)

    if isinstance(expr, UnaryExpr):
        operand = fold_constants(expr.operand)
        if isinstance(operand, ConstantExpr):
            v = operand.value
            if expr.op == "-" and isinstance(v, (int, float)) and not isinstance(v, bool):
                return ConstantExpr(-v)
            elif expr.op == "~" and isinstance(v, int) and not isinstance(v, bool):
                return ConstantExpr(~v)
            elif expr.op == "not" and isinstance(v, bool):
                return ConstantExpr(not v)
        return UnaryExpr(expr.op, operand)

    if isinstance(expr, CallExpr):
        new_args = [fold_constants(a) for a in expr.args]
        if (
            expr.func == "min"
            and len(new_args) == 2
            and isinstance(new_args[0], ConstantExpr)
            and isinstance(new_args[1], ConstantExpr)
        ):
            v1, v2 = new_args[0].value, new_args[1].value
            if (
                isinstance(v1, (int, float))
                and isinstance(v2, (int, float))
                and not isinstance(v1, bool)
                and not isinstance(v2, bool)
            ):
                return ConstantExpr(min(v1, v2))
        if (
            expr.func == "max"
            and len(new_args) == 2
            and isinstance(new_args[0], ConstantExpr)
            and isinstance(new_args[1], ConstantExpr)
        ):
            v1, v2 = new_args[0].value, new_args[1].value
            if (
                isinstance(v1, (int, float))
                and isinstance(v2, (int, float))
                and not isinstance(v1, bool)
                and not isinstance(v2, bool)
            ):
                return ConstantExpr(max(v1, v2))
        return CallExpr(expr.func, new_args)

    if isinstance(expr, IfExpExpr):
        test = fold_constants(expr.test)
        body = fold_constants(expr.body)
        orelse = fold_constants(expr.orelse)
        return IfExpExpr(test=test, body=body, orelse=orelse)


    return expr


# Opcodes that must never receive an inlined expression operand: their operands are
# instruction addresses or explicit control-flow tokens, not plain values.
_CONTROL_FLOW_OPCODES = frozenset({"jump", "stop", "end"})


def inline_temporary_into_instruction(
    instr: MlogInstruction,
    target: str,
    value: Expr,
) -> Optional[MlogInstruction]:
    """Substitute a single-use temporary or alias into a raw instruction operand.

    Returns a new ``MlogInstruction`` when every occurrence of ``target`` in the
    operand list sits in a substitutable position, otherwise ``None``.

    Safety rules (Zero Guessing principle -- no speculative rewriting):
      * Control-flow opcodes are never touched.
      * Only ``OPERAND``-role positions qualify. Destinations (``VARIABLE_DEF``),
        hardware links (``BLOCK_OR_DEVICE``), enum/token selectors
        (``KEYWORD_OR_ENUM``) and ``@``-constants are never rewritten, because
        substituting an expression there would change semantics or produce
        uncompilable DSL.
      * For VariableExpr aliases (e.g. ``b = g``), direct substitution is safe
        when the source is a valid DSL identifier.
      * For arithmetic expressions, the rendered value must satisfy
        ``is_safe_inline_expression`` (pure arithmetic/bitwise over identifiers
        and numbers). This is the exact same SSOT predicate the Python renderer
        uses to decide whether an operand is an expression or a string literal,
        so the inliner can never emit an operand the renderer would silently quote
        back into a string.
      * The value must be side-effect free; re-evaluation is only safe then.
    """
    if instr.opcode in _CONTROL_FLOW_OPCODES:
        return None
    if target not in instr.args:
        return None
    if value.has_side_effects:
        return None
    if not isinstance(value, (BinaryExpr, UnaryExpr, VariableExpr, IfExpExpr)):
        return None

    if isinstance(value, VariableExpr):
        new_name = value.name
        if not new_name.isidentifier() or new_name.startswith("@") or new_name in ("true", "false", "null"):
            return None
        args = list(instr.args)
        for idx, arg in enumerate(args):
            if arg != target:
                continue
            role = get_argument_semantic_role(instr.opcode, idx, instr.args)
            if role is not ArgumentSemanticRole.OPERAND:
                return None
            args[idx] = new_name
        return MlogInstruction(
            address=instr.address,
            opcode=instr.opcode,
            args=tuple(args),
            loc=instr.loc,
            raw_text=instr.raw_text,
        )

    rendered = value.to_python()
    if not is_safe_inline_expression(rendered):
        return None

    args = list(instr.args)
    for idx, arg in enumerate(args):
        if arg != target:
            continue
        role = get_argument_semantic_role(instr.opcode, idx, instr.args)
        if role is not ArgumentSemanticRole.OPERAND:
            return None
        args[idx] = rendered

    return MlogInstruction(
        address=instr.address,
        opcode=instr.opcode,
        args=tuple(args),
        loc=instr.loc,
        raw_text=instr.raw_text,
    )


class DataflowTransformer:
    """Transforms Structured Control Flow IR into Expression-rich Python AST."""

    def transform_program(self, program: StructuredProgram) -> StructuredProgram:
        """Main entry point: recovers expressions across the entire program."""
        if not program.is_fully_structured:
            return program

        # Pass 1: Convert raw linear InstructionNodes (set, op, print, format) into AssignNodes/ExprStmtNodes
        converted_body = self._convert_instructions_in_list(program.body)

        # Pass 2: Dataflow analysis & safe inlining across structured scopes
        optimized_body = self._optimize_scope(converted_body)

        # Pass 3: Recover f-strings from consecutive print + format statements
        final_body = self._recover_fstrings_in_scope(optimized_body)

        return StructuredProgram(
            body=final_body,
            is_fully_structured=program.is_fully_structured,
            unstructured_reasons=program.unstructured_reasons,
            instruction_by_address=getattr(program, "instruction_by_address", {}),
            defined_variables=getattr(program, "defined_variables", None),
        )

    def transform_scope(self, nodes: List[StructuredNode]) -> List[StructuredNode]:
        """Transform and optimize a structured scope of nodes including f-string recovery."""
        converted = self._convert_instructions_in_list(nodes)
        optimized = self._optimize_scope(converted)
        return self._recover_fstrings_in_scope(optimized)

    # -----------------------------------------------------------------------
    # Step 1: Instruction -> Expression IR Conversion
    # -----------------------------------------------------------------------

    def _convert_instructions_in_list(self, nodes: List[StructuredNode]) -> List[StructuredNode]:
        """Convert set/op InstructionNodes to AssignNodes and initialize condition_expr."""
        result: List[StructuredNode] = []

        for node in nodes:
            if isinstance(node, InstructionNode):
                instr = node.instruction
                op = instr.opcode
                args = instr.args

                # Case A: set dest src -> dest = src
                if op == "set" and len(args) == 2:
                    dest = args[0]
                    if not dest.isidentifier() or dest.startswith("@"):
                        result.append(node)
                        continue
                    src_expr = parse_operand_to_expr(args[1])
                    result.append(AssignNode(target=dest, value=src_expr, source_addresses=[instr.address]))
                    continue

                # Case B: op <op_name> dest a b -> dest = (a op b) or call
                if op == "op" and len(args) >= 3:
                    op_name = args[0]
                    dest = args[1]
                    a_expr = parse_operand_to_expr(args[2])
                    b_expr = parse_operand_to_expr(args[3]) if len(args) > 3 else ConstantExpr(0)

                    # B.1: Standard binary arithmetic / bitwise / comparison
                    if op_name in MLOG_TO_PY_BINARY_OPS:
                        py_op = MLOG_TO_PY_BINARY_OPS[op_name]
                        # Special unary cases:
                        if op_name == "sub" and isinstance(a_expr, ConstantExpr) and a_expr.value == 0:
                            expr = UnaryExpr("-", b_expr)
                        elif op_name == "equal" and isinstance(b_expr, ConstantExpr) and b_expr.value == 0:
                            expr = UnaryExpr("not", a_expr)
                        else:
                            expr = BinaryExpr(py_op, a_expr, b_expr)
                        result.append(AssignNode(target=dest, value=fold_constants(expr), source_addresses=[instr.address]))
                        continue

                    # B.2: Unary not (bitwise)
                    if op_name == "not":
                        result.append(AssignNode(target=dest, value=fold_constants(UnaryExpr("~", a_expr)), source_addresses=[instr.address]))
                        continue

                    # B.3: Python min and max calls: dest = min(a, b) or max(a, b)
                    if op_name in ("min", "max") and len(args) >= 4:
                        result.append(
                            AssignNode(
                                target=dest,
                                value=fold_constants(CallExpr(op_name, [a_expr, b_expr])),
                                source_addresses=[instr.address],
                            )
                        )
                        continue

                    # B.4: General logic operation call: op("max", a, b) or op("rand", a)
                    call_args = [ConstantExpr(op_name), a_expr]
                    if len(args) > 3 and op_name not in UNARY_LOGIC_OPS:
                        call_args.append(b_expr)
                    result.append(AssignNode(target=dest, value=fold_constants(CallExpr("op", call_args)), source_addresses=[instr.address]))
                    continue

                defined_vars = getattr(node, "defined_variables", None)

                # Case C: read dest cell address -> dest = read(cell, address)
                if op == "read" and len(args) == 3:
                    dest = args[0]
                    if dest.isidentifier() and not dest.startswith("@"):
                        cell_expr = semantic_argument_to_expr("read", 1, args[1], defined_vars, args)
                        addr_expr = semantic_argument_to_expr("read", 2, args[2], defined_vars, args)
                        result.append(AssignNode(target=dest, value=CallExpr("read", [cell_expr, addr_expr]), source_addresses=[instr.address]))
                        continue

                # Case D: sensor dest block prop -> dest = sensor(block, prop)
                if op == "sensor" and len(args) == 3:
                    dest = args[0]
                    if dest.isidentifier() and not dest.startswith("@"):
                        block_expr = semantic_argument_to_expr("sensor", 1, args[1], defined_vars, args)
                        prop_expr = semantic_argument_to_expr("sensor", 2, args[2], defined_vars, args)
                        result.append(AssignNode(target=dest, value=CallExpr("sensor", [block_expr, prop_expr]), source_addresses=[instr.address]))
                        continue

                # Case E: getlink dest index -> dest = getlink(index)
                if op == "getlink" and len(args) == 2:
                    dest = args[0]
                    if dest.isidentifier() and not dest.startswith("@"):
                        idx_expr = semantic_argument_to_expr("getlink", 1, args[1], defined_vars, args)
                        result.append(AssignNode(target=dest, value=CallExpr("getlink", [idx_expr]), source_addresses=[instr.address]))
                        continue

                # Case F: lookup type dest index -> dest = lookup(type, index)
                if op == "lookup" and len(args) == 3:
                    dest = args[1]
                    if dest.isidentifier() and not dest.startswith("@"):
                        type_expr = semantic_argument_to_expr("lookup", 0, args[0], defined_vars, args)
                        idx_expr = semantic_argument_to_expr("lookup", 2, args[2], defined_vars, args)
                        result.append(AssignNode(target=dest, value=CallExpr("lookup", [type_expr, idx_expr]), source_addresses=[instr.address]))
                        continue

                # Case G: packcolor dest r g b a -> dest = packcolor(r, g, b, a)
                if op == "packcolor" and len(args) == 5:
                    dest = args[0]
                    if dest.isidentifier() and not dest.startswith("@"):
                        params = [semantic_argument_to_expr("packcolor", i, args[i], defined_vars, args) for i in range(1, 5)]
                        result.append(AssignNode(target=dest, value=CallExpr("packcolor", params), source_addresses=[instr.address]))
                        continue

                # Case H: radar target1 target2 target3 sort turret sort_order output -> output = radar(...)
                if op == "radar" and len(args) >= 7:
                    dest = args[6]
                    if dest.isidentifier() and not dest.startswith("@"):
                        params = [semantic_argument_to_expr("radar", i, args[i], defined_vars, args) for i in range(6)]
                        result.append(AssignNode(target=dest, value=CallExpr("radar", params), source_addresses=[instr.address]))
                        continue

                # Case I: uradar target1 target2 target3 sort 0 sort_order output -> output = uradar(...)
                if op == "uradar":
                    if len(args) == 7:
                        dest = args[6]
                        if dest.isidentifier() and not dest.startswith("@"):
                            params = [semantic_argument_to_expr("uradar", i, args[i], defined_vars, args) for i in (0, 1, 2, 3, 5)]
                            result.append(AssignNode(target=dest, value=CallExpr("uradar", params), source_addresses=[instr.address]))
                            continue
                    elif len(args) == 6:
                        dest = args[5]
                        if dest.isidentifier() and not dest.startswith("@"):
                            params = [semantic_argument_to_expr("uradar", i, args[i], defined_vars, args) for i in range(5)]
                            result.append(AssignNode(target=dest, value=CallExpr("uradar", params), source_addresses=[instr.address]))
                            continue

                # Case J: format value -> format(value)
                if op == "format" and len(args) == 1:
                    val_expr = semantic_argument_to_expr("format", 0, args[0], defined_vars, args)
                    result.append(
                        ExprStmtNode(
                            expr=CallExpr("format", [val_expr]),
                            source_addresses=[instr.address],
                        )
                    )
                    continue

                # Case K: select dest cond comp0 comp1 a b -> dest = a if cond_expr else b
                if op == "select" and len(args) == 6:
                    dest = args[0]
                    if dest.isidentifier() and not dest.startswith("@"):
                        cond = args[1]
                        comp0_expr = semantic_argument_to_expr("select", 2, args[2], defined_vars, args)
                        comp1_expr = semantic_argument_to_expr("select", 3, args[3], defined_vars, args)
                        a_expr = semantic_argument_to_expr("select", 4, args[4], defined_vars, args)
                        b_expr = semantic_argument_to_expr("select", 5, args[5], defined_vars, args)

                        # Reconstruct condition expression
                        if cond == "notEqual" and args[3] in ("0", "false"):
                            test_expr = comp0_expr
                        elif cond == "equal" and args[3] in ("0", "false"):
                            test_expr = UnaryExpr("not", comp0_expr)
                        elif cond in MLOG_TO_PY_BINARY_OPS:
                            py_op = MLOG_TO_PY_BINARY_OPS[cond]
                            test_expr = BinaryExpr(py_op, comp0_expr, comp1_expr)
                        elif cond == "always":
                            test_expr = ConstantExpr(True)
                        else:
                            test_expr = BinaryExpr(cond, comp0_expr, comp1_expr)

                        result.append(
                            AssignNode(
                                target=dest,
                                value=fold_constants(IfExpExpr(test=test_expr, body=a_expr, orelse=b_expr)),
                                source_addresses=[instr.address],
                            )
                        )
                        continue

                # Fallback: keep InstructionNode untouched (Zero Guessing)
                result.append(node)


            elif isinstance(node, IfNode):
                # Recursively convert then and else branches
                node.then_body = self._convert_instructions_in_list(node.then_body)
                node.else_body = self._convert_instructions_in_list(node.else_body)
                result.append(node)

            elif isinstance(node, WhileNode):
                # Recursively convert body
                node.body = self._convert_instructions_in_list(node.body)
                result.append(node)

            else:
                result.append(node)

        return result

    # -----------------------------------------------------------------------
    # Step 2: Use-Def Counting & Scope Optimization
    # -----------------------------------------------------------------------

    def _optimize_scope(self, nodes: List[StructuredNode]) -> List[StructuredNode]:
        """Optimize expressions within a structured scope using iterative inlining."""
        # First recursively optimize inner scopes
        for node in nodes:
            if isinstance(node, IfNode):
                node.then_body = self._optimize_scope(node.then_body)
                node.else_body = self._optimize_scope(node.else_body)
            elif isinstance(node, WhileNode):
                node.body = self._optimize_scope(node.body)

        # Iteratively inline single-use temporaries within this linear block
        changed = True
        current_nodes = list(nodes)

        while changed:
            changed = False
            use_counts = self._count_global_uses(current_nodes)
            def_counts = self._count_global_defs(current_nodes)

            # Look for inlining opportunities
            for i, stmt in enumerate(current_nodes):
                if not isinstance(stmt, AssignNode):
                    continue

                target = stmt.target
                val = stmt.value

                # Criteria 1: Candidate temporary or single-use local intermediate
                is_temp = is_compiler_temporary(target)
                is_alias = (
                    (not is_temp)
                    and isinstance(val, VariableExpr)
                    and val.name.isidentifier()
                    and not val.name.startswith("@")
                    and val.name not in ("true", "false", "null")
                    and val.name != target
                )

                if not is_temp and not is_alias:
                    continue

                # Criteria 2: Exactly 1 definition and exactly 1 use
                if def_counts.get(target, 0) != 1 or use_counts.get(target, 0) != 1:
                    continue

                # Criteria 3: Value has no side effects
                if val.has_side_effects:
                    continue

                # Find the statement j (j > i) where target is used
                use_idx = None
                for j in range(i + 1, len(current_nodes)):
                    if target in get_node_uses(current_nodes[j]):
                        use_idx = j
                        break

                if use_idx is None:
                    # Target might be used inside an inner block or not found in top-level
                    continue

                target_node = current_nodes[use_idx]

                # If target_node is a compound block (IfNode or WhileNode), target MUST be used in
                # its condition_expr directly to be inlined safely from outside without moving across control boundaries.
                if isinstance(target_node, (IfNode, WhileNode)):
                    if target_node.condition_expr is None or target not in get_expr_variables(target_node.condition_expr):
                        continue

                # Criteria 4: No intervening statements modify any variable in val.variables_used
                val_vars = val.variables_used
                if isinstance(target_node, WhileNode) and (get_node_defs(target_node) & val_vars):
                    continue

                intervening_overwrite = False
                for k in range(i + 1, use_idx):
                    if get_node_defs(current_nodes[k]) & val_vars:
                        intervening_overwrite = True
                        break

                if intervening_overwrite:
                    continue

                # ALL SAFETY CHECKS PASSED: Safely inline target with val!
                merged_addrs = sorted(
                    set(getattr(target_node, "source_addresses", []))
                    | set(getattr(stmt, "source_addresses", []))
                )

                if isinstance(target_node, AssignNode):
                    new_val = fold_constants(substitute_variable(target_node.value, target, val))
                    current_nodes[use_idx] = AssignNode(
                        target=target_node.target,
                        value=new_val,
                        source_addresses=merged_addrs,
                    )
                    current_nodes.pop(i)
                    changed = True
                    break

                elif isinstance(target_node, ExprStmtNode):
                    new_expr = fold_constants(substitute_variable(target_node.expr, target, val))
                    current_nodes[use_idx] = ExprStmtNode(
                        expr=new_expr,
                        source_addresses=merged_addrs,
                    )
                    current_nodes.pop(i)
                    changed = True
                    break

                elif isinstance(target_node, IfNode) and target_node.condition_expr is not None:
                    new_cond = fold_constants(substitute_variable(target_node.condition_expr, target, val))
                    target_node.condition_expr = new_cond
                    target_node.source_addresses = merged_addrs
                    current_nodes.pop(i)
                    changed = True
                    break

                elif isinstance(target_node, WhileNode) and target_node.condition_expr is not None:
                    new_cond = fold_constants(substitute_variable(target_node.condition_expr, target, val))
                    target_node.condition_expr = new_cond
                    target_node.source_addresses = merged_addrs
                    current_nodes.pop(i)
                    changed = True
                    break

                elif isinstance(target_node, ReturnNode) and target_node.value is not None:
                    new_val = fold_constants(substitute_variable(target_node.value, target, val))
                    target_node.value = new_val
                    target_node.source_addresses = merged_addrs
                    current_nodes.pop(i)
                    changed = True
                    break

                elif isinstance(target_node, CallNode):
                    new_args = [fold_constants(substitute_variable(a, target, val)) for a in target_node.args]
                    target_node.args = new_args
                    target_node.source_addresses = merged_addrs
                    current_nodes.pop(i)
                    changed = True
                    break

                elif isinstance(target_node, InstructionNode):
                    new_instr = inline_temporary_into_instruction(
                        target_node.instruction, target, val
                    )
                    if new_instr is None:
                        continue
                    target_node.instruction = new_instr
                    target_node.source_addresses = merged_addrs
                    current_nodes.pop(i)
                    changed = True
                    break

        return current_nodes

    def _count_global_uses(self, nodes: List[StructuredNode]) -> Dict[str, int]:
        """Count total occurrences of each variable across all nodes."""
        counts: Dict[str, int] = {}

        def walk(n: StructuredNode):
            for var in get_node_uses(n):
                counts[var] = counts.get(var, 0) + 1

        for n in nodes:
            walk(n)

        return counts

    def _count_global_defs(self, nodes: List[StructuredNode]) -> Dict[str, int]:
        """Count total definitions of each variable across all nodes."""
        counts: Dict[str, int] = {}

        def walk(n: StructuredNode):
            for var in get_node_defs(n):
                counts[var] = counts.get(var, 0) + 1

        for n in nodes:
            walk(n)

        return counts

    def _extract_print_template(self, node: StructuredNode) -> Optional[Tuple[str, List[int]]]:
        """Extract template text and source addresses if node is a print of a string literal."""
        if isinstance(node, ExprStmtNode) and isinstance(node.expr, CallExpr) and node.expr.func == "print":
            if len(node.expr.args) == 1:
                arg = node.expr.args[0]
                if isinstance(arg, ConstantExpr) and isinstance(arg.value, str):
                    return arg.value, list(node.source_addresses)
        elif isinstance(node, InstructionNode):
            instr = node.instruction
            if instr.opcode == "print" and len(instr.args) == 1:
                arg = instr.args[0]
                if arg.startswith('"') and arg.endswith('"'):
                    unquoted = (
                        arg[1:-1]
                        .replace('\\\\', '\x00')
                        .replace('\\"', '"')
                        .replace('\\n', '\n')
                        .replace('\x00', '\\')
                    )
                    return unquoted, list(node.source_addresses)
        return None

    def _extract_format_arg(self, node: StructuredNode) -> Optional[Tuple[Expr, List[int]]]:
        """Extract argument expression and source addresses if node is a format call."""
        if isinstance(node, ExprStmtNode) and isinstance(node.expr, CallExpr) and node.expr.func == "format":
            if len(node.expr.args) == 1:
                return node.expr.args[0], list(node.source_addresses)
        elif isinstance(node, InstructionNode):
            instr = node.instruction
            if instr.opcode == "format" and len(instr.args) == 1:
                arg_expr = parse_operand_to_expr(instr.args[0])
                return arg_expr, list(node.source_addresses)
        return None

    def _build_fstring_parts(self, template: str, format_args: List[Expr]) -> List[Any]:
        """Split template string by {0}..{k-1} placeholders and insert format_args."""
        parts: List[Any] = []
        last_end = 0
        import re
        for match in re.finditer(r'\{(\d+)\}', template):
            start, end = match.span()
            if start > last_end:
                parts.append(template[last_end:start])
            idx = int(match.group(1))
            if idx < len(format_args):
                parts.append(format_args[idx])
            else:
                parts.append(match.group(0))
            last_end = end
        if last_end < len(template):
            parts.append(template[last_end:])
        return parts

    def _recover_fstrings_in_scope(self, nodes: List[StructuredNode]) -> List[StructuredNode]:
        """Convert consecutive print(template) and format(...) into print(f'...')."""
        result: List[StructuredNode] = []
        i = 0
        n = len(nodes)
        import re
        has_dangling_placeholders = False
        while i < n:
            node = nodes[i]

            if isinstance(node, IfNode):
                node.then_body = self._recover_fstrings_in_scope(node.then_body)
                node.else_body = self._recover_fstrings_in_scope(node.else_body)
                result.append(node)
                i += 1
                has_dangling_placeholders = False
                continue
            elif isinstance(node, WhileNode):
                node.body = self._recover_fstrings_in_scope(node.body)
                result.append(node)
                i += 1
                has_dangling_placeholders = False
                continue

            # Check for buffer flush (resets any dangling placeholders)
            is_flush = False
            if isinstance(node, InstructionNode) and node.instruction.opcode == "printflush":
                is_flush = True
            elif isinstance(node, ExprStmtNode) and isinstance(node.expr, CallExpr) and node.expr.func == "printflush":
                is_flush = True
            if is_flush:
                has_dangling_placeholders = False

            template_info = self._extract_print_template(node)
            if template_info is not None:
                template_text, print_source_addrs = template_info
                placeholders = re.findall(r'\{(\d+)\}', template_text)
                if placeholders:
                    int_placeholders = [int(p) for p in placeholders]
                    k = len(int_placeholders)
                    # Placeholders must be exactly 0, 1, ..., k-1 in sequence, k <= 10,
                    # and there must be no preceding unformatted placeholders in buffer
                    if (not has_dangling_placeholders) and (k <= 10) and (int_placeholders == list(range(k))) and (i + k < n):
                        format_args = []
                        all_format = True
                        merged_addrs = list(print_source_addrs)
                        for offset in range(1, k + 1):
                            next_node = nodes[i + offset]
                            fmt_arg_info = self._extract_format_arg(next_node)
                            if fmt_arg_info is None:
                                all_format = False
                                break
                            arg_expr, fmt_addrs = fmt_arg_info
                            format_args.append(arg_expr)
                            merged_addrs.extend(fmt_addrs)

                        if all_format:
                            parts = self._build_fstring_parts(template_text, format_args)
                            fstring_expr = FormattedStringExpr(parts=parts)
                            call_expr = CallExpr(func="print", args=[fstring_expr])
                            result.append(ExprStmtNode(expr=call_expr, source_addresses=merged_addrs))
                            i += k + 1
                            continue

                    # If print had placeholders but was not merged, buffer now has dangling placeholders
                    has_dangling_placeholders = True

            result.append(node)
            i += 1

        return result
