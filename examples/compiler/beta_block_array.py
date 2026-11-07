"""Example: Using hardware memory-backed BlockArray from mlog.beta.

Demonstrates fixed-size arrays backed by physical Mindustry memory blocks
(Memory Cell capacity 64, Memory Bank capacity 512). Elements are accessed
via native O(1) read and write instructions, supporting dynamic loop indexing.

Key Characteristics:
- Backed by a linked hardware block (e.g. "cell1" or "bank1").
- Supports both static indexing (buffer[0]) and dynamic variable indexing (buffer[i]).
- Single block allocation: each BlockArray exclusively maps to one memory block.
- Built-in helper methods such as .fill(value) for fast memory initialization.
"""

from mlog.beta import Array, BlockArray

# Hardware memory bank backed storage (capacity 512, size 16, dtype=int)
# Direct O(1) read/write instructions on bank1
buffer = Array[int]("bank1", 16)

# Initialize buffer with .fill()
buffer.fill(0)

# Static element assignment
buffer[0] = 42
buffer[1] = 99

# Dynamic loop indexing with variable subscript
for i in range(5):
    buffer[i] = i * 5

# In-place element update
buffer[0] += 10
first_val = buffer[0]
