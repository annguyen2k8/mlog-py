"""Control Flow Graph (CFG) Reconstruction for Mindustry Logic (mlog).

Partitions linear mlog instructions into Basic Blocks according to formal leader
rules (entry point, jump targets, instructions immediately following jumps and
terminal instructions), and establishes directed control-flow edges.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from .instruction import MlogInstruction
from .parser import parse_mlog


class EdgeType(Enum):
    """Classification of directed control flow graph edges."""
    FALLTHROUGH = "fallthrough"
    COND_JUMP_TRUE = "cond_jump_true"
    UNCOND_JUMP = "uncond_jump"


@dataclass
class CFGEdge:
    """A directed edge between two basic blocks in the CFG."""
    source: "BasicBlock"
    target: "BasicBlock"
    edge_type: EdgeType
    condition: Optional[str] = None
    operands: Optional[Tuple[str, str]] = None

    @property
    def is_back_edge(self) -> bool:
        """True if target block address is less than or equal to source block address (loop back-edge)."""
        return self.target.start_address <= self.source.start_address

    @property
    def is_forward_edge(self) -> bool:
        """True if target block address is strictly greater than source block address."""
        return self.target.start_address > self.source.start_address

    @property
    def is_self_loop(self) -> bool:
        """True if edge targets the same basic block."""
        return self.target.id == self.source.id

    def __str__(self) -> str:
        cond_str = f" [{self.condition}]" if self.condition else ""
        return f"{self.source.name} -> {self.target.name} ({self.edge_type.value}{cond_str})"


@dataclass
class BasicBlock:
    """A linear sequence of instructions with single entry and single exit."""
    id: int
    name: str
    start_address: int
    end_address: int
    instructions: List[MlogInstruction] = field(default_factory=list)
    successors: List["BasicBlock"] = field(default_factory=list)
    predecessors: List["BasicBlock"] = field(default_factory=list)
    outgoing_edges: List[CFGEdge] = field(default_factory=list)
    incoming_edges: List[CFGEdge] = field(default_factory=list)

    @property
    def is_entry(self) -> bool:
        """True if this is the program entry block (starts at address 0)."""
        return self.start_address == 0

    @property
    def last_instruction(self) -> Optional[MlogInstruction]:
        """Last instruction in this block, which determines the block exit behavior."""
        return self.instructions[-1] if self.instructions else None

    @property
    def is_terminal(self) -> bool:
        """True if the block terminates with an instruction that never falls through."""
        last = self.last_instruction
        return last.is_terminal if last else False

    @property
    def has_jump(self) -> bool:
        """True if block ends with a jump instruction."""
        last = self.last_instruction
        return last.is_jump if last else False

    @property
    def jump_target(self) -> Optional[int]:
        """Jump destination address if block ends with a jump, else None."""
        last = self.last_instruction
        return last.jump_target if (last and last.is_jump) else None

    @property
    def fallthrough_block(self) -> Optional["BasicBlock"]:
        """Successor block reached via fallthrough (condition false or normal sequence)."""
        for edge in self.outgoing_edges:
            if edge.edge_type == EdgeType.FALLTHROUGH:
                return edge.target
        return None

    @property
    def jump_target_block(self) -> Optional["BasicBlock"]:
        """Successor block reached via jump branch (conditional true or unconditional)."""
        for edge in self.outgoing_edges:
            if edge.edge_type in (EdgeType.COND_JUMP_TRUE, EdgeType.UNCOND_JUMP):
                return edge.target
        return None

    def __str__(self) -> str:
        return f"{self.name} [{self.start_address}..{self.end_address}] ({len(self.instructions)} instrs)"

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BasicBlock):
            return False
        return self.id == other.id


class ControlFlowGraph:
    """Directed Control Flow Graph representing the program structure."""

    def __init__(
        self,
        blocks: List[BasicBlock],
        instructions: List[MlogInstruction],
        edges: List[CFGEdge],
    ):
        self.blocks = blocks
        self.instructions = instructions
        self.edges = edges
        self.entry_block: Optional[BasicBlock] = blocks[0] if blocks else None

        self.block_by_id: Dict[int, BasicBlock] = {b.id: b for b in blocks}
        self.block_by_address: Dict[int, BasicBlock] = {}
        for b in blocks:
            for instr in b.instructions:
                self.block_by_address[instr.address] = b

    def get_block_at(self, address: int) -> Optional[BasicBlock]:
        """Find the basic block containing the instruction at address."""
        return self.block_by_address.get(address)

    def get_block_by_start(self, start_address: int) -> Optional[BasicBlock]:
        """Find the basic block starting at start_address."""
        for b in self.blocks:
            if b.start_address == start_address:
                return b
        return None

    def get_jump_targets(self) -> Set[int]:
        """Return all instruction addresses targeted by jumps in this CFG."""
        targets: Set[int] = set()
        for instr in self.instructions:
            if instr.is_jump and instr.jump_target is not None:
                targets.add(instr.jump_target)
        return targets

    def get_back_edges(self) -> List[CFGEdge]:
        """Return all back-edges (loop feedback edges) in the CFG."""
        return [e for e in self.edges if e.is_back_edge]

    def get_forward_edges(self) -> List[CFGEdge]:
        """Return all forward edges in the CFG."""
        return [e for e in self.edges if e.is_forward_edge]

    def get_terminal_blocks(self) -> List[BasicBlock]:
        """Return all basic blocks ending with terminal instructions or having no successors."""
        return [b for b in self.blocks if b.is_terminal or len(b.successors) == 0]

    def get_unreachable_blocks(self) -> List[BasicBlock]:
        """Return basic blocks that cannot be reached from the entry block (dead code)."""
        if not self.entry_block:
            return []
        visited: Set[int] = set()
        queue = [self.entry_block]
        while queue:
            curr = queue.pop(0)
            if curr.id not in visited:
                visited.add(curr.id)
                for succ in curr.successors:
                    if succ.id not in visited:
                        queue.append(succ)
        return [b for b in self.blocks if b.id not in visited]

    def to_dot(self) -> str:
        """Generate a Graphviz DOT representation of the CFG for visualization and debugging."""
        lines = ["digraph CFG {", '    node [shape=box, fontname="Courier"];']
        for b in self.blocks:
            instr_lines = []
            for instr in b.instructions:
                args_str = " " + " ".join(instr.args) if instr.args else ""
                instr_lines.append(f"{instr.address}: {instr.opcode}{args_str}")
            label = f"{b.name} [{b.start_address}..{b.end_address}]\\n" + "\\n".join(instr_lines)
            fillcolor = "lightblue" if b.is_entry else ("lightcoral" if b.is_terminal else "white")
            lines.append(f'    {b.name} [label="{label}", style=filled, fillcolor="{fillcolor}"];')

        for edge in self.edges:
            style = "solid"
            color = "black"
            label = ""
            if edge.edge_type == EdgeType.COND_JUMP_TRUE:
                color = "green"
                label = f'label="{edge.condition or "true"}"'
            elif edge.edge_type == EdgeType.FALLTHROUGH:
                color = "blue"
                label = 'label="fallthrough"'
            elif edge.edge_type == EdgeType.UNCOND_JUMP:
                color = "purple"
                label = 'label="always"'
            label_attr = f", {label}" if label else ""
            lines.append(f"    {edge.source.name} -> {edge.target.name} [color={color}, style={style}{label_attr}];")

        lines.append("}")
        return "\n".join(lines)


class CFGBuilder:
    """Builds a ControlFlowGraph from a sequence of MlogInstructions."""

    def build(self, instructions: List[MlogInstruction]) -> ControlFlowGraph:
        """Construct the CFG by identifying basic block leaders and resolving control-flow edges."""
        if not instructions:
            return ControlFlowGraph(blocks=[], instructions=[], edges=[])

        n = len(instructions)

        # -------------------------------------------------------------------
        # Step 1: Identify Basic Block Leaders
        # -------------------------------------------------------------------
        leaders: Set[int] = set()

        # Leader 1: Entry point is instruction 0
        leaders.add(0)

        for addr, instr in enumerate(instructions):
            # Leader 2: Target of any jump
            if instr.is_jump:
                target = instr.jump_target
                assert target is not None
                if 0 <= target < n:
                    leaders.add(target)

                # Leader 3: Instruction immediately following a jump
                if addr + 1 < n:
                    leaders.add(addr + 1)

            # Leader 4: Instruction immediately following a terminal instruction (stop, end)
            elif instr.is_terminal:
                if addr + 1 < n:
                    leaders.add(addr + 1)

        sorted_leaders = sorted(leaders)

        # -------------------------------------------------------------------
        # Step 2: Form Basic Blocks from contiguous leader segments
        # -------------------------------------------------------------------
        blocks: List[BasicBlock] = []
        block_by_start: Dict[int, BasicBlock] = {}

        for i, start_addr in enumerate(sorted_leaders):
            if i + 1 < len(sorted_leaders):
                end_addr = sorted_leaders[i + 1] - 1
            else:
                end_addr = n - 1

            block_instrs = instructions[start_addr : end_addr + 1]
            block = BasicBlock(
                id=i,
                name=f"block_{i}",
                start_address=start_addr,
                end_address=end_addr,
                instructions=block_instrs,
            )
            blocks.append(block)
            block_by_start[start_addr] = block

        # -------------------------------------------------------------------
        # Step 3: Connect Directed Edges
        # -------------------------------------------------------------------
        edges: List[CFGEdge] = []

        def add_edge(
            source: BasicBlock,
            target: BasicBlock,
            edge_type: EdgeType,
            cond: Optional[str] = None,
            ops: Optional[Tuple[str, str]] = None,
        ):
            edge = CFGEdge(
                source=source,
                target=target,
                edge_type=edge_type,
                condition=cond,
                operands=ops,
            )
            edges.append(edge)
            source.outgoing_edges.append(edge)
            target.incoming_edges.append(edge)
            if target not in source.successors:
                source.successors.append(target)
            if source not in target.predecessors:
                target.predecessors.append(source)

        for block in blocks:
            last = block.last_instruction
            if last is None:
                continue

            addr = last.address

            if last.is_unconditional_jump:
                target_addr = last.jump_target
                assert target_addr is not None
                if target_addr in block_by_start:
                    target_block = block_by_start[target_addr]
                    add_edge(block, target_block, EdgeType.UNCOND_JUMP)
                # Jumps targeting >= n represent program exit / yield

            elif last.is_conditional_jump:
                target_addr = last.jump_target
                assert target_addr is not None

                # Branch 1: Condition evaluates to True -> jump target
                if target_addr in block_by_start:
                    target_block = block_by_start[target_addr]
                    add_edge(
                        block,
                        target_block,
                        EdgeType.COND_JUMP_TRUE,
                        cond=last.jump_condition,
                        ops=last.jump_operands,
                    )

                # Branch 2: Condition evaluates to False -> fallthrough to addr + 1
                fallthrough_addr = addr + 1
                if fallthrough_addr in block_by_start:
                    fallthrough_block = block_by_start[fallthrough_addr]
                    add_edge(block, fallthrough_block, EdgeType.FALLTHROUGH)

            elif last.is_terminal:
                # stop or end: No intra-tick fallthrough edge
                pass

            else:
                # Normal instruction: unconditional fallthrough to addr + 1
                fallthrough_addr = addr + 1
                if fallthrough_addr in block_by_start:
                    fallthrough_block = block_by_start[fallthrough_addr]
                    add_edge(block, fallthrough_block, EdgeType.FALLTHROUGH)

        return ControlFlowGraph(
            blocks=blocks,
            instructions=instructions,
            edges=edges,
        )


def build_cfg(mlog_text: str, filename: str = "<stdin>") -> ControlFlowGraph:
    """Parse mlog text and construct its ControlFlowGraph."""
    instructions = parse_mlog(mlog_text, filename=filename)
    return CFGBuilder().build(instructions)
