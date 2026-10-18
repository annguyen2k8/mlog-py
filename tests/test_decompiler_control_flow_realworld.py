"""Regression tests for real-world decompiler control flow patterns.

Covers:
- Bottom-tested loops (do-while with latch conditional break)
- Nested loops with dynamic step ranges without duplicate blocks or unstructured regions
- In-loop conditional break and continue statements
- Jump targets exceeding program length (>= n_instructions)
- Short-circuit boolean branching within scope boundaries
- Semantic equivalence round-trips (compile -> decompile -> compile)
"""

import unittest

from src.mlog import compile_py
from src.decompiler import decompile
from src.decompiler.cfg import build_cfg
from src.decompiler.structurer import structure_cfg


class TestDecompilerControlFlowRealWorld(unittest.TestCase):
    """Real-world control flow regression suite based on user samples."""

    def test_gamehandle_bottom_tested_loop_with_latch_break(self):
        """Minesweeper generator loop: latch jump repeats when hasMine == 1, breaks when != 1."""
        mlog = (
            "set mines 10\n"
            "set i 0\n"
            "jump 14 greaterThanEq i mines\n"
            "op add seek offset i\n"
            "op rand xM 14 0\n"
            "op round xM xM 0\n"
            "op rand yM 13 0\n"
            "op round yM yM 0\n"
            "op mul yv yM 14\n"
            "op add val xM yv\n"
            "read hasMine bank1 val\n"
            "jump 4 equal hasMine 1\n"
            "write val bank1 seek\n"
            "op add i i 1\n"
            "jump 2 always 0 0\n"
            "stop\n"
        )
        py_code = decompile(mlog)

        # Must NOT produce an endless while True: without a break
        self.assertIn("while True:", py_code)
        self.assertTrue(
            "hasMine != 1" in py_code or "not hasMine" in py_code,
            f"Expected break condition on hasMine, got:\n{py_code}",
        )
        self.assertIn("break", py_code)
        # The statements following the inner loop must exist in the output
        self.assertIn('write(val, "bank1", seek)', py_code)
        self.assertIn("i = i + 1", py_code)

        # Roundtrip compilation: must compile to valid mlog
        res = compile_py(py_code, allow_functions=False, validate=True)
        self.assertIn("read hasMine bank1 val", res.mlog)
        self.assertIn("write val bank1 seek", res.mlog)

    def test_render_nested_loops_no_duplication_and_no_unstructured(self):
        """Nested graphics render loop with dynamic step should produce clean, deduplicated code."""
        mlog = (
            "sensor wScr display1 @displayWidth\n"
            "sensor hScr display1 @displayHeight\n"
            "set size 4\n"
            "set x 0\n"
            "jump 7 lessThanEq size 0\n"
            "jump 16 greaterThanEq x wScr\n"
            "jump 8 always 0 0\n"
            "jump 16 lessThanEq x wScr\n"
            "set y 0\n"
            "jump 14 greaterThanEq y hScr\n"
            "draw color 255 0 0 255 0 0\n"
            "draw rect x y size size 0 0\n"
            "op add y y size\n"
            "jump 9 always 0 0\n"
            "op add x x size\n"
            "jump 4 always 0 0\n"
            "end\n"
        )
        py_code = decompile(mlog)

        # Must not contain unstructured regions
        self.assertNotIn("[UNSTRUCTURED REGION]", py_code)
        self.assertNotIn("jump(", py_code)

        # The body statements must only appear once, not duplicated
        self.assertEqual(py_code.count('draw("rect", x, y, size, size, 0, 0)'), 1)
        self.assertEqual(py_code.count("y = y + size"), 1)
        self.assertEqual(py_code.count("x = x + size"), 1)

        # Roundtrip compile
        res = compile_py(py_code, allow_functions=False, validate=True)
        self.assertIn("draw rect x y size size", res.mlog)

    def test_in_loop_conditional_break(self):
        """A conditional jump targeting loop exit address within loop body becomes 'if cond: break'."""
        mlog = (
            "set i 0\n"
            "jump 7 greaterThanEq i 10\n"
            "read val bank1 i\n"
            "jump 7 equal val 99\n"
            "write val bank2 i\n"
            "op add i i 1\n"
            "jump 1 always 0 0\n"
            "print \"done\"\n"
        )
        py_code = decompile(mlog)
        self.assertIn("while i < 10:", py_code)
        self.assertIn("if val == 99:", py_code)
        self.assertIn("break", py_code)
        self.assertNotIn("[UNSTRUCTURED REGION]", py_code)

        # Verify roundtrip
        res = compile_py(py_code, allow_functions=False, validate=True)
        self.assertIn("write val bank2 i", res.mlog)

    def test_in_loop_conditional_continue(self):
        """A conditional jump targeting loop header address becomes 'if cond: continue'."""
        mlog = (
            "set i 0\n"
            "jump 7 greaterThanEq i 10\n"
            "read val bank1 i\n"
            "jump 1 equal val 0\n"
            "write val bank2 i\n"
            "op add i i 1\n"
            "jump 1 always 0 0\n"
            "print \"done\"\n"
        )
        py_code = decompile(mlog)
        self.assertIn("while i < 10:", py_code)
        self.assertIn("if val == 0:", py_code)
        self.assertIn("continue", py_code)
        self.assertNotIn("[UNSTRUCTURED REGION]", py_code)

        # Verify roundtrip
        res = compile_py(py_code, allow_functions=False, validate=True)
        self.assertIn("write val bank2 i", res.mlog)

    def test_loop_header_exit_targeting_ge_n_instructions(self):
        """Loop header conditional jump targeting >= n_instructions structures cleanly without duplication."""
        mlog = (
            "jump 3 greaterThanEq counter 5\n"
            "op add counter counter 1\n"
            "jump 0 always 0 0\n"
        )
        py_code = decompile(mlog)
        self.assertIn("while counter < 5:", py_code)
        self.assertIn("counter = counter + 1", py_code)
        self.assertNotIn("while True:", py_code)
        self.assertNotIn("[UNSTRUCTURED REGION]", py_code)

    def test_top_level_jump_ge_n_instructions_is_conditional_end(self):
        """A top-level conditional jump targeting >= n becomes 'if cond: end()'."""
        mlog = (
            "sensor on switch1 @enabled\n"
            "jump 3 equal on 0\n"
            "print \"running\"\n"
        )
        py_code = decompile(mlog)
        self.assertIn("if on != 0:", py_code)
        self.assertIn('print("running")', py_code)
        self.assertNotIn("[UNSTRUCTURED REGION]", py_code)

    def test_real_files_roundtrip_coverage(self):
        """Verify round-trip compile/decompile for user samples and corpus samples."""
        import os
        sample_files = [
            ("tests/corpus/compiler_generated/arithmetic_dataflow.mlog", "arithmetic_dataflow"),
            ("/data/data/com.termux/files/home/mlogs/minesweeper/gamehandle.mlog", "gamehandle"),
            ("/data/data/com.termux/files/home/mlogs/render.mlog", "render"),
        ]
        for path, name in sample_files:
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                orig_mlog = f.read()

            py_code = decompile(orig_mlog)
            self.assertNotIn("[UNSTRUCTURED REGION]", py_code)

            if name == "gamehandle":
                self.assertTrue("hasMine != 1" in py_code or "not hasMine" in py_code)
                self.assertIn('write(xy, "bank1", seek)', py_code)
                self.assertIn("i = i + 1", py_code)
            elif name == "render":
                self.assertEqual(py_code.count("y = y + size"), 1)
                self.assertEqual(py_code.count("x = x + size"), 1)
            elif name == "arithmetic_dataflow":
                self.assertIn("+", py_code)
                self.assertIn("res = 1", py_code)
                self.assertIn("res = 0", py_code)

            res = compile_py(py_code, allow_functions=False, validate=True)
            self.assertTrue(len(res.mlog.strip().splitlines()) > 0)


if __name__ == "__main__":
    unittest.main()
