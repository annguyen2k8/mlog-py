"""Tests for mlog.beta.Array unified constructor, compiler AST dispatch, and runtime dispatcher (P12)."""

import unittest
from typing import Any

from mlog import Array as LegacyArray
from mlog.beta import Array, BlockArray, LocalArray
from src.errors import CompileError
from src.mindustry_validator import is_mindustry_available, validate_with_mindustry
from src.mlog import compile_py
from src.validator import MlogValidator


class TestUnifiedArrayDispatcher(unittest.TestCase):
    """Test suite for mlog.beta.Array factory dispatch and validation."""

    # -----------------------------------------------------------------------
    # 1. LocalArray Dispatch Tests
    # -----------------------------------------------------------------------

    def test_local_array_positional_size(self):
        """Array(size) dispatches to LocalArray."""
        arr = Array(4)
        self.assertIsInstance(arr, LocalArray)
        self.assertEqual(len(arr), 4)
        self.assertEqual(arr.size, 4)
        self.assertEqual(list(arr), [None, None, None, None])

    def test_local_array_keyword_size(self):
        """Array(size=size) dispatches to LocalArray."""
        arr = Array(size=8)
        self.assertIsInstance(arr, LocalArray)
        self.assertEqual(len(arr), 8)
        self.assertEqual(arr.size, 8)

    def test_local_array_with_default(self):
        """Array with default value initializes elements correctly."""
        arr1 = Array(4, default=0)
        self.assertIsInstance(arr1, LocalArray)
        self.assertEqual(list(arr1), [0, 0, 0, 0])

        # Positional default
        arr2 = Array(3, 42)
        self.assertIsInstance(arr2, LocalArray)
        self.assertEqual(list(arr2), [42, 42, 42])

        # Keyword size and default
        arr3 = Array(size=2, default="init")
        self.assertIsInstance(arr3, LocalArray)
        self.assertEqual(list(arr3), ["init", "init"])

    def test_local_array_with_dtype(self):
        """Array with explicit dtype stores dtype metadata."""
        arr1 = Array(4, 0, int)
        self.assertIsInstance(arr1, LocalArray)
        self.assertEqual(arr1.dtype, int)

        arr2 = Array(size=4, dtype=float)
        self.assertIsInstance(arr2, LocalArray)
        self.assertEqual(arr2.dtype, float)

        arr3 = Array(4, dtype="bool")
        self.assertIsInstance(arr3, LocalArray)
        self.assertEqual(arr3.dtype, "bool")

    # -----------------------------------------------------------------------
    # 2. BlockArray Dispatch Tests
    # -----------------------------------------------------------------------

    def test_block_array_positional(self):
        """Array(block, size) dispatches to BlockArray."""
        arr = Array("cell1", 10)
        self.assertIsInstance(arr, BlockArray)
        self.assertEqual(arr.block, "cell1")
        self.assertEqual(arr.size, 10)
        self.assertEqual(arr.capacity, 64)
        self.assertEqual(len(arr), 10)

    def test_block_array_keyword(self):
        """Array(block=..., size=...) dispatches to BlockArray."""
        arr1 = Array(block="cell1", size=16)
        self.assertIsInstance(arr1, BlockArray)
        self.assertEqual(arr1.block, "cell1")
        self.assertEqual(arr1.size, 16)

        arr2 = Array(size=32, block="bank1")
        self.assertIsInstance(arr2, BlockArray)
        self.assertEqual(arr2.block, "bank1")
        self.assertEqual(arr2.size, 32)
        self.assertEqual(arr2.capacity, 512)

        arr3 = Array("cell2", size=20)
        self.assertIsInstance(arr3, BlockArray)
        self.assertEqual(arr3.block, "cell2")
        self.assertEqual(arr3.size, 20)

    def test_block_array_with_dtype(self):
        """Array with block and dtype stores dtype metadata."""
        arr1 = Array("cell1", 10, float)
        self.assertIsInstance(arr1, BlockArray)
        self.assertEqual(arr1.dtype, float)

        arr2 = Array("bank1", 64, dtype="unit")
        self.assertIsInstance(arr2, BlockArray)
        self.assertEqual(arr2.dtype, "unit")

        arr3 = Array(block="cell1", size=8, dtype=int)
        self.assertIsInstance(arr3, BlockArray)
        self.assertEqual(arr3.dtype, int)

    # -----------------------------------------------------------------------
    # 3. Generic Subscript Specialization Tests
    # -----------------------------------------------------------------------

    def test_generic_subscript_local_array(self):
        """Array[T](size) returns LocalArray with dtype T."""
        arr1 = Array[float](4)
        self.assertIsInstance(arr1, LocalArray)
        self.assertEqual(arr1.dtype, float)

        arr2 = Array[int](size=6, default=0)
        self.assertIsInstance(arr2, LocalArray)
        self.assertEqual(arr2.dtype, int)
        self.assertEqual(list(arr2), [0, 0, 0, 0, 0, 0])

    def test_generic_subscript_block_array(self):
        """Array[T](block, size) returns BlockArray with dtype T."""
        arr1 = Array[str]("cell1", 10)
        self.assertIsInstance(arr1, BlockArray)
        self.assertEqual(arr1.dtype, str)

        arr2 = Array[int](block="bank1", size=100)
        self.assertIsInstance(arr2, BlockArray)
        self.assertEqual(arr2.dtype, int)

    # -----------------------------------------------------------------------
    # 4. Input Validation and Error Handling Tests
    # -----------------------------------------------------------------------

    def test_reject_bool_as_size(self):
        """Array strictly rejects bool for size despite bool subclassing int."""
        with self.assertRaises(ValueError):
            Array(True)
        with self.assertRaises(ValueError):
            Array(False)
        with self.assertRaises(ValueError):
            Array(size=True)
        with self.assertRaises(ValueError):
            Array(size=False)
        with self.assertRaises(ValueError):
            Array("cell1", True)
        with self.assertRaises(ValueError):
            Array("cell1", size=False)
        with self.assertRaises(ValueError):
            Array(block="cell1", size=True)

    def test_reject_non_positive_size(self):
        """Array rejects non-positive sizes (<= 0)."""
        for invalid_size in (0, -1, -10):
            with self.subTest(size=invalid_size):
                with self.assertRaises(ValueError):
                    Array(invalid_size)
                with self.assertRaises(ValueError):
                    Array(size=invalid_size)
                with self.assertRaises(ValueError):
                    Array("cell1", invalid_size)
                with self.assertRaises(ValueError):
                    Array(block="cell1", size=invalid_size)

    def test_reject_missing_arguments(self):
        """Array requires size argument."""
        with self.assertRaises(TypeError):
            Array()
        with self.assertRaises(TypeError):
            Array("cell1")
        with self.assertRaises(TypeError):
            Array(block="cell1")
        with self.assertRaises(TypeError):
            Array(dtype=int)

    def test_reject_duplicate_arguments(self):
        """Array rejects duplicate positional and keyword arguments."""
        with self.assertRaises(TypeError):
            Array(4, size=4)
        with self.assertRaises(TypeError):
            Array("cell1", 10, size=10)
        with self.assertRaises(TypeError):
            Array("cell1", 10, block="cell2")
        with self.assertRaises(TypeError):
            Array(4, 0, default=1)
        with self.assertRaises(TypeError):
            Array(4, 0, int, dtype=float)
        with self.assertRaises(TypeError):
            Array("cell1", 10, int, dtype=float)

    def test_reject_invalid_arguments(self):
        """Array rejects unexpected keyword arguments and invalid argument types."""
        with self.assertRaises(TypeError):
            Array(4, unexpected_kw=123)
        with self.assertRaises(TypeError):
            Array("cell1", 10, invalid=True)
        with self.assertRaises(TypeError):
            Array(3.14)
        with self.assertRaises(TypeError):
            Array(["cell1"], 10)
        with self.assertRaises(TypeError):
            Array(4, 0, int, "extra")

    def test_reject_default_for_block_array(self):
        """Array strictly rejects default argument when target is BlockArray."""
        with self.assertRaises(ValueError) as ctx:
            Array("cell1", 10, default=0)
        self.assertIn("default", str(ctx.exception))
        self.assertIn("LocalArray", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx2:
            Array(block="cell1", size=10, default=0)
        self.assertIn("default", str(ctx2.exception))

        with self.assertRaises(ValueError) as ctx3:
            Array("cell1", size=10, default="val")
        self.assertIn("default", str(ctx3.exception))

    def test_reject_capacity_exceeded(self):
        """Array enforces register and memory block capacity bounds."""
        # LocalArray register capacity is 64
        with self.assertRaises(ValueError):
            Array(65)

        # cell capacity is 64
        with self.assertRaises(ValueError):
            Array("cell1", 65)

        # bank capacity is 512
        with self.assertRaises(ValueError):
            Array("bank1", 513)

    def test_local_array_capacity_property(self):
        """LocalArray exposes .capacity equal to .size."""
        arr = Array(4)
        self.assertEqual(arr.capacity, 4)

    def test_local_array_block_attribute_rejected(self):
        """LocalArray has no .block attribute."""
        arr = Array(4)
        with self.assertRaises(AttributeError):
            _ = arr.block

    def test_reject_invalid_dtype(self):
        """Array rejects invalid dtypes for both LocalArray and BlockArray."""
        # Unsupported types
        with self.assertRaises(ValueError):
            Array(4, dtype=complex)
        with self.assertRaises(ValueError):
            Array(4, dtype="invalid")
        with self.assertRaises(ValueError):
            Array("cell1", 10, dtype=complex)
        with self.assertRaises(ValueError):
            Array("cell1", 10, dtype="invalid")
        # Invalid argument type (not type or str)
        with self.assertRaises(TypeError):
            Array(4, dtype=123)
        with self.assertRaises(TypeError):
            Array("cell1", 10, dtype=123)
        # Unit and block are valid for BlockArray, but invalid for LocalArray
        with self.assertRaises(ValueError):
            Array(4, dtype="unit")
        with self.assertRaises(ValueError):
            Array(4, dtype="block")
        # Valid unit, block, and Any for BlockArray
        arr_unit = Array("cell1", 10, dtype="unit")
        self.assertEqual(arr_unit.dtype, "unit")
        arr_block = Array("cell1", 10, dtype="block")
        self.assertEqual(arr_block.dtype, "block")
        arr_any_local = Array(4, dtype=Any)
        self.assertEqual(arr_any_local.dtype, Any)
        arr_any_block = Array("cell1", 10, dtype=Any)
        self.assertEqual(arr_any_block.dtype, Any)

    # -----------------------------------------------------------------------
    # 5. Legacy Array Independence Tests
    # -----------------------------------------------------------------------

    def test_legacy_array_independence(self):
        """Ensure from mlog import Array is completely independent and preserved."""
        self.assertIsNot(LegacyArray, Array)
        self.assertNotEqual(LegacyArray.__module__, Array.__module__)
        self.assertEqual(LegacyArray.__module__, "mlog.metadata")
        self.assertEqual(Array.__module__, "mlog.beta")


class TestUnifiedArrayCompiler(unittest.TestCase):
    """Compiler AST validation, lowering, and code-generation tests for mlog.beta.Array."""

    def check_compile(self, code: str) -> str:
        res = compile_py(code, filename="test_unified_array.py", validate=True)
        MlogValidator.validate(res.mlog)
        return res.mlog

    def test_compile_from_mlog_beta_import_array(self):
        """Array() from mlog.beta dispatches to LocalArray or BlockArray."""
        code = """
from mlog.beta import Array
loc = Array(4)
loc[0] = 10
blk = Array("cell1", 10)
blk[0] = 20
"""
        mlog = self.check_compile(code)
        self.assertIn("set loc_0 10", mlog)
        self.assertIn("write 20 cell1 0", mlog)

    def test_compile_aliased_import(self):
        """from mlog.beta import Array as MyArray works for both backends."""
        code = """
from mlog.beta import Array as MyArray
loc = MyArray(3)
loc[1] = 42
blk = MyArray("cell1", 8)
blk[2] = 99
"""
        mlog = self.check_compile(code)
        self.assertIn("set loc_1 42", mlog)
        self.assertIn("write 99 cell1 2", mlog)

    def test_compile_module_attribute_access(self):
        """import mlog.beta as beta; beta.Array(...) compiles correctly."""
        code = """
import mlog.beta as beta
loc = beta.Array(2)
loc[0] = 5
blk = beta.Array("bank1", 64)
blk[10] = 77
"""
        mlog = self.check_compile(code)
        self.assertIn("set loc_0 5", mlog)
        self.assertIn("write 77 bank1 10", mlog)

    def test_compile_star_import(self):
        """from mlog.beta import * exports Array, LocalArray, BlockArray."""
        code = """
from mlog.beta import *
loc = Array(4)
loc[0] = 123
blk = Array("cell1", 16)
blk[0] = 456
"""
        mlog = self.check_compile(code)
        self.assertIn("set loc_0 123", mlog)
        self.assertIn("write 456 cell1 0", mlog)

    def test_compile_generic_dtype(self):
        """Array[T] generic subscript compiles with typed validation."""
        code = """
from mlog.beta import Array
loc = Array[float](2)
loc[0] = 12.5
blk = Array[int]("cell1", 10)
blk[0] = 42
"""
        mlog = self.check_compile(code)
        self.assertIn("set loc_0 12.5", mlog)
        self.assertIn("write 42 cell1 0", mlog)

    def test_compile_augmented_assignment(self):
        """Augmented assignments (+=) lower correctly on both backends."""
        code = """
from mlog.beta import Array
loc = Array(4, default=10)
loc[0] += 5
blk = Array("cell1", 10)
blk[0] += 2
i = 2
blk[i] += 1
"""
        mlog = self.check_compile(code)
        # LocalArray augmented assignment lowers to IROp
        self.assertIn("op add loc_0 loc_0 5", mlog)
        # BlockArray static augmented assignment lowers to read + op + write
        self.assertIn("read __tmp0 cell1 0", mlog)
        self.assertIn("op add __tmp1 __tmp0 2", mlog)
        self.assertIn("write __tmp1 cell1 0", mlog)
        # BlockArray dynamic augmented assignment lowers to read + op + write
        self.assertIn("read __tmp2 cell1 i", mlog)
        self.assertIn("op add __tmp3 __tmp2 1", mlog)
        self.assertIn("write __tmp3 cell1 i", mlog)

    def test_compile_metadata_constant_folding(self):
        """len(arr), .size, .capacity, .block, .dtype constant-fold with 0 memory instructions."""
        code = """
from mlog.beta import Array
loc = Array(4, dtype=float)
blk = Array("cell1", 16, dtype=int)
l_len = len(loc)
l_sz = loc.size
l_cap = loc.capacity
l_dt = loc.dtype
b_len = len(blk)
b_sz = blk.size
b_cap = blk.capacity
b_blk = blk.block
b_dt = blk.dtype
"""
        mlog = self.check_compile(code)
        self.assertIn("set l_len 4", mlog)
        self.assertIn("set l_sz 4", mlog)
        self.assertIn("set l_cap 4", mlog)
        self.assertIn('set l_dt "float"', mlog)
        self.assertIn("set b_len 16", mlog)
        self.assertIn("set b_sz 16", mlog)
        self.assertIn("set b_cap 64", mlog)
        self.assertIn("set b_blk cell1", mlog)
        self.assertIn('set b_dt "int"', mlog)

    def test_compile_legacy_and_beta_together(self):
        """Legacy Array and beta.Array coexist in the same source without interference."""
        code = """
from mlog import Array as LegacyArray
from mlog.beta import Array as BetaArray

leg = LegacyArray("cell1", 10)
beta_loc = BetaArray(4)
beta_blk = BetaArray("cell1", 10)

leg[0] = 111
beta_loc[0] = 222
beta_blk[0] = 333
"""
        mlog = self.check_compile(code)
        # LegacyArray occupies offset 0..9 on cell1
        self.assertIn("write 111 cell1 0", mlog)
        # Beta LocalArray uses in-register slots
        self.assertIn("set beta_loc_0 222", mlog)
        # Beta BlockArray sub-allocates contiguous offset 10..19 on cell1
        self.assertIn("write 333 cell1 10", mlog)

    def test_compile_fill_method(self):
        """fill() compiles for both LocalArray and BlockArray."""
        code = """
from mlog.beta import Array
loc = Array(3)
loc.fill(7)
blk = Array("cell1", 3)
blk.fill(99)
"""
        mlog = self.check_compile(code)
        self.assertIn("set loc_0 7", mlog)
        self.assertIn("set loc_1 7", mlog)
        self.assertIn("set loc_2 7", mlog)
        self.assertIn("write 99 cell1 0", mlog)
        self.assertIn("write 99 cell1 1", mlog)
        self.assertIn("write 99 cell1 2", mlog)

    def test_compile_dynamic_indexing_on_local_array_rejected(self):
        """Dynamic indexing on LocalArray is strictly rejected with compile error."""
        code = """
from mlog.beta import Array
l = Array(4)
i = 0
x = l[i]
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code, filename="test.py")
        self.assertIn("dynamic index is not supported", str(ctx.exception))

    def test_compile_unassigned_call_rejected(self):
        """Unassigned Array() call raises CompileError."""
        code = """
from mlog.beta import Array
Array(4)
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code, filename="test.py")
        self.assertIn("must be assigned to a variable", str(ctx.exception))

    def test_compile_inside_function_rejected(self):
        """Array declaration inside function is rejected."""
        code = """
from mlog.beta import Array
def foo():
    a = Array(4)
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code, filename="test.py", allow_functions=True)
        self.assertIn("not allowed inside functions", str(ctx.exception))

    def test_compile_inside_loop_rejected(self):
        """Array declaration inside loop is rejected."""
        code = """
from mlog.beta import Array
for i in range(10):
    a = Array(4)
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code, filename="test.py")
        self.assertIn("not allowed inside loops", str(ctx.exception))

    def test_compile_reassignment_rejected(self):
        """Reassigning an Array variable raises CompileError."""
        code = """
from mlog.beta import Array
a = Array(4)
a = Array(4)
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code, filename="test.py")
        self.assertIn("already declared", str(ctx.exception))

    def test_compile_direct_assignment_rejected(self):
        """Direct assignment of array to another variable is rejected."""
        code = """
from mlog.beta import Array
a = Array(4)
b = a
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code, filename="test.py")
        self.assertIn("cannot assign LocalArray", str(ctx.exception))

    def test_compile_default_on_block_array_rejected(self):
        """Passing default to BlockArray raises CompileError."""
        code = """
from mlog.beta import Array
a = Array("cell1", 10, default=0)
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code, filename="test.py")
        self.assertIn("argument 'default' is only supported for in-register LocalArray", str(ctx.exception))

    def test_compile_bool_as_size_rejected(self):
        """Passing bool as size raises CompileError."""
        code1 = """
from mlog.beta import Array
a = Array(True)
"""
        with self.assertRaises(CompileError):
            compile_py(code1, filename="test.py")

        code2 = """
from mlog.beta import Array
a = Array("cell1", True)
"""
        with self.assertRaises(CompileError):
            compile_py(code2, filename="test.py")

    def test_compile_capacity_exceeded_rejected(self):
        """Capacity exceeding bounds raises CompileError."""
        code1 = """
from mlog.beta import Array
a = Array(65)
"""
        with self.assertRaises(CompileError) as ctx1:
            compile_py(code1, filename="test.py")
        self.assertIn("exceeds maximum register capacity", str(ctx1.exception))

        code2 = """
from mlog.beta import Array
a = Array("cell1", 65)
"""
        with self.assertRaises(CompileError) as ctx2:
            compile_py(code2, filename="test.py")
        self.assertIn("out of memory on block 'cell1'", str(ctx2.exception))

    def test_compile_reject_invalid_dtype(self):
        """Compiler rejects invalid dtype specifications."""
        code1 = """
from mlog.beta import Array
a = Array(4, dtype=complex)
"""
        with self.assertRaises(CompileError) as ctx1:
            compile_py(code1, filename="test.py")
        self.assertIn("expected int, float, bool, str, or any", str(ctx1.exception))

        code1_non_type = """
from mlog.beta import Array
a = Array(4, dtype=3.14)
"""
        with self.assertRaises(CompileError) as ctx1b:
            compile_py(code1_non_type, filename="test.py")
        self.assertIn("dtype must be int, float, bool, str, or any", str(ctx1b.exception))

        code2 = """
from mlog.beta import Array
a = Array(4, dtype="unit")
"""
        with self.assertRaises(CompileError) as ctx2:
            compile_py(code2, filename="test.py")
        self.assertIn("unsupported Array dtype 'unit'", str(ctx2.exception))

        code3 = """
from mlog.beta import Array
a = Array("cell1", 10, dtype=complex)
"""
        with self.assertRaises(CompileError) as ctx3:
            compile_py(code3, filename="test.py")
        self.assertIn("expected one of int, float, bool, str, unit, block, any", str(ctx3.exception))

        code3_non_type = """
from mlog.beta import Array
a = Array("cell1", 10, dtype=3.14)
"""
        with self.assertRaises(CompileError) as ctx3b:
            compile_py(code3_non_type, filename="test.py")
        self.assertIn("dtype must be int, float, bool, str, unit, block, or any", str(ctx3b.exception))

        code4 = """
from mlog.beta import Array
a = Array("cell1", 10, dtype="invalid")
"""
        with self.assertRaises(CompileError) as ctx4:
            compile_py(code4, filename="test.py")
        self.assertIn("unsupported Array dtype 'invalid'", str(ctx4.exception))

    def test_compile_reject_block_on_local_array(self):
        """Compiler rejects accessing .block on LocalArray."""
        code = """
from mlog.beta import Array
loc = Array(4)
x = loc.block
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code, filename="test.py")
        self.assertIn("not an Array backed by a block", str(ctx.exception))

    def test_compile_capacity_on_local_array(self):
        """Compiler constant-folds .capacity on LocalArray."""
        code = """
from mlog.beta import Array
loc = Array(4)
c = loc.capacity
"""
        mlog = self.check_compile(code)
        self.assertIn("set c 4", mlog)

    def test_compile_import_shadowing_beta_over_legacy(self):
        """When mlog.beta import comes after mlog import, beta Array takes precedence."""
        code = """
from mlog import Array
from mlog.beta import Array
loc = Array(4)
loc[0] = 10
"""
        mlog = self.check_compile(code)
        self.assertIn("set loc_0 10", mlog)

    def test_compile_import_shadowing_legacy_over_beta(self):
        """When mlog import comes after mlog.beta import, legacy Array takes precedence."""
        code_leg = """
from mlog.beta import Array
from mlog import Array
blk = Array("cell1", 10)
blk[0] = 20
"""
        mlog = self.check_compile(code_leg)
        self.assertIn("write 20 cell1 0", mlog)

        code_beta_rejected = """
from mlog.beta import Array
from mlog import Array
loc = Array(4)
"""
        with self.assertRaises(CompileError):
            compile_py(code_beta_rejected, filename="test.py")

    def test_compile_qualified_module_isolation(self):
        """Qualified access mlog.Array and beta.Array operate independently."""
        code = """
import mlog
import mlog.beta as beta

leg = mlog.Array("cell1", 10)
loc = beta.Array(4)
blk = beta.Array("cell2", 10)

leg[0] = 1
loc[0] = 2
blk[0] = 3
"""
        mlog = self.check_compile(code)
        self.assertIn("write 1 cell1 0", mlog)
        self.assertIn("set loc_0 2", mlog)
        self.assertIn("write 3 cell2 0", mlog)

    def test_compile_wildcard_import_isolation(self):
        """Wildcard imports coexist with explicit aliased imports without interference."""
        code1 = """
from mlog import *
from mlog.beta import Array as BetaArr

leg = Array("cell1", 10)
loc = BetaArr(4)
leg[0] = 10
loc[0] = 20
"""
        mlog1 = self.check_compile(code1)
        self.assertIn("write 10 cell1 0", mlog1)
        self.assertIn("set loc_0 20", mlog1)

        code2 = """
from mlog.beta import *
from mlog import Array as LegArr

loc = Array(4)
leg = LegArr("cell1", 10)
loc[0] = 30
leg[0] = 40
"""
        mlog2 = self.check_compile(code2)
        self.assertIn("set loc_0 30", mlog2)
        self.assertIn("write 40 cell1 0", mlog2)

    def test_compile_standardized_diagnostics(self):
        """Verify standardized diagnostic messages for array call errors."""
        # Duplicate size
        code_dup_size = """
from mlog.beta import Array
a = Array(4, size=4)
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code_dup_size, filename="test.py")
        self.assertIn("duplicate argument 'size' in Array()", str(ctx.exception))

        # Duplicate block
        code_dup_block = """
from mlog.beta import Array
a = Array("cell1", 10, block="cell2")
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code_dup_block, filename="test.py")
        self.assertIn("duplicate argument 'block' in Array()", str(ctx.exception))

        # Missing size on Array()
        code_missing_size = """
from mlog.beta import Array
a = Array()
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code_missing_size, filename="test.py")
        self.assertIn("missing required argument 'size' in Array()", str(ctx.exception))

        # Missing size on Array(block="cell1")
        code_missing_block_size = """
from mlog.beta import Array
a = Array(block="cell1")
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code_missing_block_size, filename="test.py")
        self.assertIn("missing required argument 'size' in Array()", str(ctx.exception))

    def test_jvm_unified_array_execution(self):
        """Verify unified Array compiles and passes Mindustry v160.7 engine verification."""
        if not is_mindustry_available():
            self.skipTest("Mindustry v160.7 engine not available")

        code = """
from mlog.beta import Array
loc = Array(4, default=10)
loc[0] += 5
blk = Array("cell1", 16)
for i in range(16):
    blk[i] = loc[0] * i
"""
        res = compile_py(code)
        valid, msg, count = validate_with_mindustry(res.mlog)
        self.assertTrue(valid, f"Mindustry assembly error: {msg}")

    def test_jvm_legacy_and_beta_coexistence(self):
        """Verify coexistence of LegacyArray and BetaArray on JVM."""
        if not is_mindustry_available():
            self.skipTest("Mindustry v160.7 engine not available")

        code = """
from mlog import Array as LegacyArray
from mlog.beta import Array as BetaArray

leg = LegacyArray("cell1", 10)
beta_loc = BetaArray(4)
beta_blk = BetaArray("cell1", 10)

leg[0] = 111
beta_loc[0] = 222
beta_blk[0] = 333
"""
        res = compile_py(code)
        valid, msg, count = validate_with_mindustry(res.mlog)
        self.assertTrue(valid, f"Mindustry assembly error: {msg}")


if __name__ == "__main__":
    unittest.main()
