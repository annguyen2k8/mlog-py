"""Static Memory Allocator for Mindustry Memory Cells and Banks in mlog-py."""

import re
from dataclasses import dataclass
from typing import Dict, Optional

from .errors import CompileError, SourceLocation


@dataclass
class ArraySymbol:
    """Represents a statically allocated Array on a memory block."""

    name: str
    block: str
    base_offset: int
    size: int
    capacity: int


class MemoryBlockAllocator:
    """Static memory allocator that manages contiguous non-overlapping array allocations

    per memory block. Each memory block (e.g. 'cell1', 'bank1') has an independent address space.
    """

    CELL_CAPACITY = 64
    BANK_CAPACITY = 512

    def __init__(self):
        # canonical_block_name -> next available offset on this block
        self.block_offsets: Dict[str, int] = {}
        # array_name -> ArraySymbol
        self.arrays: Dict[str, ArraySymbol] = {}

    @classmethod
    def get_block_capacity(cls, block: str) -> Optional[int]:
        """Return the maximum slot capacity for a given memory block name, or None if invalid."""
        b = block.lower()
        if re.match(r"^cell\d*$", b):
            return cls.CELL_CAPACITY
        elif re.match(r"^bank\d*$", b):
            return cls.BANK_CAPACITY
        return None

    def allocate(
        self,
        name: str,
        block: str,
        size: int,
        loc: Optional[SourceLocation] = None,
    ) -> ArraySymbol:
        """Statically allocate a contiguous array region on the given memory block."""
        if name in self.arrays:
            raise CompileError(f"Array '{name}' is already declared", loc)

        canonical_block = block.lower()
        capacity = self.get_block_capacity(canonical_block)
        if capacity is None:
            raise CompileError(
                f"invalid memory block '{block}': Array only supports memory cells (e.g. 'cell', 'cell1', capacity {self.CELL_CAPACITY}) "
                f"or memory banks (e.g. 'bank', 'bank1', capacity {self.BANK_CAPACITY})",
                loc,
            )

        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise CompileError(
                f"invalid Array size: size must be a positive integer, got {size!r}",
                loc,
            )

        current_offset = self.block_offsets.get(canonical_block, 0)
        if current_offset + size > capacity:
            available = max(0, capacity - current_offset)
            raise CompileError(
                f"out of memory on block '{canonical_block}': requested {size} slots (starting at offset {current_offset}), "
                f"but capacity is {capacity} (available: {available})",
                loc,
            )

        base_offset = current_offset
        self.block_offsets[canonical_block] = current_offset + size
        symbol = ArraySymbol(
            name=name,
            block=canonical_block,
            base_offset=base_offset,
            size=size,
            capacity=capacity,
        )
        self.arrays[name] = symbol
        return symbol

    def get_array(self, name: str) -> Optional[ArraySymbol]:
        """Retrieve ArraySymbol by name, or None if not found."""
        return self.arrays.get(name)

    def is_array(self, name: str) -> bool:
        """Check if a variable name is a registered Array."""
        return name in self.arrays
