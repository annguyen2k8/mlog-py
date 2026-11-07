"""Unit and regression tests for mlog.beta.LocalArray."""

import unittest
import ast

from src.errors import CompileError
from src.beta import LocalArray as PureLocalArray
from src.mlog import compile_py
from src.validator import MlogValidator
from src.mindustry_validator import is_mindustry_available, validate_with_mindustry


class TestPureLocalArray(unittest.TestCase):
    """Tests for the pure Python LocalArray class implementation."""

    def test_basic_construction_and_indexing(self):
        arr = PureLocalArray(4)
        self.assertEqual(len(arr), 4)
        self.assertEqual(arr.size, 4)
        self.assertIsNone(arr[0])
        arr[0] = 42
        arr[3] = 99
        self.assertEqual(arr[0], 42)
        self.assertEqual(arr[3], 99)

    def test_default_value_initialization(self):
        arr = PureLocalArray(3, default=0)
        self.assertEqual(list(arr), [0, 0, 0])
        arr[1] = 10
        self.assertEqual(list(arr), [0, 10, 0])

    def test_bounds_checking(self):
        arr = PureLocalArray(3)
        with self.assertRaises(IndexError):
            _ = arr[-1]
        with self.assertRaises(IndexError):
            _ = arr[3]
        with self.assertRaises(IndexError):
            arr[-1] = 10
        with self.assertRaises(IndexError):
            arr[3] = 10

    def test_type_checking_index(self):
        arr = PureLocalArray(3)
        with self.assertRaises(TypeError):
            _ = arr["0"]  # type: ignore
        with self.assertRaises(TypeError):
            _ = arr[1.5]  # type: ignore
        with self.assertRaises(TypeError):
            _ = arr[True]  # type: ignore

    def test_invalid_capacity(self):
        with self.assertRaises(ValueError):
            PureLocalArray(0)
        with self.assertRaises(ValueError):
            PureLocalArray(-5)
        with self.assertRaises(ValueError):
            PureLocalArray(65)
        with self.assertRaises(ValueError):
            PureLocalArray(True)  # type: ignore


class TestLocalArrayCompiler(unittest.TestCase):
    """Tests for LocalArray compiler integration and MLog code generation."""

    def test_basic_static_read_write(self):
        code = """
from mlog.beta import LocalArray
arr = LocalArray(4)
arr[0] = 10
arr[1] = 20
arr[2] = arr[0] + arr[1]
arr[3] += 5
x = arr[2]
"""
        res = compile_py(code)
        mlog = res.mlog
        MlogValidator.validate(mlog)

        self.assertIn("set arr_0 10", mlog)
        self.assertIn("set arr_1 20", mlog)
        self.assertIn("op add arr_2 arr_0 arr_1", mlog)
        self.assertIn("op add arr_3 arr_3 5", mlog)
        self.assertIn("set x arr_2", mlog)

        # Confirm zero cell/bank read/write opcodes
        self.assertNotIn("read", mlog)
        self.assertNotIn("write", mlog)
        self.assertNotIn("cell", mlog)
        self.assertNotIn("bank", mlog)

    def test_default_value_emission(self):
        code = """
from mlog.beta import LocalArray
arr = LocalArray(3, default=0)
"""
        res = compile_py(code)
        mlog = res.mlog
        lines = [line.strip() for line in mlog.strip().splitlines() if line.strip()]
        self.assertEqual(lines, [
            "set arr_0 0",
            "set arr_1 0",
            "set arr_2 0",
        ])

    def test_generic_type_subscript_syntax(self):
        code = """
from mlog import beta
arr = beta.LocalArray[float](2, default=1.5)
arr[0] = 3.14
arr[1] += 0.5
"""
        res = compile_py(code)
        mlog = res.mlog
        MlogValidator.validate(mlog)
        self.assertIn("set arr_0 1.5", mlog)
        self.assertIn("set arr_1 1.5", mlog)
        self.assertIn("set arr_0 3.14", mlog)
        self.assertIn("op add arr_1 arr_1 0.5", mlog)

    def test_keyword_arguments(self):
        code = """
from mlog.beta import LocalArray
arr = LocalArray(size=2, default=7, dtype=int)
"""
        res = compile_py(code)
        mlog = res.mlog
        self.assertIn("set arr_0 7", mlog)
        self.assertIn("set arr_1 7", mlog)

    def test_len_and_size_property(self):
        code = """
from mlog.beta import LocalArray
arr = LocalArray(5)
sz = len(arr)
sz2 = arr.size
"""
        res = compile_py(code)
        mlog = res.mlog
        MlogValidator.validate(mlog)
        self.assertIn("set sz 5", mlog)
        self.assertIn("set sz2 5", mlog)

    def test_reject_negative_index(self):
        for idx in ("-1", "-2"):
            code = f"""
from mlog.beta import LocalArray
arr = LocalArray(4)
arr[{idx}] = 10
"""
            with self.assertRaises(CompileError) as ctx:
                compile_py(code)
            self.assertIn("array index out of bounds", str(ctx.exception))
            self.assertIn("outside valid range [0, 4)", str(ctx.exception))

    def test_reject_out_of_bounds_index(self):
        for idx in ("4", "5", "100"):
            code = f"""
from mlog.beta import LocalArray
arr = LocalArray(4)
arr[{idx}] = 10
"""
            with self.assertRaises(CompileError) as ctx:
                compile_py(code)
            self.assertIn("array index out of bounds", str(ctx.exception))
            self.assertIn(f"index {idx} is outside valid range [0, 4)", str(ctx.exception))

    def test_reject_out_of_bounds_read(self):
        code = """
from mlog.beta import LocalArray
arr = LocalArray(2)
x = arr[2]
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("array index out of bounds", str(ctx.exception))
        self.assertIn("index 2 is outside valid range [0, 2)", str(ctx.exception))

    def test_reject_out_of_bounds_aug_assign(self):
        code = """
from mlog.beta import LocalArray
arr = LocalArray(2)
arr[2] += 1
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("array index out of bounds", str(ctx.exception))
        self.assertIn("index 2 is outside valid range [0, 2)", str(ctx.exception))

    def test_reject_dynamic_indexing(self):
        # Dynamic read
        code_read = """
from mlog.beta import LocalArray
arr = LocalArray(4)
i = 2
x = arr[i]
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code_read)
        self.assertIn("LocalArray only supports compile-time static indexing; dynamic index is not supported", str(ctx.exception))
        self.assertIn("use BlockArray for dynamic indexing", str(ctx.exception))

        # Dynamic write
        code_write = """
from mlog.beta import LocalArray
arr = LocalArray(4)
i = 2
arr[i] = 10
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code_write)
        self.assertIn("LocalArray only supports compile-time static indexing; dynamic index is not supported", str(ctx.exception))

        # Dynamic aug assign
        code_aug = """
from mlog.beta import LocalArray
arr = LocalArray(4)
i = 2
arr[i] += 10
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code_aug)
        self.assertIn("LocalArray only supports compile-time static indexing; dynamic index is not supported", str(ctx.exception))

    def test_reject_non_integer_literal_index(self):
        for bad_idx in ("1.5", "'0'", "True"):
            code = f"""
from mlog.beta import LocalArray
arr = LocalArray(4)
arr[{bad_idx}] = 10
"""
            with self.assertRaises(CompileError) as ctx:
                compile_py(code)
            self.assertIn("array index must be an integer", str(ctx.exception))

    def test_reject_invalid_capacity(self):
        for bad_size in ("0", "-1", "65", "100"):
            code = f"""
from mlog.beta import LocalArray
arr = LocalArray({bad_size})
"""
            with self.assertRaises(CompileError) as ctx:
                compile_py(code)
            self.assertTrue(
                "LocalArray size must be a positive integer" in str(ctx.exception)
                or "exceeds maximum register capacity (64)" in str(ctx.exception)
            )

    def test_reject_unassigned_declaration(self):
        code = """
from mlog.beta import LocalArray
LocalArray(4)
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("LocalArray declaration must be assigned to a variable", str(ctx.exception))

    def test_reject_reassigning_array(self):
        code = """
from mlog.beta import LocalArray
arr = LocalArray(4)
arr = 10
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("cannot reassign Array variable 'arr'", str(ctx.exception))

    def test_reject_assigning_array_to_variable(self):
        code = """
from mlog.beta import LocalArray
arr = LocalArray(4)
other = arr
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("cannot assign LocalArray 'arr' directly to a variable", str(ctx.exception))

    def test_reject_declaration_in_function(self):
        code = """
from mlog.beta import LocalArray
def my_func():
    arr = LocalArray(4)
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code, allow_functions=True)
        self.assertIn("LocalArray declaration is not allowed inside functions", str(ctx.exception))

    def test_reject_declaration_in_loop(self):
        code = """
from mlog.beta import LocalArray
for i in range(10):
    arr = LocalArray(4)
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code)
        self.assertIn("LocalArray declaration is not allowed inside loops", str(ctx.exception))

    def test_access_global_array_from_function(self):
        code = """
from mlog.beta import LocalArray
arr = LocalArray(2, default=0)
def increment_first():
    arr[0] += 1
increment_first()
res = arr[0]
"""
        res = compile_py(code, allow_functions=True)
        mlog = res.mlog
        MlogValidator.validate(mlog)
        self.assertIn("op add arr_0 arr_0 1", mlog)
        self.assertIn("set res arr_0", mlog)

    def test_int_array_reject_incompatible_literals(self):
        code_str = """
from mlog.beta import LocalArray
arr = LocalArray(2, dtype=int)
arr[0] = "text"
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code_str)
        self.assertIn("LocalArray only stores integers; string literal is not supported", str(ctx.exception))

        code_float = """
from mlog.beta import LocalArray
arr = LocalArray(2, dtype=int)
arr[0] = 3.14
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code_float)
        self.assertIn("LocalArray only stores integers; float literal is not supported", str(ctx.exception))

    def test_bool_array_type_constraints(self):
        code_valid = """
from mlog.beta import LocalArray
arr = LocalArray(2, dtype=bool)
arr[0] = True
arr[1] = False
"""
        res = compile_py(code_valid)
        mlog = res.mlog
        self.assertIn("set arr_0 true", mlog)
        self.assertIn("set arr_1 false", mlog)

        code_int = """
from mlog.beta import LocalArray
arr = LocalArray(2, dtype=bool)
arr[0] = 1
"""
        with self.assertRaises(CompileError) as ctx:
            compile_py(code_int)
        self.assertIn("LocalArray of type 'bool' only stores booleans; integer literal is not supported", str(ctx.exception))

    def test_mindustry_jvm_execution_fidelity(self):
        if not is_mindustry_available():
            self.skipTest("Mindustry v160.7 engine not available")

        code = """
from mlog.beta import LocalArray
arr = LocalArray(4, default=0)
arr[0] = 10
arr[1] = 25
arr[2] = arr[0] + arr[1]
arr[3] = arr[2] * 2
final_val = arr[3]
"""
        res = compile_py(code)
        valid, msg, count = validate_with_mindustry(res.mlog)
        self.assertTrue(valid, f"Mindustry assembly error: {msg}")


if __name__ == "__main__":
    unittest.main()
