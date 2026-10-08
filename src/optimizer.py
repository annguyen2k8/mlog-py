"""Optimizer interface and stubs for Mindustry Logic IR.

Phase 1 keeps optimization disabled to ensure strict correctness.
Phase 2 can implement concrete passes (constant folding, dead code elimination, etc.).
"""

from typing import List
from .ir import IRNode


class IROptimizer:
    """Base interface for IR optimization passes."""

    def optimize(self, instructions: List[IRNode]) -> List[IRNode]:
        """Perform optimization and return transformed IR instructions."""
        raise NotImplementedError


class PassThroughOptimizer(IROptimizer):
    """Null optimizer for Phase 1 (preserves exact instructions)."""

    def optimize(self, instructions: List[IRNode]) -> List[IRNode]:
        return list(instructions)
