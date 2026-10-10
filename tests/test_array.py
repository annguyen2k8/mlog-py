"""Comprehensive test suite for Array feature in mlog-py.

Covers:
- Static allocation on memory cells (capacity 64) and memory banks (capacity 512)
- Independent address spaces for distinct memory blocks
- Contiguous non-overlapping offsets for multiple arrays sharing a block
- Out of memory detection and capacity enforcement
- Read and write with static literal indices and dynamic indices
- Offset resolution (base_offset addition for secondary arrays)
- Strict validation: non-positive size, float/string sizes, invalid block types
- Static index bounds checking (negative and >= size)
- Integer-only storage enforcement (float/string rejected)
- Prohibition of direct array usage, reassignment, and declarations in loops
- Runtime Array class functionality
- Mindustry real Java engine assembly verification
"""

import unittest

from src.errors import CompileError
from src.metadata import Array
from src.mindustry_validator import is_mindustry_available, validate_with_mindustry
from src.mlog import compile_py
from src.validator import MlogValidator


class TestArrayStaticAllocation(unittest.TestCase):
    """Tests for static memory allocation on cells and banks."""

    def test_single_array_cell(self):
        """Single array on memory cell allocates from offset 0."""
        code = """
from mlog import Array
a = Array("cell1", size=10)
a[0] = 42
"""
        res = compile_py(code)
        self.assertIn("write 42 cell1 0", res.mlog)
        MlogValidator.validate(res.mlog)

    def test_single_array_bank(self):
        """Single array on memory bank allocates from offset 0 up to 512."""
        code = """
from mlog import Array
b = Array("bank1", size=100)
b[0] = 99
b[99] = 100
"""
        res = compile_py(code)
        self.assertIn("write 99 bank1 0", res.mlog)
        self.assertIn("write 100 bank1 99", res.mlog)
        MlogValidator.validate(res.mlog)

    def test_positional_arguments(self):
        """Array supports positional Array(block, size)."""
        code = """
from mlog import Array
a = Array("cell1", 15)
a[0] = 7
"""
        res = compile_py(code)
        self.assertIn("write 7 cell1 0", res.mlog)

    def test_multiple_arrays_same_block_contiguous_offsets(self):
        """Multiple arrays on the same block get contiguous, non-overlapping base offsets."""
        code = """
from mlog import Array
a = Array("cell1", size=10)
b = Array("cell1", size=20)
c = Array("cell1", size=34)

a[0] = 100
a[9] = 109

b[0] = 200
b[19] = 219

c[0] = 300
c[33] = 333
"""
        res = compile_py(code)
        # a is at offset 0..9
        self.assertIn("write 100 cell1 0", res.mlog)
        self.assertIn("write 109 cell1 9", res.mlog)
        # b is at offset 10..29 (base 10)
        self.assertIn("write 200 cell1 10", res.mlog)
        self.assertIn("write 219 cell1 29", res.mlog)
        # c is at offset 30..63 (base 30)
        self.assertIn("write 300 cell1 30", res.mlog)
        self.assertIn("write 333 cell1 63", res.mlog)
        MlogValidator.validate(res.mlog)

    def test_independent_address_spaces_across_blocks(self):
        """Arrays on distinct blocks start at offset 0 independently."""
        code = """
from mlog import Array
cell_a = Array("cell1", size=10)
cell_b = Array("cell2", size=15)
bank_a = Array("bank1", size=50)

cell_a[0] = 1
cell_b[0] = 2
bank_a[0] = 3
"""
        res = compile_py(code)
        self.assertIn("write 1 cell1 0", res.mlog)
        self.assertIn("write 2 cell2 0", res.mlog)
        self.assertIn("write 3 bank1 0", res.mlog)

    def test_cell_exact_capacity_limit(self):
        """Memory cell exactly fills 64 slots."""
        code = """
from mlog import Array
a = Array("cell1", size=40)
b = Array("cell1", size=24)
"""
        res = compile_py(code)
        self.assertEqual(res.mlog.strip(), "")

    def test_bank_exact_capacity_limit(self):
        """Memory bank exactly fills 512 slots."""
        code = """
from mlog import Array
a = Array("bank1", size=300)
b = Array("bank1", size=212)
"""
        res = compile_py(code)
        self.assertEqual(res.mlog.strip(), "")


class TestArrayCapacityErrors(unittest.TestCase):
    """Tests for capacity limits and out of memory error messages."""

    def test_cell_out_of_memory_single(self):
        """Requesting > 64 on cell raises out of memory."""
        code = """
from mlog import Array
a = Array("cell1", size=65)
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("out of memory on block 'cell1'", str(ctx.exception))
        self.assertIn("capacity is 64", str(ctx.exception))

    def test_cell_out_of_memory_multiple(self):
        """Cumulative allocations exceeding 64 on cell raise out of memory."""
        code = """
from mlog import Array
a = Array("cell1", size=40)
b = Array("cell1", size=25)
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("out of memory on block 'cell1'", str(ctx.exception))
        self.assertIn("requested 25 slots", str(ctx.exception))
        self.assertIn("available: 24", str(ctx.exception))

    def test_bank_out_of_memory_single(self):
        """Requesting > 512 on bank raises out of memory."""
        code = """
from mlog import Array
a = Array("bank1", size=513)
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("out of memory on block 'bank1'", str(ctx.exception))
        self.assertIn("capacity is 512", str(ctx.exception))

    def test_bank_out_of_memory_multiple(self):
        """Cumulative allocations exceeding 512 on bank raise out of memory."""
        code = """
from mlog import Array
a = Array("bank1", size=500)
b = Array("bank1", size=15)
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("out of memory on block 'bank1'", str(ctx.exception))
        self.assertIn("requested 15 slots", str(ctx.exception))
        self.assertIn("available: 12", str(ctx.exception))


class TestArrayAccessAndIndexing(unittest.TestCase):
    """Tests for reading and writing array elements."""

    def test_read_literal_index(self):
        """Reading from literal index resolves directly to base_offset + index."""
        code = """
from mlog import Array
a = Array("cell1", size=10)
b = Array("cell1", size=10)
x = a[3]
y = b[4]
"""
        res = compile_py(code)
        self.assertIn("read x cell1 3", res.mlog)
        self.assertIn("read y cell1 14", res.mlog)  # base 10 + 4 = 14

    def test_write_literal_index(self):
        """Writing to literal index resolves directly to base_offset + index."""
        code = """
from mlog import Array
a = Array("cell1", size=10)
b = Array("cell1", size=10)
a[3] = 42
b[4] = 84
"""
        res = compile_py(code)
        self.assertIn("write 42 cell1 3", res.mlog)
        self.assertIn("write 84 cell1 14", res.mlog)  # base 10 + 4 = 14

    def test_dynamic_index_read_and_write(self):
        """Dynamic indices add base_offset only when base_offset > 0."""
        code = """
from mlog import Array
a = Array("cell1", size=10)
b = Array("cell1", size=10)
i = 2
val_a = a[i]
val_b = b[i]
a[i] = val_a + 1
b[i] = val_b + 2
"""
        res = compile_py(code)
        lines = res.mlog.splitlines()
        # a[i] reading: base 0, uses i directly
        self.assertIn("read val_a cell1 i", lines)
        # b[i] reading: base 10, adds 10 to i
        self.assertTrue(any("op add __tmp" in l and "i 10" in l for l in lines))
        # a[i] writing: base 0, uses i directly
        self.assertTrue(any(l.startswith("write ") and l.endswith("cell1 i") for l in lines))

    def test_array_in_binary_expression(self):
        """Array indexing inside complex expression works seamlessly."""
        code = """
from mlog import Array
a = Array("cell1", size=10)
sum_val = a[0] + a[1] * a[2]
"""
        res = compile_py(code)
        self.assertIn("read __tmp0 cell1 0", res.mlog)
        self.assertIn("read __tmp1 cell1 1", res.mlog)
        self.assertIn("read __tmp2 cell1 2", res.mlog)

    def test_array_in_loop_with_len(self):
        """Looping through an array using range(len(a))."""
        code = """
from mlog import Array
a = Array("cell1", size=8)
for i in range(len(a)):
    a[i] = i * 3
"""
        res = compile_py(code)
        self.assertIn("jump 6 greaterThanEq i 8", res.mlog)
        self.assertIn("write __tmp0 cell1 i", res.mlog)

    def test_array_in_condition(self):
        """Array elements can be tested in conditions."""
        code = """
from mlog import Array
a = Array("cell1", size=5)
if a[0] > 100:
    a[1] = 1
"""
        res = compile_py(code)
        self.assertIn("read __tmp0 cell1 0", res.mlog)
        self.assertIn("jump 3 lessThanEq __tmp0 100", res.mlog)


class TestArrayValidationErrors(unittest.TestCase):
    """Tests for compiler error detection and rejection."""

    def test_invalid_block_type(self):
        """Non-cell and non-bank blocks are rejected."""
        code = """
from mlog import Array
a = Array("reactor1", size=10)
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("invalid memory block 'reactor1'", str(ctx.exception))

    def test_zero_size(self):
        """Size 0 is rejected."""
        code = """
from mlog import Array
a = Array("cell1", size=0)
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("positive integer", str(ctx.exception))

    def test_negative_size(self):
        """Negative size is rejected."""
        code = """
from mlog import Array
a = Array("cell1", size=-10)
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("positive integer", str(ctx.exception))

    def test_float_size(self):
        """Float size is rejected."""
        code = """
from mlog import Array
a = Array("cell1", size=10.5)
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("positive integer literal", str(ctx.exception))

    def test_index_out_of_bounds_positive(self):
        """Static index >= size is rejected."""
        code = """
from mlog import Array
a = Array("cell1", size=10)
x = a[10]
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("array index out of bounds", str(ctx.exception))
        self.assertIn("valid range [0, 10)", str(ctx.exception))

    def test_index_out_of_bounds_negative(self):
        """Negative static index is rejected."""
        code = """
from mlog import Array
a = Array("cell1", size=10)
a[-1] = 5
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("array index out of bounds", str(ctx.exception))

    def test_float_element_rejected(self):
        """Array only stores integers; float literal assignment is rejected."""
        code = """
from mlog import Array
a = Array("cell1", size=10)
a[0] = 3.14
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("Array only stores integers", str(ctx.exception))

    def test_string_element_rejected(self):
        """Array only stores integers; string literal assignment is rejected."""
        code = """
from mlog import Array
a = Array("cell1", size=10)
a[0] = "text"
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("Array only stores integers", str(ctx.exception))

    def test_float_index_rejected(self):
        """Float indexing is rejected."""
        code = """
from mlog import Array
a = Array("cell1", size=10)
x = a[1.5]
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("array index must be an integer", str(ctx.exception))

    def test_standalone_array_call_rejected(self):
        """Unassigned Array call is rejected."""
        code = """
from mlog import Array
Array("cell1", size=10)
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("Array declaration must be assigned to a variable", str(ctx.exception))

    def test_array_reassignment_rejected(self):
        """Reassigning an Array variable to a scalar is rejected."""
        code = """
from mlog import Array
a = Array("cell1", size=10)
a = 5
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("cannot reassign Array variable 'a'", str(ctx.exception))

    def test_direct_array_assignment_rejected(self):
        """Assigning an Array object directly to another variable is rejected."""
        code = """
from mlog import Array
a = Array("cell1", size=10)
b = a
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("cannot assign Array 'a' directly", str(ctx.exception))

    def test_array_in_expression_rejected(self):
        """Using Array name directly in an expression is rejected."""
        code = """
from mlog import Array
a = Array("cell1", size=10)
x = a + 1
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("cannot use Array 'a' directly in an expression", str(ctx.exception))

    def test_array_in_loop_rejected(self):
        """Declaring an Array inside a loop is rejected."""
        code = """
from mlog import Array
for i in range(5):
    a = Array("cell1", size=10)
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("not allowed inside loops", str(ctx.exception))

    def test_slice_rejected(self):
        """Slicing an Array is rejected."""
        code = """
from mlog import Array
a = Array("cell1", size=10)
x = a[0:5]
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("slicing is not supported", str(ctx.exception))


class TestRuntimeArray(unittest.TestCase):
    """Tests for Python runtime Array emulation class."""

    def test_runtime_array_operations(self):
        arr = Array("cell1", size=5)
        self.assertEqual(len(arr), 5)
        self.assertEqual(arr.block, "cell1")
        self.assertEqual(arr.size, 5)

        arr[0] = 42
        arr[4] = 99
        self.assertEqual(arr[0], 42)
        self.assertEqual(arr[4], 99)
        self.assertEqual(arr[1], 0)

        with self.assertRaises(IndexError):
            _ = arr[5]

        with self.assertRaises(IndexError):
            arr[-1] = 1

        with self.assertRaises(TypeError):
            arr[0] = 3.14

        with self.assertRaises(TypeError):
            arr[0] = "string"


class TestArrayMindustryHarnessValidation(unittest.TestCase):
    """Tests that compiled array programs pass real Mindustry LAssembler."""

    def test_mindustry_assembly_validation(self):
        if not is_mindustry_available():
            self.skipTest("Mindustry Java harness not available")

        code = """
from mlog import Array
a = Array("cell1", size=10)
b = Array("cell1", size=20)
c = Array("bank1", size=100)

for i in range(len(a)):
    a[i] = i * 2

b[0] = a[0] + 5
b[1] = b[0] * 3
c[50] = b[1]
"""
        res = compile_py(code)
        valid, msg, count = validate_with_mindustry(res.mlog)
        self.assertTrue(valid, f"Mindustry assembly error: {msg}")
        self.assertGreater(count, 0)


class TestArrayAuditRegressions(unittest.TestCase):
    """Regression tests for audit findings on feature/array branch."""

    def test_global_array_in_function(self):
        """Global arrays declared at module level are accessible inside functions (allow_functions=True)."""
        code = """
from mlog import Array

arr = Array("cell1", size=10)

def set_element():
    arr[0] = 42

def read_element():
    return arr[0]

set_element()
val = read_element()
"""
        res = compile_py(code, allow_functions=True)
        self.assertIn("write 42 cell1 0", res.mlog)
        self.assertIn("read __tmp0 cell1 0", res.mlog)
        self.assertIn("set __retval_read_element __tmp0", res.mlog)
        self.assertIn("set val __retval_read_element", res.mlog)
        MlogValidator.validate(res.mlog)

    def test_array_inside_function_rejected(self):
        """Declaring Array inside a function body is rejected with a clear message."""
        code = """
from mlog import Array

def my_func():
    arr = Array("cell1", size=10)
    arr[0] = 1

my_func()
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code, allow_functions=True)
        self.assertIn("not allowed inside functions", str(ctx.exception))

    def test_case_insensitive_block_allocation(self):
        """Memory blocks are case-normalized: cell1 and Cell1 share contiguous space on cell1."""
        code = """
from mlog import Array

a = Array("cell1", size=30)
b = Array("Cell1", size=20)

a[0] = 1
b[0] = 2
"""
        res = compile_py(code)
        self.assertIn("write 1 cell1 0", res.mlog)
        self.assertIn("write 2 cell1 30", res.mlog)
        MlogValidator.validate(res.mlog)

    def test_case_insensitive_capacity_overflow(self):
        """Cumulative size across case variants (cell1 + Cell1) respects the 64 capacity limit."""
        code = """
from mlog import Array

a = Array("cell1", size=40)
b = Array("Cell1", size=30)
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("out of memory on block 'cell1'", str(ctx.exception))
        self.assertIn("requested 30 slots", str(ctx.exception))
        self.assertIn("available: 24", str(ctx.exception))

    def test_bool_element_rejected_compiler(self):
        """Assigning boolean literal to array element is rejected at compile time."""
        code = """
from mlog import Array

a = Array("cell1", size=10)
a[0] = True
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("boolean literal is not supported", str(ctx.exception))

    def test_bool_index_rejected_compiler(self):
        """Indexing with boolean literal is rejected at compile time for both read and write."""
        code_write = """
from mlog import Array

a = Array("cell1", size=10)
a[True] = 5
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code_write)
        self.assertIn("array index must be an integer, got boolean literal", str(ctx.exception))

        code_read = """
from mlog import Array

a = Array("cell1", size=10)
x = a[False]
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code_read)
        self.assertIn("array index must be an integer, got boolean literal", str(ctx.exception))

    def test_bool_rejected_runtime_array(self):
        """Runtime Array class synchronizes with compiler in rejecting boolean index, value, and size."""
        arr = Array("cell1", size=5)

        # Boolean value assignment rejected
        with self.assertRaises(TypeError):
            arr[0] = True

        # Boolean index reading rejected
        with self.assertRaises(TypeError):
            _ = arr[True]

        # Boolean index writing rejected
        with self.assertRaises(TypeError):
            arr[False] = 10

        # Boolean size rejected
        with self.assertRaises(ValueError):
            Array("cell1", True)

    def test_strict_block_naming_conventions(self):
        """Only standard Mindustry cell and bank naming patterns are accepted."""
        # Valid names
        code_valid = """
from mlog import Array

c0 = Array("cell", size=5)
c1 = Array("cell1", size=5)
c2 = Array("cell99", size=5)
b0 = Array("bank", size=10)
b1 = Array("bank1", size=10)
"""
        res = compile_py(code_valid)
        self.assertIsNotNone(res.mlog)

        # Invalid names
        invalid_names = ["cellular", "bankrupt", "cell_1", "bankA", "reactor1", "container1"]
        for bad_name in invalid_names:
            code_bad = f"""
from mlog import Array
a = Array("{bad_name}", size=10)
"""
            with self.assertRaises(CompileError) as ctx:
                compile_py(code_bad)
            self.assertIn(f"invalid memory block '{bad_name}'", str(ctx.exception))

    def test_dynamic_bounds_behavior(self):
        """Dynamic indices compile without static errors and emit unchecked MLog access."""
        code = """
from mlog import Array

a = Array("cell1", size=10)
b = Array("cell1", size=20)
i = 15
a[i] = 100
val = b[i]
"""
        res = compile_py(code)
        # a[i] uses i directly (base 0)
        self.assertIn("write 100 cell1 i", res.mlog)
        # b[i] computes i + 10 (base 10)
        self.assertIn("op add __tmp0 i 10", res.mlog)
        self.assertIn("read val cell1 __tmp0", res.mlog)
        MlogValidator.validate(res.mlog)


class TestFloatArray(unittest.TestCase):
    """Tests for Phase 1: Float Array support in mlog-py."""

    def test_float_array_declaration(self):
        """Float arrays can be declared with dtype=float or positional dtype."""
        code = """
from mlog import Array

a = Array("cell1", size=10, dtype=float)
b = Array("cell1", 15, float)
c = Array("bank1", 20, dtype="float")

a[0] = 3.14
b[0] = -0.001
c[0] = 100.5
"""
        res = compile_py(code)
        self.assertIn("write 3.14 cell1 0", res.mlog)
        self.assertIn("op sub __tmp0 0 0.001", res.mlog)
        self.assertIn("write __tmp0 cell1 10", res.mlog)
        self.assertIn("write 100.5 bank1 0", res.mlog)
        MlogValidator.validate(res.mlog)

    def test_default_dtype_is_int_and_rejects_float(self):
        """Default Array dtype is int, which strictly rejects float literals."""
        code = """
from mlog import Array

a = Array("cell1", size=10)
a[0] = 3.14
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("Array only stores integers; float literal is not supported", str(ctx.exception))

    def test_float_array_accepts_integer_literals(self):
        """Float array can store integer literals (promoted to numeric in MLog)."""
        code = """
from mlog import Array

a = Array("cell1", size=10, dtype=float)
a[0] = 42
"""
        res = compile_py(code)
        self.assertIn("write 42 cell1 0", res.mlog)
        MlogValidator.validate(res.mlog)

    def test_float_array_runtime_expressions(self):
        """Float array stores results of runtime expressions and sensor readings."""
        code = """
from mlog import Array, sensor, SensorProperty

arr = Array("cell1", size=5, dtype=float)
arr[0] = sensor("reactor1", SensorProperty.HEAT)
arr[1] = arr[0] * 1.5 + 0.25
"""
        res = compile_py(code)
        self.assertIn("sensor __tmp0 reactor1 @heat", res.mlog)
        self.assertIn("write __tmp0 cell1 0", res.mlog)
        self.assertIn("read __tmp1 cell1 0", res.mlog)
        self.assertIn("op mul __tmp2 __tmp1 1.5", res.mlog)
        self.assertIn("op add __tmp3 __tmp2 0.25", res.mlog)
        self.assertIn("write __tmp3 cell1 1", res.mlog)
        MlogValidator.validate(res.mlog)

    def test_float_array_reading_and_arithmetic(self):
        """Reading from float array integrates seamlessly in expressions."""
        code = """
from mlog import Array

a = Array("cell1", size=5, dtype=float)
val = a[0] + 2.718
"""
        res = compile_py(code)
        self.assertIn("read __tmp0 cell1 0", res.mlog)
        self.assertIn("op add val __tmp0 2.718", res.mlog)
        MlogValidator.validate(res.mlog)

    def test_float_array_rejects_string_and_bool_literals(self):
        """Float array rejects string and boolean literals."""
        code_str = """
from mlog import Array
a = Array("cell1", size=5, dtype=float)
a[0] = "text"
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code_str)
        self.assertIn("string literal is not supported", str(ctx.exception))

        code_bool = """
from mlog import Array
a = Array("cell1", size=5, dtype=float)
a[0] = True
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code_bool)
        self.assertIn("boolean literal is not supported", str(ctx.exception))

    def test_float_array_rejects_float_index(self):
        """Float array index must still be an integer slot."""
        code = """
from mlog import Array
a = Array("cell1", size=5, dtype=float)
x = a[1.5]
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("array index must be an integer, got float literal", str(ctx.exception))

    def test_invalid_dtype_rejected(self):
        """Unsupported dtypes are rejected at compile time."""
        invalid_dtypes = ["str", "list", "dict", "complex"]
        for bad_dt in invalid_dtypes:
            code = f"""
from mlog import Array
a = Array("cell1", size=5, dtype="{bad_dt}")
"""
            with self.assertRaises(CompileError) as ctx:
                compile_py(code)
            self.assertIn("unsupported Array dtype", str(ctx.exception))

    def test_runtime_float_array(self):
        """Runtime Array emulation class handles float dtype accurately."""
        arr = Array("cell1", size=5, dtype=float)
        self.assertEqual(arr.dtype, float)
        self.assertEqual(arr[0], 0.0)

        # Store float
        arr[0] = 3.14159
        self.assertAlmostEqual(arr[0], 3.14159)

        # Store int (promoted to float)
        arr[1] = 100
        self.assertIsInstance(arr[1], float)
        self.assertEqual(arr[1], 100.0)

        # Reject bool value
        with self.assertRaises(TypeError):
            arr[2] = True

        # Reject str value
        with self.assertRaises(TypeError):
            arr[2] = "invalid"

        # Reject bool index
        with self.assertRaises(TypeError):
            _ = arr[True]

        # Repr contains dtype
        self.assertIn("dtype=float", repr(arr))

    def test_float_array_mindustry_harness(self):
        """Float array bytecode passes real Mindustry LAssembler."""
        if not is_mindustry_available():
            self.skipTest("Mindustry Java harness not available")

        code = """
from mlog import Array, sensor, SensorProperty

readings = Array("cell1", size=10, dtype=float)
readings[0] = sensor("reactor1", SensorProperty.HEAT)
for i in range(5):
    readings[i] = i * 0.25
"""
        res = compile_py(code)
        valid, msg, count = validate_with_mindustry(res.mlog)
        self.assertTrue(valid, f"Mindustry assembly error: {msg}")
        self.assertGreater(count, 0)


class TestBoolArray(unittest.TestCase):
    """Tests for Phase 2: Bool Array (dtype=bool)."""

    def test_bool_array_declaration(self):
        """Array declaration accepts dtype=bool and dtype='bool'."""
        code1 = """
from mlog import Array

flags = Array("cell1", size=10, dtype=bool)
"""
        res1 = compile_py(code1)
        self.assertEqual(res1.mlog.strip(), "")

        code2 = """
from mlog import Array

flags = Array("cell1", size=10, dtype="bool")
"""
        res2 = compile_py(code2)
        self.assertEqual(res2.mlog.strip(), "")

    def test_bool_array_literal_assignment(self):
        """Assigning True/False literals compiles to write true/false opcodes."""
        code = """
from mlog import Array

flags = Array("cell1", size=10, dtype=bool)
flags[0] = True
flags[1] = False
"""
        res = compile_py(code)
        self.assertIn("write true cell1 0", res.mlog)
        self.assertIn("write false cell1 1", res.mlog)
        MlogValidator.validate(res.mlog)

    def test_bool_array_reject_int_literal(self):
        """Assigning integer literals to bool Array is strictly rejected at compile time."""
        for val in ("1", "0", "42", "-1"):
            code = f"""
from mlog import Array

flags = Array("cell1", size=10, dtype=bool)
flags[0] = {val}
"""
            with self.assertRaises(CompileError) as ctx:
                compile_py(code)
            self.assertIn("Array of type 'bool' only stores booleans; integer literal is not supported", str(ctx.exception))

    def test_bool_array_reject_float_literal(self):
        """Assigning float literals to bool Array is rejected at compile time."""
        for val in ("1.0", "0.0", "3.14", "-0.5"):
            code = f"""
from mlog import Array

flags = Array("cell1", size=10, dtype=bool)
flags[0] = {val}
"""
            with self.assertRaises(CompileError) as ctx:
                compile_py(code)
            self.assertIn("Array of type 'bool' only stores booleans; float literal is not supported", str(ctx.exception))

    def test_bool_array_reject_str_literal(self):
        """Assigning string literals to bool Array is rejected at compile time."""
        code = """
from mlog import Array

flags = Array("cell1", size=10, dtype=bool)
flags[0] = "true"
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("Array of type 'bool' only stores booleans; string literal is not supported", str(ctx.exception))

    def test_bool_array_reject_bool_index(self):
        """Indexing a bool Array with a boolean literal is rejected at compile time."""
        code_write = """
from mlog import Array

flags = Array("cell1", size=10, dtype=bool)
flags[True] = True
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code_write)
        self.assertIn("array index must be an integer, got boolean literal", str(ctx.exception))

        code_read = """
from mlog import Array

flags = Array("cell1", size=10, dtype=bool)
x = flags[False]
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code_read)
        self.assertIn("array index must be an integer, got boolean literal", str(ctx.exception))

    def test_bool_array_compare_assignment(self):
        """Assigning comparison expressions stores 0/1 without redundant normalization opcodes."""
        code = """
from mlog import Array

flags = Array("cell1", size=10, dtype=bool)
flags[0] = x > 10
flags[1] = a == b
"""
        res = compile_py(code)
        self.assertIn("op greaterThan", res.mlog)
        self.assertIn("op equal", res.mlog)
        # Should not emit extra notEqual normalization for already-boolean comparisons
        self.assertNotIn("op notEqual", res.mlog)
        self.assertIn("write", res.mlog)
        MlogValidator.validate(res.mlog)

    def test_bool_array_not_assignment(self):
        """Assigning 'not' expressions stores boolean without redundant normalization opcodes."""
        code = """
from mlog import Array

flags = Array("cell1", size=10, dtype=bool)
flags[0] = not is_active
"""
        res = compile_py(code)
        self.assertIn("op equal", res.mlog)
        self.assertNotIn("op notEqual", res.mlog)
        MlogValidator.validate(res.mlog)

    def test_bool_array_dynamic_normalization(self):
        """Assigning general dynamic runtime expressions normalizes value to 0 or 1 via notEqual."""
        code = """
from mlog import Array

flags = Array("cell1", size=10, dtype=bool)
flags[0] = raw_number
"""
        res = compile_py(code)
        self.assertIn("op notEqual", res.mlog)
        self.assertIn("raw_number 0", res.mlog)
        self.assertIn("write", res.mlog)
        MlogValidator.validate(res.mlog)

    def test_bool_array_read_in_condition(self):
        """Reading bool array element directly in if condition."""
        code = """
from mlog import Array, print, printflush

flags = Array("cell1", size=10, dtype=bool)
if flags[0]:
    print("ACTIVE")
    printflush("message1")
"""
        res = compile_py(code)
        self.assertIn("read", res.mlog)
        self.assertIn("jump", res.mlog)
        MlogValidator.validate(res.mlog)

    def test_bool_array_read_to_variable(self):
        """Reading bool array element into a variable."""
        code = """
from mlog import Array

flags = Array("cell1", size=10, dtype=bool)
state = flags[0]
"""
        res = compile_py(code)
        self.assertIn("read state cell1 0", res.mlog)
        MlogValidator.validate(res.mlog)

    def test_runtime_bool_array(self):
        """Runtime Array emulation class handles bool dtype accurately and strictly."""
        arr = Array("cell1", size=5, dtype=bool)
        self.assertEqual(arr.dtype, bool)
        self.assertIs(arr[0], False)

        # Assign True and False
        arr[0] = True
        self.assertIs(arr[0], True)
        arr[1] = False
        self.assertIs(arr[1], False)

        # Reject non-bool types at runtime
        for invalid_val in (1, 0, 42, -1):
            with self.assertRaises(TypeError):
                arr[2] = invalid_val

        for invalid_val in (1.0, 0.0, 3.14):
            with self.assertRaises(TypeError):
                arr[2] = invalid_val

        with self.assertRaises(TypeError):
            arr[2] = "true"

        # Reject boolean index
        with self.assertRaises(TypeError):
            _ = arr[True]

        # Explicit policy: Reading corrupt/foreign non-0/1 values raises ValueError
        arr._data[3] = 42
        with self.assertRaises(ValueError) as ctx:
            _ = arr[3]
        self.assertIn("Invalid boolean encoding in Array: expected 0 or 1, got 42", str(ctx.exception))

        arr._data[3] = -1
        with self.assertRaises(ValueError):
            _ = arr[3]

        # Valid encoded integer 1 and 0 convert to bool True/False
        arr._data[3] = 1
        self.assertIs(arr[3], True)
        arr._data[3] = 0
        self.assertIs(arr[3], False)

        # Repr
        self.assertIn("dtype=bool", repr(arr))

    def test_bool_array_mindustry_harness(self):
        """Bool array bytecode passes real Mindustry LAssembler."""
        if not is_mindustry_available():
            self.skipTest("Mindustry Java harness not available")

        code = """
from mlog import Array, print, printflush

status = Array("cell1", size=10, dtype=bool)
status[0] = True
status[1] = False
for i in range(5):
    status[i] = i > 2

if status[3]:
    print("Unit active")
    printflush("message1")
"""
        res = compile_py(code)
        valid, msg, count = validate_with_mindustry(res.mlog)
        self.assertTrue(valid, f"Mindustry assembly error: {msg}")
        self.assertGreater(count, 0)


if __name__ == "__main__":
    unittest.main()
