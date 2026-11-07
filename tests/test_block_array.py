"""Unit and integration tests for mlog.beta.BlockArray."""

import unittest

from src.errors import CompileError
from src.beta import BlockArray as PureBlockArray
from src.mlog import compile_py
from src.validator import MlogValidator
from src.mindustry_validator import is_mindustry_available, validate_with_mindustry


class TestPureBlockArray(unittest.TestCase):
    """Tests for the pure Python BlockArray class implementation."""

    def test_basic_construction_and_indexing(self):
        arr = PureBlockArray("cell1", 10)
        self.assertEqual(len(arr), 10)
        self.assertEqual(arr.size, 10)
        self.assertEqual(arr.capacity, 64)
        self.assertEqual(arr.block, "cell1")
        self.assertEqual(arr[0], 0.0)  # Mindustry memory initializes to 0.0

        arr[0] = 42
        arr[9] = 99
        self.assertEqual(arr[0], 42)
        self.assertEqual(arr[9], 99)

    def test_bank_capacity(self):
        arr = PureBlockArray("bank1", 200)
        self.assertEqual(arr.capacity, 512)
        self.assertEqual(arr.size, 200)
        self.assertEqual(arr.block, "bank1")

    def test_bounds_checking(self):
        arr = PureBlockArray("cell1", 5)
        with self.assertRaises(IndexError):
            _ = arr[-1]
        with self.assertRaises(IndexError):
            _ = arr[5]
        with self.assertRaises(IndexError):
            arr[-1] = 10
        with self.assertRaises(IndexError):
            arr[5] = 10

    def test_type_checking_index(self):
        arr = PureBlockArray("cell1", 5)
        with self.assertRaises(TypeError):
            _ = arr["0"]  # type: ignore
        with self.assertRaises(TypeError):
            _ = arr[1.5]  # type: ignore
        with self.assertRaises(TypeError):
            _ = arr[True]  # type: ignore

    def test_invalid_arguments(self):
        with self.assertRaises(ValueError):
            PureBlockArray("", 10)
        with self.assertRaises(ValueError):
            PureBlockArray("vault1", 10)
        with self.assertRaises(ValueError):
            PureBlockArray("cell1", 0)
        with self.assertRaises(ValueError):
            PureBlockArray("cell1", -5)
        with self.assertRaises(ValueError):
            PureBlockArray("cell1", 65)  # exceeds cell capacity (64)
        with self.assertRaises(ValueError):
            PureBlockArray("bank1", 513)  # exceeds bank capacity (512)

    def test_fill_and_iteration(self):
        arr = PureBlockArray("cell1", 4)
        arr.fill(7)
        self.assertEqual(list(arr), [7, 7, 7, 7])


class TestBlockArrayCompiler(unittest.TestCase):
    """Tests for BlockArray compiler integration and MLog code generation."""

    def test_static_read_write_base_offset_zero(self):
        code = """
from mlog.beta import BlockArray
arr = BlockArray("cell1", 10)
arr[0] = 42
arr[1] = 100
x = arr[0]
y = arr[1]
"""
        res = compile_py(code)
        mlog = res.mlog
        MlogValidator.validate(mlog)

        self.assertIn("write 42 cell1 0", mlog)
        self.assertIn("write 100 cell1 1", mlog)
        self.assertIn("read x cell1 0", mlog)
        self.assertIn("read y cell1 1", mlog)

    def test_sub_allocation_multi_array_partitioning(self):
        code = """
from mlog.beta import BlockArray
arr_a = BlockArray("cell1", 10)
arr_b = BlockArray("cell1", 20)
arr_a[0] = 11
arr_b[0] = 22
arr_b[5] = 33
"""
        res = compile_py(code)
        mlog = res.mlog
        MlogValidator.validate(mlog)

        # arr_a is at offset 0..9
        self.assertIn("write 11 cell1 0", mlog)
        # arr_b is at offset 10..29 -> arr_b[0] writes to physical 10
        self.assertIn("write 22 cell1 10", mlog)
        # arr_b[5] writes to physical 10 + 5 = 15
        self.assertIn("write 33 cell1 15", mlog)

    def test_dynamic_indexing_base_offset_zero(self):
        code = """
from mlog.beta import BlockArray
arr = BlockArray("cell1", 32)
i = 5
arr[i] = 99
val = arr[i]
"""
        res = compile_py(code)
        mlog = res.mlog
        MlogValidator.validate(mlog)

        lines = [line.strip() for line in mlog.strip().splitlines()]
        # Dynamic access with base_offset == 0 must emit exactly 1 write and 1 read without op add
        self.assertIn("write 99 cell1 i", lines)
        self.assertIn("read val cell1 i", lines)

    def test_dynamic_indexing_sub_allocation_offset(self):
        code = """
from mlog.beta import BlockArray
dummy = BlockArray("cell1", 10)
arr = BlockArray("cell1", 20)
i = 3
arr[i] = 77
val = arr[i]
"""
        res = compile_py(code)
        mlog = res.mlog
        MlogValidator.validate(mlog)

        # arr has base_offset 10
        # Dynamic write: op add __tmp i 10 -> write 77 cell1 __tmp (exactly 2 instructions)
        self.assertIn("write 77 cell1 __tmp0", mlog)
        self.assertIn("op add __tmp0 i 10", mlog)
        # Dynamic read: op add __tmp i 10 -> read val cell1 __tmp (exactly 2 instructions)
        self.assertIn("op add __tmp1 i 10", mlog)
        self.assertIn("read val cell1 __tmp1", mlog)

    def test_augmented_assignment(self):
        code = """
from mlog.beta import BlockArray
arr = BlockArray("cell1", 10)
arr[0] += 5
i = 2
arr[i] *= 3
"""
        res = compile_py(code)
        mlog = res.mlog
        MlogValidator.validate(mlog)

        self.assertIn("read __tmp0 cell1 0", mlog)
        self.assertIn("op add __tmp1 __tmp0 5", mlog)
        self.assertIn("write __tmp1 cell1 0", mlog)

    def test_metadata_constant_folding(self):
        code = """
from mlog.beta import BlockArray
arr = BlockArray("cell1", 16)
sz = len(arr)
sz2 = arr.size
cap = arr.capacity
blk = arr.block
"""
        res = compile_py(code)
        mlog = res.mlog
        MlogValidator.validate(mlog)

        self.assertIn("set sz 16", mlog)
        self.assertIn("set sz2 16", mlog)
        self.assertIn("set cap 64", mlog)
        self.assertIn("set blk cell1", mlog)

    def test_fill_small_array_unrolled(self):
        code = """
from mlog.beta import BlockArray
arr = BlockArray("cell1", 3)
arr.fill(42)
"""
        res = compile_py(code)
        mlog = res.mlog
        MlogValidator.validate(mlog)

        # Small array (<= 4) unrolls directly into 3 writes
        self.assertIn("write 42 cell1 0", mlog)
        self.assertIn("write 42 cell1 1", mlog)
        self.assertIn("write 42 cell1 2", mlog)
        self.assertNotIn("jump", mlog)

    def test_fill_large_array_loop(self):
        code = """
from mlog.beta import BlockArray
arr = BlockArray("cell1", 20)
arr.fill(99)
"""
        res = compile_py(code)
        mlog = res.mlog
        MlogValidator.validate(mlog)

        # Larger array (> 4) emits a compact loop
        self.assertIn("jump", mlog)
        self.assertIn("write 99 cell1", mlog)


class TestBlockArrayDtypes(unittest.TestCase):
    """Tests for each dtype supported by BlockArray."""

    def test_dtype_int(self):
        code = """
from mlog.beta import BlockArray
arr = BlockArray("cell1", 4, dtype=int)
arr[0] = 10
arr[1] = 20
"""
        res = compile_py(code)
        self.assertIn("write 10 cell1 0", res.mlog)
        self.assertIn("write 20 cell1 1", res.mlog)

        # Rejects float literal to int array
        with self.assertRaises(CompileError) as ctx:
            compile_py('from mlog.beta import BlockArray\narr = BlockArray("cell1", 4, dtype=int)\narr[0] = 3.14\n')
        self.assertIn("only stores integers", str(ctx.exception))

    def test_dtype_float(self):
        code = """
from mlog.beta import BlockArray
arr = BlockArray("cell1", 4, dtype=float)
arr[0] = 3.14159
arr[1] = 10  # int literal allowed in float
"""
        res = compile_py(code)
        self.assertIn("write 3.14159 cell1 0", res.mlog)
        self.assertIn("write 10 cell1 1", res.mlog)

    def test_dtype_bool(self):
        code = """
from mlog.beta import BlockArray
arr = BlockArray("cell1", 4, dtype=bool)
arr[0] = True
arr[1] = False
"""
        res = compile_py(code)
        self.assertIn("write true cell1 0", res.mlog)
        self.assertIn("write false cell1 1", res.mlog)

        # Rejects numeric literal to bool array
        with self.assertRaises(CompileError) as ctx:
            compile_py('from mlog.beta import BlockArray\narr = BlockArray("cell1", 4, dtype=bool)\narr[0] = 1\n')
        self.assertIn("only stores booleans", str(ctx.exception))

    def test_dtype_str(self):
        code = """
from mlog.beta import BlockArray
arr = BlockArray("cell1", 4, dtype=str)
arr[0] = "hello"
arr[1] = "world"
"""
        res = compile_py(code)
        self.assertIn('write "hello" cell1 0', res.mlog)
        self.assertIn('write "world" cell1 1', res.mlog)

        # Rejects numeric literal to str array
        with self.assertRaises(CompileError) as ctx:
            compile_py('from mlog.beta import BlockArray\narr = BlockArray("cell1", 4, dtype=str)\narr[0] = 123\n')
        self.assertIn("only stores strings", str(ctx.exception))

    def test_dtype_unit_and_block(self):
        code = """
from mlog.beta import BlockArray
units = BlockArray("cell1", 4, dtype="unit")
units[0] = "@flare"
blocks = BlockArray("cell1", 4, dtype="block")
blocks[0] = "@router"
"""
        res = compile_py(code)
        self.assertIn('write "@flare" cell1 0', res.mlog)
        self.assertIn('write "@router" cell1 4', res.mlog)

    def test_dtype_any(self):
        code = """
from mlog.beta import BlockArray
items = BlockArray("cell1", 4, dtype="any")
items[0] = 123
items[1] = 45.67
items[2] = "text"
items[3] = "@flare"
"""
        res = compile_py(code)
        self.assertIn("write 123 cell1 0", res.mlog)
        self.assertIn("write 45.67 cell1 1", res.mlog)
        self.assertIn('write "text" cell1 2', res.mlog)
        self.assertIn('write "@flare" cell1 3', res.mlog)


class TestBlockArrayBoundsAndDiagnostics(unittest.TestCase):
    """Tests for capacity limits, bounds checks, and error diagnostics."""

    def test_out_of_memory_single_array(self):
        # Exceeds cell capacity (64)
        with self.assertRaises(CompileError) as ctx:
            compile_py('from mlog.beta import BlockArray\narr = BlockArray("cell1", 65)\n')
        self.assertIn("out of memory on block 'cell1'", str(ctx.exception))
        self.assertIn("capacity is 64", str(ctx.exception))

    def test_out_of_memory_shared_block(self):
        # Two arrays exceeding capacity 64
        code = """
from mlog.beta import BlockArray
a = BlockArray("cell1", 40)
b = BlockArray("cell1", 30)
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("out of memory on block 'cell1'", str(ctx.exception))
        self.assertIn("requested 30 slots", str(ctx.exception))
        self.assertIn("available: 24", str(ctx.exception))

    def test_reject_negative_static_index(self):
        code = """
from mlog.beta import BlockArray
arr = BlockArray("cell1", 10)
arr[-1] = 5
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("array index out of bounds", str(ctx.exception))
        self.assertIn("outside valid range [0, 10)", str(ctx.exception))

    def test_reject_out_of_bounds_static_index(self):
        code = """
from mlog.beta import BlockArray
arr = BlockArray("cell1", 10)
x = arr[10]
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("array index out of bounds", str(ctx.exception))
        self.assertIn("index 10 is outside valid range [0, 10)", str(ctx.exception))

    def test_reject_unassigned_declaration(self):
        code = """
from mlog.beta import BlockArray
BlockArray("cell1", 10)
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("BlockArray declaration must be assigned to a variable", str(ctx.exception))

    def test_reject_assigning_array_to_variable(self):
        code = """
from mlog.beta import BlockArray
arr = BlockArray("cell1", 10)
b = arr
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("cannot assign BlockArray 'arr' directly to a variable", str(ctx.exception))


class TestRegisterNamespaceSafety(unittest.TestCase):
    """Tests for Requirement A: Register namespace safety."""

    def test_reject_variable_colliding_with_local_array_register(self):
        code = """
from mlog.beta import LocalArray
pos = LocalArray(3)
pos_0 = 100
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("variable name 'pos_0' conflicts with element register of LocalArray 'pos'", str(ctx.exception))

    def test_allow_variable_outside_local_array_range(self):
        code = """
from mlog.beta import LocalArray
pos = LocalArray(2)
pos_2 = 100
pos[0] = 5
"""
        res = compile_py(code)
        self.assertIn("set pos_2 100", res.mlog)
        self.assertIn("set pos_0 5", res.mlog)


class TestMindustryJvmExecution(unittest.TestCase):
    """Tests executing generated BlockArray MLog code on Mindustry v160.7 engine."""

    def test_jvm_multi_array_execution(self):
        if not is_mindustry_available():
            self.skipTest("Mindustry v160.7 engine not available")

        code = """
from mlog.beta import BlockArray
buf1 = BlockArray("cell1", 10, dtype=float)
buf2 = BlockArray("cell1", 20, dtype=float)

buf1[0] = 12.5
buf1[1] = 25.0
buf2[0] = buf1[0] + buf1[1]
val = buf2[0]
"""
        res = compile_py(code)
        valid, msg, count = validate_with_mindustry(res.mlog)
        self.assertTrue(valid, f"Mindustry assembly error: {msg}")

    def test_jvm_dynamic_loop_execution(self):
        if not is_mindustry_available():
            self.skipTest("Mindustry v160.7 engine not available")

        code = """
from mlog.beta import BlockArray
arr = BlockArray("cell1", 16)
for i in range(16):
    arr[i] = i * 3
total = 0
for i in range(16):
    total += arr[i]
"""
        res = compile_py(code)
        valid, msg, count = validate_with_mindustry(res.mlog)
        self.assertTrue(valid, f"Mindustry assembly error: {msg}")


if __name__ == "__main__":
    unittest.main()
