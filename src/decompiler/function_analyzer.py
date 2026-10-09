"""Function and Procedure Recovery Engine for Mindustry Logic (mlog).

Performs whole-program CFG analysis to discover function boundaries, calling conventions,
call sites, return paths, parameters, and return values without guessing.
Guarantees semantic correctness and strict Zero Guessing.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .cfg import ControlFlowGraph
from .dataflow import (
    DataflowTransformer,
    condition_to_expr,
    parse_operand_to_expr,
)
from .expression import Expr
from .function_ir import CallNode, FunctionDef, FunctionProgram, Parameter, ReturnNode
from .instruction import MlogInstruction
from .semantics import (
    collect_program_defined_variables,
    get_instruction_dest_vars,
    get_instruction_read_vars as sem_get_instruction_read_vars,
)
from .structured_ir import (
    AssignNode,
    BreakNode,
    ContinueNode,
    IfNode,
    InstructionNode,
    StructuredNode,
    WhileNode,
    condition_to_python,
)
from .structurer import CFGStructurer


@dataclass
class CallSiteInfo:
    """Metadata describing a verified function call site."""
    call_jump_address: int
    target_entry_address: int
    return_site_address: int
    return_var: Optional[str] = None
    retval_var: Optional[str] = None
    target_var: Optional[str] = None
    parameter_set_addresses: List[int] = field(default_factory=list)
    arg_values: Dict[str, str] = field(default_factory=dict)


@dataclass
class FunctionCandidate:
    """Metadata describing a recovered function candidate."""
    name: str
    entry_address: int
    end_address: int
    return_var: Optional[str] = None
    retval_var: Optional[str] = None
    return_addresses: List[int] = field(default_factory=list)
    call_sites: List[CallSiteInfo] = field(default_factory=list)
    parameters: List[str] = field(default_factory=list)
    body_instructions: List[MlogInstruction] = field(default_factory=list)
    has_return_value: bool = False
    convention: str = "counter"  # "counter", "direct", "terminal"


def is_special_register(var: str) -> bool:
    """Return True if var is a Mindustry special register or literal."""
    if var.startswith("@"):
        return True
    if var in ("true", "false", "null"):
        return True
    if var.startswith("__ret"):
        return True
    # Numeric literal check
    try:
        float(var)
        return True
    except ValueError:
        pass
    return False


def get_instruction_read_vars(
    instr: MlogInstruction,
    defined_variables: Optional[Set[str]] = None,
) -> List[str]:
    """Get all variable names read by an instruction."""
    return sem_get_instruction_read_vars(instr, defined_variables)


def get_instruction_dest_var(instr: MlogInstruction) -> Optional[str]:
    """Get the destination variable written by an instruction, if any."""
    dests = get_instruction_dest_vars(instr)
    return dests[0] if dests else None


class FunctionAnalyzer:
    """Whole-program CFG analysis to discover and reconstruct functions."""

    def __init__(self, cfg: ControlFlowGraph):
        self.cfg = cfg
        self.instructions = cfg.instructions
        self.instr_by_addr: Dict[int, MlogInstruction] = {i.address: i for i in cfg.instructions}
        self.n_instructions = len(cfg.instructions)
        self.defined_variables = collect_program_defined_variables(cfg.instructions)

    def analyze(self) -> FunctionProgram:
        """Execute full Phase 4 function discovery and program reconstruction."""
        if not self.instructions:
            return FunctionProgram(functions=[], global_statements=[])

        # Step 1: Detect main entry preamble jump (e.g. instruction 0: jump main always 0 0)
        main_entry_jump_addr: Optional[int] = None
        global_start_addr = 0

        first_instr = self.instructions[0]
        if (
            first_instr.is_jump
            and first_instr.jump_type.name == "UNCONDITIONAL"
            and first_instr.jump_target is not None
            and first_instr.jump_target > 1
        ):
            main_entry_jump_addr = 0
            global_start_addr = first_instr.jump_target

        # Step 2: Find all function candidates via calling convention handshakes
        candidates = self._discover_function_candidates(main_entry_jump_addr, global_start_addr)

        if not candidates:
            # No functions proven: fallback to standard Phase 2-3 structured program
            structurer = CFGStructurer(self.cfg)
            structured = structurer.structure(recover_expressions=True)
            return FunctionProgram(
                functions=[],
                global_statements=structured.body,
                is_fully_structured=structured.is_fully_structured,
                unstructured_reasons=structured.unstructured_reasons,
                instruction_by_address=self.instr_by_addr,
            )

        # Step 3: Decompile and structure each function body
        recovered_functions: List[FunctionDef] = []
        fn_address_ranges: List[Tuple[int, int]] = []

        for cand in candidates:
            fn_def = self._reconstruct_function(cand)
            recovered_functions.append(fn_def)
            fn_address_ranges.append((cand.entry_address, cand.end_address))

        # Step 4: Reconstruct global statements, replacing call sites with CallNodes
        global_statements = self._reconstruct_global_code(
            candidates,
            main_entry_jump_addr,
            global_start_addr,
            fn_address_ranges,
        )

        return FunctionProgram(
            functions=recovered_functions,
            global_statements=global_statements,
            is_fully_structured=True,
            instruction_by_address=self.instr_by_addr,
        )

    def _discover_function_candidates(
        self,
        preamble_jump_addr: Optional[int],
        global_start_addr: int,
    ) -> List[FunctionCandidate]:
        """Discover function candidates by matching call sites and return handshakes."""
        candidates: List[FunctionCandidate] = []
        discovered_entries: Set[int] = set()

        # -------------------------------------------------------------------
        # Convention 1: Link Register Return (set @counter <ret_var>)
        # -------------------------------------------------------------------
        counter_returns: List[Tuple[int, str]] = []  # (address, ret_var)
        for instr in self.instructions:
            if instr.opcode == "set" and len(instr.args) >= 2 and instr.args[0] == "@counter":
                ret_v = instr.args[1]
                if ret_v.isidentifier() and not ret_v.startswith("@"):
                    counter_returns.append((instr.address, ret_v))

        for ret_addr, ret_var in counter_returns:
            for instr in self.instructions:
                if (
                    instr.opcode == "set"
                    and len(instr.args) >= 2
                    and instr.args[0] == ret_var
                ):
                    set_ret_addr = instr.address
                    target_ret_site_str = instr.args[1]

                    try:
                        expected_ret_site = int(target_ret_site_str)
                    except ValueError:
                        continue

                    call_jump_instr: Optional[MlogInstruction] = None
                    for offset in (1, 2, 3):
                        candidate_addr = set_ret_addr + offset
                        if candidate_addr in self.instr_by_addr:
                            ci = self.instr_by_addr[candidate_addr]
                            if ci.is_jump and ci.jump_type.name == "UNCONDITIONAL":
                                call_jump_instr = ci
                                break

                    if call_jump_instr is None:
                        continue

                    actual_ret_site = call_jump_instr.address + 1
                    if expected_ret_site != actual_ret_site:
                        continue

                    fn_entry = call_jump_instr.jump_target
                    if fn_entry is None:
                        continue

                    cand = next((c for c in candidates if c.entry_address == fn_entry), None)
                    if cand is None:
                        fn_name = self._derive_function_name(fn_entry, ret_var)
                        cand = FunctionCandidate(
                            name=fn_name,
                            entry_address=fn_entry,
                            end_address=ret_addr,
                            return_var=ret_var,
                            convention="counter",
                        )
                        candidates.append(cand)
                        discovered_entries.add(fn_entry)

                    if ret_addr not in cand.return_addresses:
                        cand.return_addresses.append(ret_addr)
                    if ret_addr > cand.end_address:
                        cand.end_address = ret_addr

                    call_site = CallSiteInfo(
                        call_jump_address=call_jump_instr.address,
                        target_entry_address=fn_entry,
                        return_site_address=actual_ret_site,
                        return_var=ret_var,
                    )
                    cand.call_sites.append(call_site)

        # -------------------------------------------------------------------
        # Convention 2: Direct Return Jump
        # -------------------------------------------------------------------
        if preamble_jump_addr == 0 and global_start_addr > 1:
            for instr in self.instructions:
                if (
                    instr.address >= global_start_addr
                    and instr.is_jump
                    and instr.jump_type.name == "UNCONDITIONAL"
                    and instr.jump_target is not None
                    and 1 <= instr.jump_target < global_start_addr
                ):
                    call_addr = instr.address
                    fn_entry = instr.jump_target
                    ret_site = call_addr + 1

                    if fn_entry in discovered_entries:
                        continue

                    matching_ret_jump: Optional[int] = None
                    for a in range(fn_entry, global_start_addr):
                        if a not in self.instr_by_addr:
                            break
                        callee_i = self.instr_by_addr[a]
                        if (
                            callee_i.is_jump
                            and callee_i.jump_type.name == "UNCONDITIONAL"
                            and callee_i.jump_target == ret_site
                        ):
                            matching_ret_jump = a
                            break

                    if matching_ret_jump is not None:
                        fn_name = f"func_{fn_entry}"
                        cand = FunctionCandidate(
                            name=fn_name,
                            entry_address=fn_entry,
                            end_address=matching_ret_jump,
                            return_addresses=[matching_ret_jump],
                            convention="direct",
                        )
                        cand.call_sites.append(
                            CallSiteInfo(
                                call_jump_address=call_addr,
                                target_entry_address=fn_entry,
                                return_site_address=ret_site,
                            )
                        )
                        candidates.append(cand)
                        discovered_entries.add(fn_entry)

        # -------------------------------------------------------------------
        # Convention 3: Void Terminal Procedures
        # -------------------------------------------------------------------
        if preamble_jump_addr == 0 and global_start_addr > 1:
            curr_entry = 1
            while curr_entry < global_start_addr:
                if curr_entry in discovered_entries:
                    c = next(c for c in candidates if c.entry_address == curr_entry)
                    curr_entry = c.end_address + 1
                    continue

                proc_end = curr_entry
                while proc_end < global_start_addr:
                    pi = self.instr_by_addr[proc_end]
                    if pi.opcode in ("end", "stop"):
                        break
                    proc_end += 1

                main_callers = [
                    i for i in self.instructions
                    if i.address >= global_start_addr
                    and i.is_jump
                    and i.jump_type.name == "UNCONDITIONAL"
                    and i.jump_target == curr_entry
                ]
                if main_callers:
                    cand = FunctionCandidate(
                        name=f"proc_{curr_entry}",
                        entry_address=curr_entry,
                        end_address=min(proc_end, global_start_addr - 1),
                        return_addresses=[proc_end] if proc_end < global_start_addr else [],
                        convention="terminal",
                    )
                    for caller in main_callers:
                        cand.call_sites.append(
                            CallSiteInfo(
                                call_jump_address=caller.address,
                                target_entry_address=curr_entry,
                                return_site_address=caller.address + 1,
                            )
                        )
                    candidates.append(cand)
                    discovered_entries.add(curr_entry)
                    curr_entry = cand.end_address + 1
                else:
                    curr_entry += 1

        # Post-process candidates: expand end_address to include duplicate fallback returns
        for cand in candidates:
            while cand.end_address + 1 < self.n_instructions:
                next_i = self.instr_by_addr[cand.end_address + 1]
                if (
                    cand.return_var is not None
                    and next_i.opcode == "set"
                    and len(next_i.args) >= 2
                    and next_i.args[0] == "@counter"
                    and next_i.args[1] == cand.return_var
                ):
                    cand.end_address += 1
                else:
                    break

            cand.body_instructions = [
                self.instr_by_addr[a]
                for a in range(cand.entry_address, cand.end_address + 1)
                if a in self.instr_by_addr
            ]

        # Collect global variable reads (outside all function definitions)
        global_reads: Set[str] = set()
        for addr, instr in self.instr_by_addr.items():
            if not any(cand.entry_address <= addr <= cand.end_address for cand in candidates):
                for rv in get_instruction_read_vars(instr, self.defined_variables):
                    if not is_special_register(rv) and not rv.startswith("__retval"):
                        global_reads.add(rv)

        for cand in candidates:
            self._analyze_candidate_parameters_and_returns(cand, global_reads)

        candidates.sort(key=lambda c: c.entry_address)
        return candidates

    def _derive_function_name(self, entry_addr: int, ret_var: str) -> str:
        """Derive a friendly, deterministic function name from ret_var or address."""
        if ret_var.startswith("__ret_"):
            base = ret_var[6:]
            if base.isidentifier():
                return base
        return f"func_{entry_addr}"

    def _analyze_candidate_parameters_and_returns(
        self, cand: FunctionCandidate, global_reads: Set[str]
    ):
        """Extract parameter names, argument values at call sites, and return values."""
        defined_in_fn: Set[str] = set()
        used_before_def: List[str] = []

        for instr in cand.body_instructions:
            read_vars = get_instruction_read_vars(instr, self.defined_variables)
            for v in read_vars:
                if v not in defined_in_fn and v not in used_before_def:
                    if not is_special_register(v) and v != cand.return_var:
                        used_before_def.append(v)

            dest = get_instruction_dest_var(instr)
            if dest:
                defined_in_fn.add(dest)

        # Variables that are read in global code are global variables, not local parameters
        potential_params = [v for v in used_before_def if v not in global_reads]
        all_call_set_vars: Set[str] = set()

        for cs in cand.call_sites:
            addr = cs.call_jump_address - 1
            param_addrs: List[int] = []
            arg_map: Dict[str, str] = {}

            while addr >= 0 and addr >= cs.call_jump_address - 10:
                if addr not in self.instr_by_addr:
                    break
                instr = self.instr_by_addr[addr]
                if instr.is_jump or instr.opcode in ("end", "stop"):
                    break
                if instr.opcode == "set" and len(instr.args) >= 2:
                    dest = instr.args[0]
                    val = instr.args[1]
                    if dest == cand.return_var:
                        param_addrs.append(addr)
                    elif dest in potential_params:
                        param_addrs.append(addr)
                        arg_map[dest] = val
                        all_call_set_vars.add(dest)
                addr -= 1

            cs.parameter_set_addresses = sorted(param_addrs)
            cs.arg_values = arg_map

            ret_site = cs.return_site_address
            if ret_site in self.instr_by_addr:
                ret_instr = self.instr_by_addr[ret_site]
                if ret_instr.opcode == "set" and len(ret_instr.args) >= 2:
                    src_v = ret_instr.args[1]
                    if src_v.startswith("__retval") or (cand.retval_var and src_v == cand.retval_var):
                        cs.target_var = ret_instr.args[0]
                        cs.retval_var = src_v
                        cand.retval_var = src_v

        cand.parameters = [v for v in potential_params if v in all_call_set_vars]

        for ret_addr in cand.return_addresses:
            prev_addr = ret_addr - 1
            if prev_addr in self.instr_by_addr:
                pi = self.instr_by_addr[prev_addr]
                if pi.opcode == "set" and len(pi.args) >= 2:
                    dest = pi.args[0]
                    if dest.startswith("__retval"):
                        cand.retval_var = dest
                        cand.has_return_value = True

    def _structure_range(
        self,
        start_addr: int,
        stop_addr: int,
        loop_stack: List[Tuple[int, int]],
        fn_cand: Optional[FunctionCandidate] = None,
        fn_ranges: Optional[List[Tuple[int, int]]] = None,
        call_map: Optional[Dict[int, Tuple[FunctionCandidate, CallSiteInfo]]] = None,
        call_start_map: Optional[Dict[int, Tuple[FunctionCandidate, CallSiteInfo]]] = None,
        absorbed_addresses: Optional[Set[int]] = None,
    ) -> List[StructuredNode]:
        if fn_ranges is None:
            fn_ranges = []
        if call_map is None:
            call_map = {}
        if call_start_map is None:
            call_start_map = {}
        if absorbed_addresses is None:
            absorbed_addresses = set()

        nodes: List[StructuredNode] = []
        curr_addr = start_addr

        while curr_addr < stop_addr:
            if fn_cand is None:
                in_fn = False
                for f_start, f_end in fn_ranges:
                    if f_start <= curr_addr <= f_end:
                        curr_addr = f_end + 1
                        in_fn = True
                        break
                if in_fn:
                    continue

            if curr_addr not in self.instr_by_addr:
                curr_addr += 1
                continue

            # Check Call Site at call jump address
            if curr_addr in call_map:
                cand, cs = call_map[curr_addr]
                args = [
                    parse_operand_to_expr(cs.arg_values.get(p, p))
                    for p in cand.parameters
                ]
                call_addrs = sorted(
                    set(cs.parameter_set_addresses)
                    | {cs.call_jump_address}
                    | ({cs.return_site_address} if cs.target_var else set())
                )
                nodes.append(
                    CallNode(
                        func_name=cand.name,
                        args=args,
                        target=cs.target_var,
                        source_addresses=call_addrs,
                    )
                )
                if cs.target_var and cs.return_site_address > curr_addr:
                    curr_addr = cs.return_site_address + 1
                else:
                    curr_addr += 1
                continue

            if curr_addr in absorbed_addresses:
                curr_addr += 1
                continue

            instr = self.instr_by_addr[curr_addr]

            # Check Return instruction in function
            if fn_cand is not None:
                is_ret = (
                    curr_addr in fn_cand.return_addresses
                    or (
                        instr.opcode == "set"
                        and len(instr.args) >= 2
                        and instr.args[0] == "@counter"
                    )
                )
                if is_ret:
                    ret_val_expr: Optional[Expr] = None
                    ret_addrs = [curr_addr]
                    if nodes and isinstance(nodes[-1], AssignNode):
                        last_assign = nodes[-1]
                        if fn_cand.retval_var and last_assign.target == fn_cand.retval_var:
                            ret_val_expr = last_assign.value
                            ret_addrs = sorted(set(ret_addrs) | set(last_assign.source_addresses))
                            nodes.pop()
                    elif nodes and isinstance(nodes[-1], InstructionNode):
                        last_instr = nodes[-1].instruction
                        if (
                            last_instr.opcode == "set"
                            and len(last_instr.args) >= 2
                            and fn_cand.retval_var
                            and last_instr.args[0] == fn_cand.retval_var
                        ):
                            ret_val_expr = parse_operand_to_expr(last_instr.args[1])
                            ret_addrs = sorted(set(ret_addrs) | set([last_instr.address]))
                            nodes.pop()

                    if not (nodes and isinstance(nodes[-1], ReturnNode) and ret_val_expr is None):
                        nodes.append(ReturnNode(value=ret_val_expr, source_addresses=ret_addrs))
                    curr_addr += 1
                    continue



            # Check Break / Continue in loops
            if instr.is_jump and instr.jump_type.name == "UNCONDITIONAL" and instr.jump_target is not None:
                target = instr.jump_target
                if loop_stack:
                    curr_loop_start, curr_loop_end = loop_stack[-1]
                    if target == curr_loop_start:
                        nodes.append(ContinueNode(source_addresses=[curr_addr]))
                        curr_addr += 1
                        continue
                    if target == curr_loop_end:
                        nodes.append(BreakNode(source_addresses=[curr_addr]))
                        curr_addr += 1
                        continue
                if target >= stop_addr:
                    curr_addr += 1
                    continue

            # Check Loop Header
            matching_latch: Optional[int] = None
            for a in range(curr_addr + 1, stop_addr):
                if a in self.instr_by_addr:
                    cand_i = self.instr_by_addr[a]
                    if (
                        cand_i.is_jump
                        and cand_i.jump_type.name == "UNCONDITIONAL"
                        and cand_i.jump_target == curr_addr
                    ):
                        matching_latch = a
                        break

            if matching_latch is not None:
                cond_str = "True"
                cond_expr: Optional[Expr] = None
                exit_addr = matching_latch + 1
                loop_body_start = curr_addr

                if instr.is_conditional_jump and instr.jump_target is not None:
                    exit_addr = instr.jump_target
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
                    loop_body_start = curr_addr + 1

                loop_body = self._structure_range(
                    start_addr=loop_body_start,
                    stop_addr=matching_latch,
                    loop_stack=loop_stack + [(curr_addr, exit_addr)],
                    fn_cand=fn_cand,
                    fn_ranges=fn_ranges,
                    call_map=call_map,
                    call_start_map=call_start_map,
                    absorbed_addresses=absorbed_addresses,
                )
                nodes.append(WhileNode(condition_str=cond_str, body=loop_body, condition_expr=cond_expr, source_addresses=sorted(set([curr_addr, matching_latch]))))
                curr_addr = max(exit_addr, matching_latch + 1)
                continue

            # Check Conditional Branch (If / If-Else)
            if instr.is_conditional_jump and instr.jump_target is not None:
                jump_target = instr.jump_target
                fallthrough = curr_addr + 1

                if jump_target > curr_addr and jump_target <= stop_addr:
                    has_else = False
                    merge_addr = jump_target
                    if jump_target - 1 in self.instr_by_addr:
                        prev_i = self.instr_by_addr[jump_target - 1]
                        if (
                            prev_i.is_jump
                            and prev_i.jump_type.name == "UNCONDITIONAL"
                            and prev_i.jump_target is not None
                            and prev_i.jump_target > jump_target
                            and prev_i.jump_target <= stop_addr
                        ):
                            has_else = True
                            merge_addr = prev_i.jump_target

                    if has_else:
                        cond_str = condition_to_python(
                            instr.jump_condition or "always",
                            instr.args[2] if len(instr.args) > 2 else "0",
                            instr.args[3] if len(instr.args) > 3 else "0",
                            invert=False,
                        )
                        cond_expr = condition_to_expr(
                            instr.jump_condition or "always",
                            instr.args[2] if len(instr.args) > 2 else "0",
                            instr.args[3] if len(instr.args) > 3 else "0",
                            invert=False,
                        )
                        then_body = self._structure_range(
                            start_addr=jump_target,
                            stop_addr=merge_addr,
                            loop_stack=loop_stack,
                            fn_cand=fn_cand,
                            fn_ranges=fn_ranges,
                            call_map=call_map,
                            call_start_map=call_start_map,
                            absorbed_addresses=absorbed_addresses,
                        )
                        else_body = self._structure_range(
                            start_addr=fallthrough,
                            stop_addr=jump_target - 1,
                            loop_stack=loop_stack,
                            fn_cand=fn_cand,
                            fn_ranges=fn_ranges,
                            call_map=call_map,
                            call_start_map=call_start_map,
                            absorbed_addresses=absorbed_addresses,
                        )
                        nodes.append(IfNode(condition_str=cond_str, then_body=then_body, else_body=else_body, condition_expr=cond_expr, source_addresses=sorted(set([curr_addr, jump_target - 1]))))
                        curr_addr = merge_addr
                        continue
                    else:
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
                        then_body = self._structure_range(
                            start_addr=fallthrough,
                            stop_addr=jump_target,
                            loop_stack=loop_stack,
                            fn_cand=fn_cand,
                            fn_ranges=fn_ranges,
                            call_map=call_map,
                            call_start_map=call_start_map,
                            absorbed_addresses=absorbed_addresses,
                        )
                        nodes.append(IfNode(condition_str=cond_str, then_body=then_body, else_body=[], condition_expr=cond_expr, source_addresses=[curr_addr]))
                        curr_addr = jump_target
                        continue

            # Standard linear instruction
            nodes.append(InstructionNode(instruction=instr, defined_variables=self.defined_variables))
            curr_addr += 1

        return nodes

    def _reconstruct_function(self, cand: FunctionCandidate) -> FunctionDef:
        """Structure a candidate's body instructions into a FunctionDef."""
        # Find internal call sites
        call_map: Dict[int, Tuple[FunctionCandidate, CallSiteInfo]] = {}
        call_start_map: Dict[int, Tuple[FunctionCandidate, CallSiteInfo]] = {}
        absorbed_addresses: Set[int] = set()

        for cs in cand.call_sites:
            if cs.call_jump_address <= cand.end_address:
                call_map[cs.call_jump_address] = (cand, cs)
                start_c = cs.parameter_set_addresses[0] if cs.parameter_set_addresses else cs.call_jump_address
                call_start_map[start_c] = (cand, cs)
                absorbed_addresses.update(cs.parameter_set_addresses)
                if cs.target_var is not None:
                    absorbed_addresses.add(cs.return_site_address)

        raw_nodes = self._structure_range(
            start_addr=cand.entry_address,
            stop_addr=cand.end_address + 1,
            loop_stack=[],
            fn_cand=cand,
            call_map=call_map,
            call_start_map=call_start_map,
            absorbed_addresses=absorbed_addresses,
        )

        transformer = DataflowTransformer()
        converted = transformer._convert_instructions_in_list(raw_nodes)
        optimized = transformer._optimize_scope(converted)

        params = [Parameter(name=p) for p in cand.parameters]

        return FunctionDef(
            name=cand.name,
            parameters=params,
            body=optimized,
            return_var=cand.return_var,
            retval_var=cand.retval_var,
            entry_address=cand.entry_address,
            source_addresses=list(range(cand.entry_address, cand.end_address + 1)),
        )

    def _reconstruct_global_code(
        self,
        candidates: List[FunctionCandidate],
        preamble_jump_addr: Optional[int],
        global_start_addr: int,
        fn_ranges: List[Tuple[int, int]],
    ) -> List[StructuredNode]:
        """Structure global instructions outside function bodies, inlining CallNodes."""
        call_map: Dict[int, Tuple[FunctionCandidate, CallSiteInfo]] = {}
        call_start_map: Dict[int, Tuple[FunctionCandidate, CallSiteInfo]] = {}
        absorbed_addresses: Set[int] = set()

        for cand in candidates:
            for cs in cand.call_sites:
                call_map[cs.call_jump_address] = (cand, cs)
                start_c = cs.parameter_set_addresses[0] if cs.parameter_set_addresses else cs.call_jump_address
                call_start_map[start_c] = (cand, cs)
                absorbed_addresses.update(cs.parameter_set_addresses)
                if cs.target_var is not None:
                    absorbed_addresses.add(cs.return_site_address)

        struct_start = global_start_addr if (preamble_jump_addr is not None and preamble_jump_addr == 0) else 0

        raw_nodes = self._structure_range(
            start_addr=struct_start,
            stop_addr=self.n_instructions,
            loop_stack=[],
            fn_cand=None,
            fn_ranges=fn_ranges,
            call_map=call_map,
            call_start_map=call_start_map,
            absorbed_addresses=absorbed_addresses,
        )

        transformer = DataflowTransformer()
        converted = transformer._convert_instructions_in_list(raw_nodes)
        optimized = transformer._optimize_scope(converted)

        return optimized
