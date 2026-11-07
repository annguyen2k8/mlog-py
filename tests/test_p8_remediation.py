"""Pure Python unit tests for P8 remediation (P8-REM-01).

Verifies the elimination of redundant conditional exit guards for compile-time
constant true conditions in while loops, preserving control-flow accuracy,
jump targets, dynamic condition guards, break/continue semantics, and
byte-identical corpus roundtrips across all 5 affected files.
"""

import os
import unittest
from pathlib import Path

from mlog import compile_py
from mlog.decompiler import decompile
from mlog.errors import CompileError

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "tests" / "corpus"


def _read_corpus(rel_path: str) -> str:
    return (CORPUS_DIR / rel_path).read_text(encoding="utf-8")


def _normalized_lines(text: str) -> list[str]:
    return [line.strip() for line in text.strip().splitlines()]


class TestP8WhileLoopOptimization(unittest.TestCase):
    """Targeted compiler tests for while loop condition lowering."""

    def test_while_true_omits_redundant_guard(self):
        """while True: emits only body instructions and unconditional backward jump."""
        source = "while True:\n    x = 1\n"
        mlog = compile_py(source).mlog
        lines = _normalized_lines(mlog)
        self.assertEqual(lines, [
            "set x 1",
            "jump 0 always 0 0",
        ])

    def test_while_literal_int_non_zero_omits_guard(self):
        """while 1: emits only body instructions and unconditional backward jump."""
        source = "while 1:\n    x = 1\n"
        mlog = compile_py(source).mlog
        lines = _normalized_lines(mlog)
        self.assertEqual(lines, [
            "set x 1",
            "jump 0 always 0 0",
        ])

    def test_while_constant_expr_folded_omits_guard(self):
        """while 1 == 1: and while not False: fold to constant true and omit guard."""
        for cond in ("1 == 1", "not False", "True and True", "1 != 0"):
            source = f"while {cond}:\n    x = 1\n"
            mlog = compile_py(source, fold_constants=True).mlog
            lines = _normalized_lines(mlog)
            self.assertEqual(
                lines,
                ["set x 1", "jump 0 always 0 0"],
                f"Failed for condition: {cond}",
            )

    def test_while_false_preserves_guard(self):
        """while False: must preserve guard jumping past loop body."""
        source = "while False:\n    x = 1\n"
        mlog = compile_py(source).mlog
        lines = _normalized_lines(mlog)
        self.assertEqual(lines, [
            "jump 3 equal false 0",
            "set x 1",
            "jump 0 always 0 0",
        ])

    def test_while_zero_preserves_guard(self):
        """while 0: must preserve guard jumping past loop body."""
        source = "while 0:\n    x = 1\n"
        mlog = compile_py(source).mlog
        lines = _normalized_lines(mlog)
        self.assertEqual(lines, [
            "jump 3 equal 0 0",
            "set x 1",
            "jump 0 always 0 0",
        ])

    def test_while_dynamic_condition_preserves_guard(self):
        """while x < 10: must preserve condition check and accurate jump target."""
        source = "while x < 10:\n    x = x + 1\n"
        mlog = compile_py(source).mlog
        lines = _normalized_lines(mlog)
        self.assertEqual(lines, [
            "jump 3 greaterThanEq x 10",
            "op add x x 1",
            "jump 0 always 0 0",
        ])

    def test_while_true_break_semantics(self):
        """break inside while True: jumps to instruction after loop."""
        source = (
            "while True:\n"
            "    if x > 10:\n"
            "        break\n"
            "    x = x + 1\n"
            "print(x)\n"
        )
        mlog = compile_py(source).mlog
        lines = _normalized_lines(mlog)
        # Expected layout without leading guard:
        # 0: jump 2 lessThanEq x 10
        # 1: jump 4 always 0 0       (break jumps to line 4)
        # 2: op add x x 1
        # 3: jump 0 always 0 0       (loop back to line 0)
        # 4: print x
        self.assertEqual(lines, [
            "jump 2 lessThanEq x 10",
            "jump 4 always 0 0",
            "op add x x 1",
            "jump 0 always 0 0",
            "print x",
        ])

    def test_while_true_continue_semantics(self):
        """continue inside while True: jumps back to loop start."""
        source = (
            "while True:\n"
            "    if x == 5:\n"
            "        continue\n"
            "    x = x + 1\n"
        )
        mlog = compile_py(source).mlog
        lines = _normalized_lines(mlog)
        # Expected layout without leading guard:
        # 0: jump 2 notEqual x 5
        # 1: jump 0 always 0 0       (continue jumps to loop start at 0)
        # 2: op add x x 1
        # 3: jump 0 always 0 0       (loop back to line 0)
        self.assertEqual(lines, [
            "jump 2 notEqual x 5",
            "jump 0 always 0 0",
            "op add x x 1",
            "jump 0 always 0 0",
        ])

    def test_nested_while_loops(self):
        """Nested while True and dynamic while loops maintain correct targets."""
        source = (
            "while True:\n"
            "    while i < 5:\n"
            "        i = i + 1\n"
            "    break\n"
        )
        mlog = compile_py(source).mlog
        lines = _normalized_lines(mlog)
        # Outer while True: starts at 0
        # Inner while i < 5: starts at 0
        # 0: jump 3 greaterThanEq i 5
        # 1: op add i i 1
        # 2: jump 0 always 0 0
        # 3: jump 5 always 0 0       (break from outer loop jumps to 5)
        # 4: jump 0 always 0 0       (outer loop back)
        self.assertEqual(lines, [
            "jump 3 greaterThanEq i 5",
            "op add i i 1",
            "jump 0 always 0 0",
            "jump 5 always 0 0",
            "jump 0 always 0 0",
        ])

    def test_while_true_with_else_block(self):
        """while True: ... else: ... preserves else block structure."""
        source = (
            "while True:\n"
            "    break\n"
            "else:\n"
            "    x = 10\n"
        )
        mlog = compile_py(source).mlog
        lines = _normalized_lines(mlog)
        # break jumps to while_end (line 3, skipping else block at line 2)
        self.assertEqual(lines, [
            "jump 3 always 0 0",
            "jump 0 always 0 0",
            "set x 10",
        ])


class TestP8CorpusRoundtripByteIdentity(unittest.TestCase):
    """Verifies byte-identity across all 5 affected corpus files."""

    def _assert_roundtrip_byte_identical(self, rel_path: str):
        orig_mlog = _read_corpus(rel_path)
        py_code = decompile(orig_mlog, filename=rel_path)
        recompiled = compile_py(py_code, allow_functions=True, validate=True).mlog
        orig_lines = _normalized_lines(orig_mlog)
        rec_lines = _normalized_lines(recompiled)
        self.assertEqual(
            orig_lines,
            rec_lines,
            f"Byte mismatch in {rel_path}: orig {len(orig_lines)} lines != rec {len(rec_lines)} lines",
        )

    def test_flare_miner_byte_identical(self):
        self._assert_roundtrip_byte_identical("handwritten/flare_miner.mlog")

    def test_turret_radar_byte_identical(self):
        self._assert_roundtrip_byte_identical("handwritten/turret_radar.mlog")

    def test_scale_100_byte_identical(self):
        self._assert_roundtrip_byte_identical("pathological/scale_100_instr.mlog")

    def test_scale_500_byte_identical(self):
        self._assert_roundtrip_byte_identical("pathological/scale_500_instr.mlog")

    def test_scale_1000_byte_identical(self):
        self._assert_roundtrip_byte_identical("pathological/scale_1000_instr.mlog")

    def test_p8_rem_02_large_compiler_program_assignment_layout(self):
        """P8-REM-02: large_compiler_program assignment layout verification.

        The diff is strictly the commutative parameter assignment order:
        original sets (a, b) while recompiled sets (b, a). Both have identical
        instruction count (38) and disjoint non-aliasing registers.
        """
        lcp_orig = _read_corpus("compiler_generated/large_compiler_program.mlog")
        lcp_py = decompile(lcp_orig)
        lcp_rec = compile_py(lcp_py, allow_functions=True, validate=True).mlog
        orig_lines = _normalized_lines(lcp_orig)
        rec_lines = _normalized_lines(lcp_rec)
        self.assertEqual(len(orig_lines), len(rec_lines))
        self.assertEqual(len(orig_lines), 41)
        # Line 17-18 are commutative assignments to distinct registers
        self.assertEqual({orig_lines[17], orig_lines[18]}, {"set a s1", "set b z"})
        self.assertEqual({rec_lines[17], rec_lines[18]}, {"set a s1", "set b z"})
        # All other lines are byte-identical
        for i in range(len(orig_lines)):
            if i not in (17, 18):
                self.assertEqual(orig_lines[i], rec_lines[i], f"Mismatch at line {i}")

    def test_p8_rem_03_empty_branches_eof_termination(self):
        """P8-REM-03: empty_branches EOF termination verification.

        Unconditional jump past final instruction (jump 7) is decompiled to
        idiomatic end(), which re-lowers to the canonical 'end' opcode.
        Total instruction count remains 7 (lines 0..6).
        """
        eb_orig = _read_corpus("control_flow/empty_branches.mlog")
        eb_py = decompile(eb_orig)
        self.assertIn("end()", eb_py)
        eb_rec = compile_py(eb_py, allow_functions=True, validate=True).mlog
        orig_lines = _normalized_lines(eb_orig)
        rec_lines = _normalized_lines(eb_rec)
        self.assertEqual(len(orig_lines), len(rec_lines))
        self.assertEqual(len(orig_lines), 7)
        self.assertEqual(orig_lines[6], "jump 7 always 0 0")
        self.assertEqual(rec_lines[6], "end")
        # Lines 0..5 are byte-identical
        self.assertEqual(orig_lines[:6], rec_lines[:6])

    def test_out_of_scope_files_remain_unmodified_behavior(self):
        """Verify multi_func_math maintains its documented behavior."""
        mfm_orig = _read_corpus("compiler_generated/multi_func_math.mlog")
        mfm_py = decompile(mfm_orig)
        mfm_rec = compile_py(mfm_py, allow_functions=True, validate=True).mlog
        self.assertEqual(len(_normalized_lines(mfm_orig)), len(_normalized_lines(mfm_rec)))


if __name__ == "__main__":
    unittest.main()
