"""Example: Using Legacy Array for static memory cell and bank allocation in mlog-py.

Note:
    This demonstrates the backward-compatible Legacy Array API (`from mlog import Array`).
    It packs multiple contiguous arrays into shared hardware memory cells or banks.
    For the new Unified Array API (with register-backed LocalArray requiring zero
    memory cells on map, and dedicated BlockArray), see `beta_local_array.py` and
    `beta_block_array.py` (`from mlog.beta import Array`).
"""

from mlog import Array

# Statically allocate non-overlapping arrays on cell1 (capacity 64)
# buffer_a gets offsets 0..9 (size 10, default dtype=int)
# buffer_b gets offsets 10..29 (size 20, default dtype=int)
buffer_a = Array("cell1", size=10)
buffer_b = Array("cell1", size=20)

# Float array on cell1 (offsets 30..39, dtype=float)
readings = Array("cell1", size=10, dtype=float)

# Bool array on cell1 (offsets 40..49, dtype=bool)
flags = Array("cell1", size=10, dtype=bool)

# Statically allocate a table on bank1 (capacity 512)
data_bank = Array("bank1", size=100)

# Direct static index assignments
buffer_a[0] = 42
buffer_b[0] = 99
readings[0] = 3.14
flags[0] = True
flags[1] = False

# Iterating and accessing array elements dynamically
for i in range(len(buffer_a)):
    buffer_a[i] = i * 5
    buffer_b[i] = buffer_a[i] + 10
    flags[i] = i > 5

# Store result to memory bank
data_bank[0] = buffer_b[0]
