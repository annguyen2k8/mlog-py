"""Dataflow and Use-Def Analysis for Expression Recovery.

Analyzes definition-use chains across Structured Control Flow IR, recovers
Python expression trees from flat mlog instructions (set, op, jump conditions),
performs safe copy/constant propagation, and eliminates compiler temporaries
strictly following the Zero Guessing principle.
"""

from typing import Dict, List, Optional, Set, Tuple

from .expression import (
    MLOG_TO_PY_BINARY_OPS,
    BinaryExpr,
    CallExpr,
    ConstantExpr,
    Expr,
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
)
from .structured_ir import (
    AssignNode,
    ExprStmtNode,
    IfNode,
    InstructionNode,
    StructuredNode,
    StructuredProgram,
    WhileNode,
)
from .function_ir import CallNode, ReturnNode


def is_compiler_temporary(name: str) -> bool:
    """Return True if variable name matches standard compiler temporary conventions."""
    if name.startswith("__tmp"):
        return True
    if name.startswith("*tmp"):
        return True
    if name.startswith("_tmp") and (len(name) <= 5 or name[4:].isdigit()):
        return True
    return False


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
        "strictEqual": "!=" if invert else "==",
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
        return UnaryExpr(
            op=expr.op,
            operand=substitute_variable(expr.operand, var_name, replacement),
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


class DataflowTransformer:
    """Transforms Structured Control Flow IR into Expression-rich Python AST."""

    def transform_program(self, program: StructuredProgram) -> StructuredProgram:
        """Main entry point: recovers expressions across the entire program."""
        if not program.is_fully_structured:
            return program

        # Pass 1: Convert raw linear InstructionNodes (set, op) into AssignNodes/ExprStmtNodes
        converted_body = self._convert_instructions_in_list(program.body)

        # Pass 2: Dataflow analysis & safe inlining across structured scopes
        optimized_body = self._optimize_scope(converted_body)

        return StructuredProgram(
            body=optimized_body,
            is_fully_structured=program.is_fully_structured,
            unstructured_reasons=program.unstructured_reasons,
            instruction_by_address=getattr(program, "instruction_by_address", {}),
            defined_variables=getattr(program, "defined_variables", None),
        )

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
                        result.append(AssignNode(target=dest, value=expr, source_addresses=[instr.address]))
                        continue

                    # B.2: Unary not (bitwise)
                    if op_name == "not":
                        result.append(AssignNode(target=dest, value=UnaryExpr("~", a_expr), source_addresses=[instr.address]))
                        continue

                    # B.3: Python min and max calls: dest = min(a, b) or max(a, b)
                    if op_name in ("min", "max") and len(args) >= 4:
                        result.append(
                            AssignNode(
                                target=dest,
                                value=CallExpr(op_name, [a_expr, b_expr]),
                                source_addresses=[instr.address],
                            )
                        )
                        continue

                    # B.4: General logic operation call: op("max", a, b) or op("rand", a)
                    call_args = [ConstantExpr(op_name), a_expr]
                    if len(args) > 3 and op_name not in UNARY_LOGIC_OPS:
                        call_args.append(b_expr)
                    result.append(AssignNode(target=dest, value=CallExpr("op", call_args), source_addresses=[instr.address]))
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
                if not is_compiler_temporary(target):
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

                # Criteria 4: No intervening statements modify any variable in val.variables_used
                val_vars = val.variables_used
                intervening_overwrite = False
                for k in range(i + 1, use_idx):
                    if get_node_defs(current_nodes[k]) & val_vars:
                        intervening_overwrite = True
                        break

                if intervening_overwrite:
                    continue

                # ALL SAFETY CHECKS PASSED: Safely inline target with val!
                target_node = current_nodes[use_idx]
                merged_addrs = sorted(
                    set(getattr(target_node, "source_addresses", []))
                    | set(getattr(stmt, "source_addresses", []))
                )

                if isinstance(target_node, AssignNode):
                    new_val = substitute_variable(target_node.value, target, val)
                    current_nodes[use_idx] = AssignNode(
                        target=target_node.target,
                        value=new_val,
                        source_addresses=merged_addrs,
                    )
                    current_nodes.pop(i)
                    changed = True
                    break

                elif isinstance(target_node, ExprStmtNode):
                    new_expr = substitute_variable(target_node.expr, target, val)
                    current_nodes[use_idx] = ExprStmtNode(
                        expr=new_expr,
                        source_addresses=merged_addrs,
                    )
                    current_nodes.pop(i)
                    changed = True
                    break

                elif isinstance(target_node, IfNode) and target_node.condition_expr is not None:
                    new_cond = substitute_variable(target_node.condition_expr, target, val)
                    target_node.condition_expr = new_cond
                    target_node.source_addresses = merged_addrs
                    current_nodes.pop(i)
                    changed = True
                    break

                elif isinstance(target_node, WhileNode) and target_node.condition_expr is not None:
                    new_cond = substitute_variable(target_node.condition_expr, target, val)
                    target_node.condition_expr = new_cond
                    target_node.source_addresses = merged_addrs
                    current_nodes.pop(i)
                    changed = True
                    break

                elif isinstance(target_node, ReturnNode) and target_node.value is not None:
                    new_val = substitute_variable(target_node.value, target, val)
                    target_node.value = new_val
                    target_node.source_addresses = merged_addrs
                    current_nodes.pop(i)
                    changed = True
                    break

                elif isinstance(target_node, CallNode):
                    new_args = [substitute_variable(a, target, val) for a in target_node.args]
                    target_node.args = new_args
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
