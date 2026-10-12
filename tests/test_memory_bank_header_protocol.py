"""Tests for Memory Bank Header Protocol pattern and static allocation in mlog-py.

Verifies:
- Header protocol layout: slots 0-2 for 3 scalar variables, array allocated sequentially from slot 3 onwards.
- Literal and dynamic index offset resolution (base_offset > 0 adds offset).
- Augmented assignment on offset array elements.
- Capacity enforcement (512 max slots on bank, 64 max slots on cell).
- Multiple non-overlapping arrays on the same memory block.
- Backward compatibility: single arrays without header start at offset 0 with zero-overhead indexing.
- Raw read/write interaction and documentation of allocator bypass risk.
"""

import unittest

from src.mlog import compile_py
from src.errors import CompileError
from src.mindustry_validator import is_mindustry_available, validate_with_mindustry
from src.validator import MlogValidator


class TestMemoryBankHeaderProtocol(unittest.TestCase):
    """Test suite for Memory Bank Header Protocol (3 scalars at slots 0-2, data at 3+)."""

    def test_header_protocol_3_scalars_and_array_layout(self):
        """Header array of size 3 occupies slots 0-2; subsequent data array starts at slot 3."""
        code = """
from mlog import Array

# Header Block (Slots 0..2): 3 scalar variables
header = Array("bank1", size=3, dtype="float")

# Data Block (Slots 3..102): Array of 100 elements
data = Array("bank1", size=100, dtype="float")

# Write scalars
header[0] = 1.0     # slot 0: status / ready flag
header[1] = 100.0   # slot 1: count / length
header[2] = 999.0   # slot 2: timestamp / checksum

# Write array elements at literal indices
data[0] = 42.0      # slot 3 (base_offset 3 + 0)
data[1] = 43.0      # slot 4 (base_offset 3 + 1)
data[99] = 141.0    # slot 102 (base_offset 3 + 99)

# Read scalars and array
s0 = header[0]
s1 = header[1]
s2 = header[2]
d0 = data[0]
d99 = data[99]
"""
        res = compile_py(code)
        mlog = res.mlog

        # Verify literal write addresses
        self.assertIn("write 1.0 bank1 0", mlog)
        self.assertIn("write 100.0 bank1 1", mlog)
        self.assertIn("write 999.0 bank1 2", mlog)
        self.assertIn("write 42.0 bank1 3", mlog)
        self.assertIn("write 43.0 bank1 4", mlog)
        self.assertIn("write 141.0 bank1 102", mlog)

        # Verify literal read addresses
        self.assertIn("read s0 bank1 0", mlog)
        self.assertIn("read s1 bank1 1", mlog)
        self.assertIn("read s2 bank1 2", mlog)
        self.assertIn("read d0 bank1 3", mlog)
        self.assertIn("read d99 bank1 102", mlog)

        MlogValidator.validate(mlog)
        if is_mindustry_available():
            valid, msg, _ = validate_with_mindustry(mlog)
            self.assertTrue(valid, f"Mindustry assembly error: {msg}")

    def test_header_protocol_dynamic_indexing_offsets(self):
        """Dynamic indices on header (base 0) use index directly; data (base 3) adds offset 3."""
        code = """
from mlog import Array

header = Array("bank1", size=3, dtype="float")
data = Array("bank1", size=50, dtype="float")

# Dynamic access on data array (base_offset = 3)
i = 5
data[i] = 77.0
val = data[i]

# Dynamic access on header (base_offset = 0)
k = 1
header[k] = 88.0
h_val = header[k]
"""
        res = compile_py(code)
        lines = res.mlog.splitlines()

        # Dynamic access on data (base 3) must add 3 to index i
        self.assertTrue(any("op add __tmp" in l and "i 3" in l for l in lines))
        # Write to dynamic address
        self.assertTrue(any(l.startswith("write 77.0 bank1 __tmp") for l in lines))
        # Read from dynamic address
        self.assertTrue(any(l.startswith("read val bank1 __tmp") for l in lines))

        # Dynamic access on header (base 0) uses k directly without op add
        self.assertIn("write 88.0 bank1 k", lines)
        self.assertIn("read h_val bank1 k", lines)

        MlogValidator.validate(res.mlog)

    def test_header_protocol_augmented_assignment_offsets(self):
        """Augmented assignments on header and offset data array reuse computed address register."""
        code = """
from mlog import Array

header = Array("bank1", size=3, dtype="float")
data = Array("bank1", size=50, dtype="float")

# Literal augmented assign
header[0] += 10.0   # slot 0
data[0] += 5.0      # slot 3

# Dynamic augmented assign
i = 4
data[i] += 1.0      # slot i + 3
"""
        res = compile_py(code)
        mlog = res.mlog
        lines = mlog.splitlines()

        # Literal header[0] += 10.0 operates on slot 0
        self.assertIn("read __tmp0 bank1 0", mlog)
        self.assertIn("write __tmp1 bank1 0", mlog)

        # Literal data[0] += 5.0 operates on slot 3
        self.assertIn("read __tmp2 bank1 3", mlog)
        self.assertIn("write __tmp3 bank1 3", mlog)

        # Dynamic data[i] += 1.0 evaluates address once with offset 3
        self.assertTrue(any("op add __tmp" in l and "i 3" in l for l in lines))

        MlogValidator.validate(mlog)

    def test_header_protocol_3_distinct_scalar_arrays_layout(self):
        """Pattern 1B: 3 distinct 1-element arrays occupy slots 0, 1, 2; data occupies 3+."""
        code = """
from mlog import Array

status = Array("bank1", size=1, dtype="float")  # slot 0
length = Array("bank1", size=1, dtype="float")  # slot 1
crc    = Array("bank1", size=1, dtype="float")  # slot 2
data   = Array("bank1", size=20, dtype="float") # slots 3..22

status[0] = 1.0
length[0] = 20.0
crc[0] = 555.0

data[0] = 10.0
data[19] = 29.0
"""
        res = compile_py(code)
        mlog = res.mlog

        self.assertIn("write 1.0 bank1 0", mlog)
        self.assertIn("write 20.0 bank1 1", mlog)
        self.assertIn("write 555.0 bank1 2", mlog)
        self.assertIn("write 10.0 bank1 3", mlog)
        self.assertIn("write 29.0 bank1 22", mlog)

        MlogValidator.validate(mlog)

    def test_header_protocol_exact_capacity_boundary(self):
        """Header (size 3) + Data (size 509) = exactly 512 slots (fills bank1 completely)."""
        code = """
from mlog import Array

header = Array("bank1", size=3, dtype="float")
data = Array("bank1", size=509, dtype="float")

header[2] = 3.0       # slot 2
data[0] = 10.0        # slot 3
data[508] = 999.0     # slot 511 (last slot of bank1)
"""
        res = compile_py(code)
        mlog = res.mlog

        self.assertIn("write 3.0 bank1 2", mlog)
        self.assertIn("write 10.0 bank1 3", mlog)
        self.assertIn("write 999.0 bank1 511", mlog)

        MlogValidator.validate(mlog)

    def test_header_protocol_capacity_overflow_rejected(self):
        """Header (size 3) + Data (size 510) = 513 slots > 512 capacity -> CompileError."""
        code = """
from mlog import Array

header = Array("bank1", size=3, dtype="float")
data = Array("bank1", size=510, dtype="float")
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)

        msg = str(ctx.exception)
        self.assertIn("out of memory on block 'bank1'", msg)
        self.assertIn("requested 510 slots (starting at offset 3)", msg)
        self.assertIn("capacity is 512 (available: 509)", msg)

    def test_header_protocol_multiple_arrays_after_header(self):
        """Multiple arrays after header are allocated contiguously without overlapping."""
        code = """
from mlog import Array

header = Array("bank1", size=3, dtype="float")    # slots 0..2
arr1   = Array("bank1", size=50, dtype="float")   # slots 3..52
arr2   = Array("bank1", size=100, dtype="float")  # slots 53..152
arr3   = Array("bank1", size=359, dtype="float")  # slots 153..511

# Total = 3 + 50 + 100 + 359 = 512 slots (exact capacity)
header[0] = 1.0
arr1[0] = 10.0
arr1[49] = 14.9
arr2[0] = 20.0
arr2[99] = 29.9
arr3[0] = 30.0
arr3[358] = 39.9
"""
        res = compile_py(code)
        mlog = res.mlog

        self.assertIn("write 1.0 bank1 0", mlog)
        self.assertIn("write 10.0 bank1 3", mlog)
        self.assertIn("write 14.9 bank1 52", mlog)
        self.assertIn("write 20.0 bank1 53", mlog)
        self.assertIn("write 29.9 bank1 152", mlog)
        self.assertIn("write 30.0 bank1 153", mlog)
        self.assertIn("write 39.9 bank1 511", mlog)

        MlogValidator.validate(mlog)

        # Trying to add even 1 more slot fails
        overflow_code = code + '\narr4 = Array("bank1", size=1, dtype="float")\n'
        with self.assertRaises(CompileError) as ctx:
            compile_py(overflow_code)
        self.assertIn("out of memory on block 'bank1'", str(ctx.exception))

    def test_backward_compatibility_single_array_starts_at_zero(self):
        """Existing programs without header protocol still allocate from offset 0 with zero-overhead indexing."""
        code = """
from mlog import Array

data = Array("bank1", size=100)
i = 5
data[0] = 10
data[i] = 20
val = data[i]
"""
        res = compile_py(code)
        mlog = res.mlog
        lines = mlog.splitlines()

        # Slot 0 directly
        self.assertIn("write 10 bank1 0", mlog)
        # Base offset 0 means NO 'op add ... i 0' instruction
        self.assertFalse(any("op add" in l and " 0" in l for l in lines))
        # Direct dynamic write and read with index i
        self.assertIn("write 20 bank1 i", lines)
        self.assertIn("read val bank1 i", lines)

        MlogValidator.validate(mlog)

    def test_memory_cell_header_protocol_capacity(self):
        """Header protocol on memory cell (capacity 64): 3 header slots + 61 data slots = 64."""
        code = """
from mlog import Array

header = Array("cell1", size=3, dtype="int")
data = Array("cell1", size=61, dtype="int")

header[2] = 3
data[0] = 10
data[60] = 70   # slot 3 + 60 = 63 (last slot of cell1)
"""
        res = compile_py(code)
        mlog = res.mlog

        self.assertIn("write 3 cell1 2", mlog)
        self.assertIn("write 10 cell1 3", mlog)
        self.assertIn("write 70 cell1 63", mlog)

        MlogValidator.validate(mlog)

        # 62 data slots -> 3 + 62 = 65 > 64 -> CompileError
        overflow_code = """
from mlog import Array
header = Array("cell1", size=3, dtype="int")
data = Array("cell1", size=62, dtype="int")
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(overflow_code)
        self.assertIn("out of memory on block 'cell1'", str(ctx.exception))
        self.assertIn("capacity is 64 (available: 61)", str(ctx.exception))

    def test_raw_read_write_interaction_and_allocator_bypass(self):
        """Demonstrates that raw write/read instructions bypass the allocator.

        When raw write(val, block, 0) is called without declaring a header Array,
        the allocator assigns data Array to slot 0, causing a silent collision.
        This verifies why the Header Protocol (declaring header via Array) is essential.
        """
        code = """
from mlog import Array, write, read

# Without declaring header through Array:
data = Array("bank1", size=10, dtype="float")

# Raw write directly writes to slot 0, colliding with data[0]
write(999.0, "bank1", 0)
data[0] = 42.0
"""
        res = compile_py(code)
        mlog = res.mlog

        # Both raw write and data[0] target slot 0 because data started at offset 0
        self.assertIn("write 999.0 bank1 0", mlog)
        self.assertIn("write 42.0 bank1 0", mlog)

        MlogValidator.validate(mlog)


if __name__ == "__main__":
    unittest.main()
