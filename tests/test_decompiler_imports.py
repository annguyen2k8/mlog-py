"""Regression and verification tests for decompiler self-contained DSL imports.

Verifies:
- Minimal canonical import headers ('from mlog import ...')
- Correct import generation for op, draw, read, write, sensor, control, etc.
- Multi-symbol subset API imports sorted alphabetically
- Zero-unused-import guarantee: no header emitted when using only pure Python constructs
- Valid syntax verified via ast.parse() and Python builtin compile()
- Recompilation equivalence via compile_py()
- Realistic 7-segment / display controller roundtrip verification
"""

import ast
import unittest

from src.mlog import compile_py
from src.decompiler import decompile, decompile_with_source_map
from src.decompiler.dsl_symbols import (
    collect_used_dsl_symbols,
    extract_dsl_symbols_from_ast,
    format_import_header,
    get_required_dsl_imports,
)


class TestDecompilerImports(unittest.TestCase):
    """Test suite for decompiler automatic import header generation."""

    def test_output_with_op_import(self):
        """Unfoldable op calls (e.g. min, max, sin) must import op."""
        mlog = """
set n 1500
op min n n 999
"""
        py = decompile(mlog)
        # 1. Valid syntax
        ast.parse(py)
        code_obj = compile(py, "<test>", "exec")
        self.assertIsNotNone(code_obj)

        # 2. Contains import
        self.assertIn("from mlog import op", py)
        self.assertTrue("op('min', n, 999)" in py or 'op("min", n, 999)' in py)

        # 3. Can recompile
        res = compile_py(py)
        self.assertIn("op min n n 999", res.mlog)

    def test_output_with_draw_and_drawflush(self):
        """Drawing instructions must import draw and drawflush."""
        mlog = """
draw clear 0 0 0 0 0 0
draw color 255 0 0 255 0 0
draw line 0 0 80 80 0 0
drawflush display1
"""
        py = decompile(mlog)
        ast.parse(py)
        code_obj = compile(py, "<test>", "exec")
        self.assertIsNotNone(code_obj)

        self.assertIn("from mlog import draw, drawflush", py)
        self.assertIn('drawflush("display1")', py)

        # Recompile roundtrip
        res = compile_py(py)
        self.assertIn("draw clear", res.mlog)
        self.assertIn("drawflush display1", res.mlog)

    def test_output_with_read_and_write(self):
        """Memory cell access must import read and write."""
        mlog = """
read data cell1 0
op add data data 1
write data cell1 0
"""
        py = decompile(mlog)
        ast.parse(py)
        code_obj = compile(py, "<test>", "exec")
        self.assertIsNotNone(code_obj)

        self.assertIn("from mlog import read, write", py)
        self.assertIn('read(data, "cell1", 0)', py)
        self.assertIn('write(data, "cell1", 0)', py)

        # Roundtrip
        res = compile_py(py)
        self.assertIn("read data cell1 0", res.mlog)
        self.assertIn("write data cell1 0", res.mlog)

    def test_output_subset_api_sorted(self):
        """Multiple distinct intrinsics must be imported alphabetically in a single header."""
        mlog = """
sensor hp vault1 @health
control enabled reactor1 1 0 0 0
wait 0.5
"""
        py = decompile(mlog)
        ast.parse(py)
        code_obj = compile(py, "<test>", "exec")
        self.assertIsNotNone(code_obj)

        self.assertIn("from mlog import control, sensor, wait", py)

        # Roundtrip
        res = compile_py(py)
        self.assertIn("sensor hp vault1 @health", res.mlog)
        self.assertIn("control enabled reactor1 1 0 0 0", res.mlog)
        self.assertIn("wait 0.5", res.mlog)

    def test_no_imports_when_only_python_primitives_used(self):
        """Programs with only assignments, arithmetic and loops must NOT emit import header."""
        mlog = """
set x 10
op add y x 5
op mul z y 2
jump 5 lessThanEq z 100
set z 100
"""
        py = decompile(mlog)
        ast.parse(py)
        compile(py, "<test>", "exec")

        # Zero unused import bar: NO 'from mlog'
        self.assertNotIn("from mlog", py)
        self.assertIn("x = 10", py)
        self.assertIn("y = x + 5", py)
        self.assertIn("z = y * 2", py)

    def test_unstructured_jump_imports_jump(self):
        """Unstructured jump fallback must import jump."""
        mlog = """
set x 10
jump 3 greaterThan x 5
set y 1
jump 5 always 0 0
set y 2
jump 2 lessThan y 10
set z 3
"""
        py = decompile(mlog)
        ast.parse(py)
        compile(py, "<test>", "exec")

        self.assertIn("from mlog import jump", py)
        self.assertIn("jump(", py)

    def test_stop_and_end_intrinsics(self):
        """stop and end instructions must import stop and end."""
        mlog = """
stop
end
"""
        py = decompile(mlog)
        ast.parse(py)
        compile(py, "<test>", "exec")

        self.assertIn("from mlog import end, stop", py)
        self.assertIn("stop()", py)
        self.assertIn("end()", py)

    def test_realistic_7segment_display_controller(self):
        """Realistic 7-segment display logic with clamp, draw and memory read."""
        mlog = """
set val 0
read val cell1 0
op min clamped val 9
op max clamped clamped 0
draw clear 0 0 0 0 0 0
draw color 0 255 128 255 0 0
draw rect 10 10 20 60 0 0
drawflush display1
"""
        py = decompile(mlog)

        # 1. Syntax check via ast.parse
        ast.parse(py)
        code_obj = compile(py, "<test>", "exec")
        self.assertIsNotNone(code_obj)

        # 2. Check header has exactly the needed symbols
        self.assertIn("from mlog import draw, drawflush, op, read", py)

        # 3. Execute in Python runtime environment where mlog is installed
        import mlog as mlog_module
        namespace = {
            "__builtins__": __builtins__,
            "clear": "clear",
            "color": "color",
            "rect": "rect",
        }
        for name in dir(mlog_module):
            if not name.startswith("_"):
                namespace[name] = getattr(mlog_module, name)
        # Executing should not raise NameError for any DSL symbol!
        exec(py, namespace)

        # 4. Recompile roundtrip
        res = compile_py(py)
        self.assertIn("read val cell1 0", res.mlog)
        self.assertIn("draw clear", res.mlog)
        self.assertIn("drawflush display1", res.mlog)

    def test_sourcemap_with_imports_preserves_accuracy(self):
        """SourceMap line numbers must be aligned with actual Python lines when imports exist."""
        mlog = """
draw clear 0 0 0 0 0 0
drawflush display1
"""
        code, sm = decompile_with_source_map(mlog)
        ast.parse(code)

        lines = code.splitlines()
        self.assertEqual(lines[0], "from mlog import draw, drawflush")
        self.assertEqual(lines[1], "")
        self.assertEqual(lines[2], "draw(clear, 0, 0, 0, 0, 0, 0)")
        self.assertEqual(lines[3], 'drawflush("display1")')

        # Instruction 0 (draw clear) must map to line 3
        draw_line = sm.mlog_to_python(0)
        self.assertEqual(draw_line, 3)

        # Instruction 1 (drawflush) must map to line 4
        flush_line = sm.mlog_to_python(1)
        self.assertEqual(flush_line, 4)


if __name__ == "__main__":
    unittest.main()
