"""Static Memory Allocator for Mindustry Memory Cells and Banks in mlog-py."""

import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .errors import CompileError, SourceLocation


@dataclass
class ArraySymbol:
    """Represents a statically allocated Array on a memory block."""

    name: str
    block: str
    base_offset: int
    size: int
    capacity: int
    dtype: str = "int"
    is_block_array: bool = False


@dataclass
class LocalArraySymbol:
    """Represents a statically allocated in-register LocalArray."""

    name: str
    size: int
    dtype: str = "int"
    default: Optional[Any] = None


class MemoryBlockAllocator:
    """Static memory allocator that manages contiguous non-overlapping array allocations

    per memory block. Each memory block (e.g. 'cell1', 'bank1') has an independent address space.
    Also tracks compile-time in-register LocalArray allocations.
    """

    CELL_CAPACITY = 64
    BANK_CAPACITY = 512
    BLOCK_ARRAY_DTYPES = ("int", "float", "bool", "str", "unit", "block", "any")

    def __init__(self):
        # canonical_block_name -> next available offset on this block
        self.block_offsets: Dict[str, int] = {}
        # array_name -> ArraySymbol
        self.arrays: Dict[str, ArraySymbol] = {}
        # array_name -> LocalArraySymbol
        self.local_arrays: Dict[str, LocalArraySymbol] = {}

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
        dtype: str = "int",
        loc: Optional[SourceLocation] = None,
    ) -> ArraySymbol:
        """Statically allocate a contiguous array region on the given memory block."""
        if name in self.arrays:
            raise CompileError(f"Array '{name}' is already declared", loc)

        if dtype not in ("int", "float", "bool"):
            raise CompileError(
                f"unsupported Array dtype '{dtype}': expected int, float, or bool",
                loc,
            )

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
            dtype=dtype,
        )
        self.arrays[name] = symbol
        return symbol

    def allocate_block(
        self,
        name: str,
        block: str,
        size: int,
        dtype: str = "int",
        loc: Optional[SourceLocation] = None,
    ) -> ArraySymbol:
        """Statically allocate a contiguous array region for a beta.BlockArray on the given memory block."""
        if name in self.arrays or name in self.local_arrays:
            raise CompileError(f"Array '{name}' is already declared", loc)

        if dtype not in self.BLOCK_ARRAY_DTYPES:
            raise CompileError(
                f"unsupported BlockArray dtype '{dtype}': expected one of {', '.join(self.BLOCK_ARRAY_DTYPES)}",
                loc,
            )

        canonical_block = block.lower()
        capacity = self.get_block_capacity(canonical_block)
        if capacity is None:
            raise CompileError(
                f"invalid memory block '{block}': BlockArray only supports memory cells (e.g. 'cell', 'cell1', capacity {self.CELL_CAPACITY}) "
                f"or memory banks (e.g. 'bank', 'bank1', capacity {self.BANK_CAPACITY})",
                loc,
            )

        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise CompileError(
                f"invalid BlockArray size: size must be a positive integer, got {size!r}",
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
            dtype=dtype,
            is_block_array=True,
        )
        self.arrays[name] = symbol
        return symbol

    def get_array(self, name: str) -> Optional[ArraySymbol]:
        """Retrieve ArraySymbol by name, or None if not found."""
        return self.arrays.get(name)

    def is_array(self, name: str) -> bool:
        """Check if a variable name is a registered Array."""
        return name in self.arrays

    def allocate_local(
        self,
        name: str,
        size: int,
        dtype: str = "int",
        default: Optional[Any] = None,
        loc: Optional[SourceLocation] = None,
    ) -> LocalArraySymbol:
        """Statically allocate an in-register LocalArray."""
        if name in self.arrays or name in self.local_arrays:
            raise CompileError(f"Array '{name}' is already declared", loc)

        if dtype not in ("int", "float", "bool", "str", "any"):
            raise CompileError(
                f"unsupported LocalArray dtype '{dtype}': expected int, float, bool, str, or any",
                loc,
            )

        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise CompileError(
                f"invalid LocalArray size: size must be a positive integer, got {size!r}",
                loc,
            )

        if size > 64:
            raise CompileError(
                f"LocalArray size {size} exceeds maximum register capacity (64)",
                loc,
            )

        symbol = LocalArraySymbol(
            name=name,
            size=size,
            dtype=dtype,
            default=default,
        )
        self.local_arrays[name] = symbol
        return symbol

    def get_local_array(self, name: str) -> Optional[LocalArraySymbol]:
        """Retrieve LocalArraySymbol by name, or None if not found."""
        return self.local_arrays.get(name)

    def is_local_array(self, name: str) -> bool:
        """Check if a variable name is a registered LocalArray."""
        return name in self.local_arrays
