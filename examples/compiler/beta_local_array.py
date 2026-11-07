"""Example: Using register-backed LocalArray from mlog.beta.

Demonstrates in-register fixed-size arrays without requiring any memory cell or
memory bank block linked to the processor. Array elements are mapped directly
to processor registers (coords_0, coords_1, etc.) for zero-latency execution.

Key Characteristics:
- Zero hardware memory cell / bank required on the map.
- Fast, zero-overhead register operations (no read/write instructions).
- Static indexing only (coords[0], coords[1]); dynamic indexing (coords[i]) is
  rejected at compile time because processor registers cannot be computed dynamically.
- Size limit: 1 <= size <= 64 elements.
"""

from mlog.beta import Array, LocalArray

# In-register 2D coordinates (size=2, dtype=float) using generic syntax
# Zero memory cell or bank required on the map!
coords = Array[float](2)

# Direct static index assignments
coords[0] = 100.0
coords[1] = 50.0

# In-place augmented assignment on register elements
coords[0] += 25.5

# Direct element reads
x = coords[0]
y = coords[1]

# Constant-folded length and capacity
total = len(coords)
