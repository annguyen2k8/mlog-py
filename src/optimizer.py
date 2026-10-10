"""Optimizer interface and passes for Mindustry Logic IR.

Phase 1 keeps IR optimization disabled (PassThrough) to ensure strict correctness.
Phase 2 provides AST-level constant folding and future optimization passes.
"""

from typing import List
from .ir import IRNode
from .compiler import ConstantFolder, fold_constants

__all__ = [
    "IROptimizer",
    "PassThroughOptimizer",
    "ConstantFolder",
    "fold_constants",
]


class IROptimizer:
    """Base interface for IR optimization passes."""

    def optimize(self, instructions: List[IRNode]) -> List[IRNode]:
        """Perform optimization and return transformed IR instructions."""
        raise NotImplementedError


class PassThroughOptimizer(IROptimizer):
    """Null optimizer for Phase 1 (preserves exact instructions)."""

    def optimize(self, instructions: List[IRNode]) -> List[IRNode]:
        return list(instructions)

