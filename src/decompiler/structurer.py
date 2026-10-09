"""Structured Control Flow Recovery Engine for Mindustry Logic (mlog).

Recovers high-level structured control flow (if, if/else, elif, while, break, continue)
from ControlFlowGraph without guessing. Fallbacks to UnstructuredNode on irreducible CFG
or unstructured jump patterns to guarantee semantic correctness.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from .cfg import BasicBlock, CFGEdge, ControlFlowGraph, build_cfg
from .dataflow import (
    DataflowTransformer,
    condition_to_expr,
    is_compiler_temporary,
    substitute_variable,
)
from .expression import (
    MLOG_TO_PY_BINARY_OPS,
    BinaryExpr,
    ConstantExpr,
    parse_operand_to_expr,
)
from .semantics import collect_program_defined_variables
from .structured_ir import (
    BreakNode,
    ContinueNode,
    IfNode,
    InstructionNode,
    PassNode,
    StructuredNode,
    StructuredProgram,
    UnstructuredNode,
    WhileNode,
    condition_to_python,
)


@dataclass
class LoopInfo:
    """Metadata describing a detected natural loop."""
    id: int
    header: BasicBlock
    latches: List[BasicBlock]
    blocks: Set[BasicBlock]
    exit_blocks: List[BasicBlock]
    primary_exit: Optional[BasicBlock]
    header_address: int
    exit_address: int
    max_body_address: int


class CFGStructurer:
    """Decompiles a ControlFlowGraph into a StructuredProgram."""

    def __init__(self, cfg: ControlFlowGraph):
        self.cfg = cfg
        self.blocks = sorted(cfg.blocks, key=lambda b: b.start_address)
        self.block_by_address: Dict[int, BasicBlock] = {b.start_address: b for b in self.blocks}
        self.instructions = cfg.instructions
        self.n_instructions = len(cfg.instructions)
        self.defined_variables = collect_program_defined_variables(self.instructions)

        # Analysis caches
        self.dom: Dict[int, Set[int]] = {}
        self.idom: Dict[int, int] = {}
        self.loops: List[LoopInfo] = []
        self.loop_by_header: Dict[int, LoopInfo] = {}
        self.is_reducible = True
        self.unstructured_reasons: List[str] = []

        self._analyze()

    # -----------------------------------------------------------------------
    # Step 1: Dominators & Reducibility Analysis
    # -----------------------------------------------------------------------

    def _analyze(self):
        """Perform dominance and natural loop analysis."""
        if not self.blocks:
            return

        self._compute_dominators()
        self._detect_loops()
        self._check_reducibility()

    def _compute_dominators(self):
        """Compute dominator sets and immediate dominators using iterative dataflow on reachable blocks."""
        unreachable = set(self.cfg.get_unreachable_blocks())
        reachable = [b for b in self.blocks if b not in unreachable]
        if not reachable:
            return

        entry_id = reachable[0].id
        all_reachable_ids = {b.id for b in reachable}

        self.dom = {b.id: set(all_reachable_ids) for b in reachable}
        self.dom[entry_id] = {entry_id}

        changed = True
        while changed:
            changed = False
            for b in reachable:
                if b.id == entry_id:
                    continue
                # Only consider predecessors that are reachable
                preds = [p for p in b.predecessors if p.id in self.dom and p not in unreachable]
                if not preds:
                    new_dom = {b.id}
                else:
                    new_dom = {b.id} | set.intersection(*(self.dom[p.id] for p in preds))
                if new_dom != self.dom[b.id]:
                    self.dom[b.id] = new_dom
                    changed = True

        # Immediate dominators
        for b in reachable:
            if b.id == entry_id:
                continue
            strict_doms = self.dom[b.id] - {b.id}
            if strict_doms:
                # The idom is the strict dominator with maximum dominator set size
                self.idom[b.id] = max(strict_doms, key=lambda d: len(self.dom[d]))

    def _detect_loops(self):
        """Identify all natural loops from back-edges on reachable blocks."""
        unreachable = set(self.cfg.get_unreachable_blocks())
        back_edges: List[CFGEdge] = []
        for edge in self.cfg.edges:
            # Skip edges originating from or targeting dead code
            if edge.source in unreachable or edge.target in unreachable:
                continue

            # An edge is a natural back-edge if the target dominates the source
            if edge.target.id in self.dom.get(edge.source.id, set()):
                back_edges.append(edge)
            elif edge.target.start_address <= edge.source.start_address:
                # Backward jump where target does NOT dominate source -> Irreducible CFG!
                self.is_reducible = False
                self.unstructured_reasons.append(
                    f"Irreducible backward jump from block {edge.source.start_address} "
                    f"to {edge.target.start_address} (target does not dominate source)"
                )

        # Group back-edges by loop header
        loops_by_header_id: Dict[int, List[BasicBlock]] = {}
        for edge in back_edges:
            loops_by_header_id.setdefault(edge.target.id, []).append(edge.source)

        loop_counter = 0
        for header_id, latches in loops_by_header_id.items():
            header_block = self.cfg.block_by_id[header_id]
            # Construct loop body using reverse CFG walk from latches
            loop_nodes: Set[BasicBlock] = {header_block}
            stack = list(latches)
            while stack:
                curr = stack.pop()
                if curr not in loop_nodes:
                    loop_nodes.add(curr)
                    for pred in curr.predecessors:
                        if pred not in loop_nodes:
                            stack.append(pred)

            # Identify exit blocks
            exit_blocks: List[BasicBlock] = []
            for b in loop_nodes:
                for succ in b.successors:
                    if succ not in loop_nodes and succ not in exit_blocks:
                        exit_blocks.append(succ)

            # Determine primary exit and exit address
            primary_exit: Optional[BasicBlock] = None
            last_h = header_block.last_instruction
            if last_h and last_h.is_conditional_jump and last_h.jump_target is not None:
                target_b = self.block_by_address.get(last_h.jump_target)
                if target_b and target_b not in loop_nodes:
                    primary_exit = target_b

            max_body_addr = max(b.end_address for b in loop_nodes)
            if not primary_exit:
                # Natural exit is block immediately following max body address
                next_addr = max_body_addr + 1
                primary_exit = self.block_by_address.get(next_addr)

            exit_addr = primary_exit.start_address if primary_exit else (max_body_addr + 1)

            loop_info = LoopInfo(
                id=loop_counter,
                header=header_block,
                latches=latches,
                blocks=loop_nodes,
                exit_blocks=exit_blocks,
                primary_exit=primary_exit,
                header_address=header_block.start_address,
                exit_address=exit_addr,
                max_body_address=max_body_addr,
            )
            loop_counter += 1
            self.loops.append(loop_info)
            self.loop_by_header[header_block.start_address] = loop_info

        # Sort loops by start address, and for identical start, larger body first (outer before inner)
        self.loops.sort(key=lambda l: (l.header_address, -l.max_body_address))

    def _check_reducibility(self):
        """Check for overlapping non-nested loops or multiple entries."""
        for i, l1 in enumerate(self.loops):
            for l2 in self.loops[i + 1 :]:
                if l1.blocks & l2.blocks:
                    # Overlapping loops: one must be a strict subset of the other
                    if not (l2.blocks.issubset(l1.blocks) or l1.blocks.issubset(l2.blocks)):
                        self.is_reducible = False
                        self.unstructured_reasons.append(
                            f"Irreducible interleaved loops between header {l1.header_address} "
                            f"and header {l2.header_address}"
                        )

    # -----------------------------------------------------------------------
    # Step 2: Recursive Structuring
    # -----------------------------------------------------------------------

    def structure(self, recover_expressions: bool = False) -> StructuredProgram:
        """Structure the entire CFG into a StructuredProgram."""
        if not self.blocks:
            return StructuredProgram(body=[], is_fully_structured=True, defined_variables=self.defined_variables)

        if not self.is_reducible:
            # Irreducible CFG: Do not guess! Emit fallback unstructured program
            return StructuredProgram(
                body=[
                    UnstructuredNode(
                        reason="; ".join(self.unstructured_reasons),
                        instructions=self.instructions,
                        defined_variables=self.defined_variables,
                    )
                ],
                is_fully_structured=False,
                unstructured_reasons=self.unstructured_reasons,
                instruction_by_address={i.address: i for i in self.instructions},
                defined_variables=self.defined_variables,
            )

        try:
            body = self._structure_range(
                start_address=0,
                stop_address=self.n_instructions,
                loop_stack=[],
            )
            has_unstructured = self._has_unstructured_nodes(body)
            prog = StructuredProgram(
                body=body,
                is_fully_structured=not has_unstructured,
                unstructured_reasons=self.unstructured_reasons,
                instruction_by_address={i.address: i for i in self.instructions},
                defined_variables=self.defined_variables,
            )
            # Phase 3: Dataflow and Expression Recovery
            if recover_expressions and prog.is_fully_structured:
                prog = DataflowTransformer().transform_program(prog)
            return prog
        except Exception as e:
            # Fallback gracefully on any structuring ambiguity
            reason = f"Structuring fallback: {str(e)}"
            return StructuredProgram(
                body=[
                    UnstructuredNode(
                        reason=reason,
                        instructions=self.instructions,
                        defined_variables=self.defined_variables,
                    )
                ],
                is_fully_structured=False,
                unstructured_reasons=[reason],
                instruction_by_address={i.address: i for i in self.instructions},
                defined_variables=self.defined_variables,
            )

    def _has_unstructured_nodes(self, nodes: List[StructuredNode]) -> bool:
        """Return True if any node in the AST is an UnstructuredNode."""
        for n in nodes:
            if isinstance(n, UnstructuredNode):
                return True
            if isinstance(n, IfNode):
                if self._has_unstructured_nodes(n.then_body) or self._has_unstructured_nodes(n.else_body):
                    return True
            elif isinstance(n, WhileNode):
                if self._has_unstructured_nodes(n.body):
                    return True
        return False

    def _structure_range(
        self,
        start_address: int,
        stop_address: int,
        loop_stack: List[LoopInfo],
    ) -> List[StructuredNode]:
        """Structure instructions in [start_address, stop_address)."""
        nodes: List[StructuredNode] = []
        curr_addr = start_address

        while curr_addr < stop_address:
            # Boundary check
            if curr_addr >= self.n_instructions:
                break

            instr = self.instructions[curr_addr]
            block = self.block_by_address.get(curr_addr)

            # ---------------------------------------------------------------
            # Pattern A: Loop Header
            # ---------------------------------------------------------------
            if curr_addr in self.loop_by_header and not any(l.header_address == curr_addr for l in loop_stack):
                loop = self.loop_by_header[curr_addr]
                # Header condition
                header_instr = loop.header.last_instruction
                has_exit_jump = (
                    header_instr
                    and header_instr.is_conditional_jump
                    and header_instr.jump_target == loop.exit_address
                )

                if has_exit_jump:
                    # Inverted condition: loop executes while NOT (jump_to_exit)
                    cond_str = condition_to_python(
                        header_instr.jump_condition or "always",
                        header_instr.args[2] if len(header_instr.args) > 2 else "0",
                        header_instr.args[3] if len(header_instr.args) > 3 else "0",
                        invert=True,
                    )
                    cond_expr = condition_to_expr(
                        header_instr.jump_condition or "always",
                        header_instr.args[2] if len(header_instr.args) > 2 else "0",
                        header_instr.args[3] if len(header_instr.args) > 3 else "0",
                        invert=True,
                    )
                    # Check for pre-jump instructions inside loop header (e.g. temp calculations for condition)
                    pre_instrs = loop.header.instructions[:-1]
                    unhandled_pre_nodes = []
                    for p_instr in pre_instrs:
                        inlined = False
                        if p_instr.opcode == "op" and len(p_instr.args) >= 3:
                            dest = p_instr.args[1]
                            if dest in cond_expr.variables_used and is_compiler_temporary(dest):
                                op_name = p_instr.args[0]
                                a_expr = parse_operand_to_expr(p_instr.args[2])
                                b_expr = parse_operand_to_expr(p_instr.args[3]) if len(p_instr.args) > 3 else ConstantExpr(0)
                                if op_name in MLOG_TO_PY_BINARY_OPS:
                                    py_op = MLOG_TO_PY_BINARY_OPS[op_name]
                                    sub_expr = BinaryExpr(py_op, a_expr, b_expr)
                                    cond_expr = substitute_variable(cond_expr, dest, sub_expr)
                                    cond_str = cond_expr.to_python()
                                    inlined = True
                        elif p_instr.opcode == "set" and len(p_instr.args) == 2:
                            dest = p_instr.args[0]
                            if dest in cond_expr.variables_used and is_compiler_temporary(dest):
                                src_expr = parse_operand_to_expr(p_instr.args[1])
                                cond_expr = substitute_variable(cond_expr, dest, src_expr)
                                cond_str = cond_expr.to_python()
                                inlined = True
                        if not inlined:
                            unhandled_pre_nodes.append(InstructionNode(p_instr, defined_variables=self.defined_variables))

                    # Loop body starts right after the header block
                    body_start = loop.header.end_address + 1
                else:
                    # Infinite loop (while True:) or loop with condition at latch
                    cond_str = "True"
                    cond_expr = ConstantExpr(True)
                    body_start = curr_addr
                    unhandled_pre_nodes = []

                # Body range: from body_start up to loop.max_body_address + 1
                # The final instruction of the loop is the latch back-edge jump (jump header always)
                # It is excluded from the body statements.
                latch_block = max(loop.latches, key=lambda b: b.end_address)
                body_stop = latch_block.end_address  # excludes latch jump at latch_block.end_address

                body_nodes = self._structure_range(
                    start_address=body_start,
                    stop_address=body_stop,
                    loop_stack=loop_stack + [loop],
                )
                if unhandled_pre_nodes:
                    body_nodes = unhandled_pre_nodes + body_nodes
                if not body_nodes:
                    body_nodes = [PassNode()]

                while_addrs: List[int] = []
                if has_exit_jump and header_instr:
                    while_addrs.append(header_instr.address)
                if hasattr(latch_block, "last_instruction") and latch_block.last_instruction:
                    while_addrs.append(latch_block.last_instruction.address)

                nodes.append(
                    WhileNode(
                        condition_str=cond_str,
                        body=body_nodes,
                        loop_id=loop.id,
                        condition_expr=cond_expr,
                        source_addresses=sorted(set(while_addrs)),
                    )
                )

                # Advance pointer to loop exit
                curr_addr = loop.exit_address
                continue

            # ---------------------------------------------------------------
            # Pattern B: Break & Continue
            # ---------------------------------------------------------------
            if instr.is_unconditional_jump and instr.jump_target is not None:
                target = instr.jump_target

                if loop_stack:
                    innermost_loop = loop_stack[-1]
                    # Continue: targets innermost loop header
                    if target == innermost_loop.header_address:
                        nodes.append(ContinueNode(loop_id=innermost_loop.id, source_addresses=[instr.address]))
                        curr_addr += 1
                        continue

                    # Break: targets innermost loop exit
                    if target == innermost_loop.exit_address:
                        nodes.append(BreakNode(loop_id=innermost_loop.id, source_addresses=[instr.address]))
                        curr_addr += 1
                        continue

                    # Target outer loop? Multi-level break/continue not supported in Python
                    for outer_loop in loop_stack[:-1]:
                        if target in (outer_loop.header_address, outer_loop.exit_address):
                            nodes.append(
                                UnstructuredNode(
                                    reason=f"Multi-level jump to outer loop at address {target}",
                                    instructions=[instr],
                                    defined_variables=self.defined_variables,
                                )
                            )
                            curr_addr += 1
                            continue

                # If jumping to stop_address (merge point of enclosing branch/loop), consume jump
                if target >= stop_address:
                    curr_addr += 1
                    continue

                # Unstructured jump
                nodes.append(
                    UnstructuredNode(
                        reason=f"Unstructured unconditional jump to address {target}",
                        instructions=[instr],
                        defined_variables=self.defined_variables,
                    )
                )
                curr_addr += 1
                continue

            # ---------------------------------------------------------------
            # Pattern C: Conditional Branch (If / If-Else / Elif)
            # ---------------------------------------------------------------
            if instr.is_conditional_jump and instr.jump_target is not None:
                jump_target = instr.jump_target
                fallthrough = curr_addr + 1

                # Backward jump not handled as a loop -> Unstructured
                if jump_target <= curr_addr:
                    nodes.append(
                        UnstructuredNode(
                            reason=f"Unstructured backward conditional jump to address {jump_target}",
                            instructions=[instr],
                            defined_variables=self.defined_variables,
                        )
                    )
                    curr_addr += 1
                    continue

                # C.1: Empty Branch (jump_target == fallthrough)
                if jump_target == fallthrough:
                    cond_str = condition_to_python(
                        instr.jump_condition or "always",
                        instr.args[2] if len(instr.args) > 2 else "0",
                        instr.args[3] if len(instr.args) > 3 else "0",
                        invert=True,
                    )
                    cond_expr = condition_to_expr(
                        instr.jump_condition or "always",
                        instr.args[2] if len(instr.args) > 2 else "0",
                        instr.args[3] if len(instr.args) > 3 else "0",
                        invert=True,
                    )
                    nodes.append(IfNode(condition_str=cond_str, then_body=[PassNode()], else_body=[], condition_expr=cond_expr, source_addresses=[instr.address]))
                    curr_addr = jump_target
                    continue

                # C.2: Normal forward branching (fallthrough is then, jump_target is else or merge)
                cond_str = condition_to_python(
                    instr.jump_condition or "always",
                    instr.args[2] if len(instr.args) > 2 else "0",
                    instr.args[3] if len(instr.args) > 3 else "0",
                    invert=True,
                )
                cond_expr = condition_to_expr(
                    instr.jump_condition or "always",
                    instr.args[2] if len(instr.args) > 2 else "0",
                    instr.args[3] if len(instr.args) > 3 else "0",
                    invert=True,
                )

                # Check if 'then' branch ends with an unconditional jump skipping an 'else' branch:
                # Pattern: [fallthrough .. jump_target - 2], at jump_target - 1: jump M always (M > jump_target)
                last_then_instr = self.instructions[jump_target - 1]
                has_else = (
                    last_then_instr.is_unconditional_jump
                    and last_then_instr.jump_target is not None
                    and last_then_instr.jump_target > jump_target
                )
                if has_else and loop_stack:
                    innermost = loop_stack[-1]
                    # If the jump at jump_target - 1 targets innermost loop exit or header,
                    # it represents a break / continue statement inside the then-body,
                    # not an unconditional jump skipping an else branch.
                    if last_then_instr.jump_target in (innermost.exit_address, innermost.header_address):
                        has_else = False

                if has_else:
                    merge_addr = last_then_instr.jump_target
                    then_stop = jump_target - 1  # exclude the skip-else jump

                    then_body = self._structure_range(
                        start_address=fallthrough,
                        stop_address=then_stop,
                        loop_stack=loop_stack,
                    )
                    if not then_body:
                        then_body = [PassNode()]

                    else_body = self._structure_range(
                        start_address=jump_target,
                        stop_address=merge_addr,
                        loop_stack=loop_stack,
                    )
                    if not else_body:
                        else_body = [PassNode()]

                    # Check if else_body starts with an IfNode that shares merge_addr -> mark as elif
                    if len(else_body) == 1 and isinstance(else_body[0], IfNode):
                        else_body[0].is_elif = True

                    nodes.append(
                        IfNode(
                            condition_str=cond_str,
                            then_body=then_body,
                            else_body=else_body,
                            condition_expr=cond_expr,
                            source_addresses=sorted(set([instr.address, last_then_instr.address])),
                        )
                    )
                    curr_addr = merge_addr
                    continue

                else:
                    # Simple if without else: merge point is jump_target
                    then_body = self._structure_range(
                        start_address=fallthrough,
                        stop_address=jump_target,
                        loop_stack=loop_stack,
                    )
                    if not then_body:
                        then_body = [PassNode()]

                    nodes.append(
                        IfNode(
                            condition_str=cond_str,
                            then_body=then_body,
                            else_body=[],
                            condition_expr=cond_expr,
                            source_addresses=[instr.address],
                        )
                    )
                    curr_addr = jump_target
                    continue

            # ---------------------------------------------------------------
            # Pattern D: Linear Instruction (set, op, wait, stop, end, etc.)
            # ---------------------------------------------------------------
            nodes.append(InstructionNode(instruction=instr, defined_variables=self.defined_variables))
            curr_addr += 1

        return nodes


def structure_cfg(cfg: ControlFlowGraph, recover_expressions: bool = False) -> StructuredProgram:
    """Structure a ControlFlowGraph into a StructuredProgram."""
    return CFGStructurer(cfg).structure(recover_expressions=recover_expressions)


def decompile_to_structured(
    mlog_text: str,
    filename: str = "<stdin>",
    recover_expressions: bool = False,
) -> StructuredProgram:
    """Convenience pipeline: parse mlog -> build CFG -> structure control flow."""
    cfg = build_cfg(mlog_text, filename=filename)
    return structure_cfg(cfg, recover_expressions=recover_expressions)


def recover_expressions(program: StructuredProgram) -> StructuredProgram:
    """Run Phase 3 dataflow analysis and expression recovery on a StructuredProgram."""
    return DataflowTransformer().transform_program(program)
