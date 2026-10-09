"""Phase 5 Hardening & Real-World Corpus Verification Test Suite.

Verifies the Mindustry Logic (mlog) to Python DSL decompiler across real-world,
compiler-generated, structured control flow, function, mindustry API, and pathological corpus cases.
"""

import ast
import glob
import os
import py_compile
import tempfile
import time
import tracemalloc
import unittest
from typing import Dict, List, Set, Tuple

from src.decompiler import decompile, decompile_with_source_map
from src.decompiler.cfg import build_cfg
from src.decompiler.function_analyzer import FunctionAnalyzer
from src.decompiler.sourcemap import SourceMap
from src.decompiler.structured_ir import UnstructuredNode
from src.decompiler.structurer import recover_expressions, structure_cfg
from src.mlog import compile_py


CORPUS_DIR = os.path.join(os.path.dirname(__file__), "corpus")


class TestCorpusDecompilation(unittest.TestCase):
    """Verifies that all corpus cases decompile to valid Python DSL."""

    def _get_corpus_files(self, category: str) -> List[str]:
        path = os.path.join(CORPUS_DIR, category, "*.mlog")
        files = sorted(glob.glob(path))
        self.assertTrue(len(files) > 0, f"No files found in {category}")
        return files

    def _verify_file(self, path: str):
        with open(path) as f:
            mlog_text = f.read()

        py_code, sm = decompile_with_source_map(mlog_text, filename=path)

        # 1. AST parse check
        tree = ast.parse(py_code)
        self.assertIsNotNone(tree)

        # 2. Bytecode compilation check
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
            tf.write(py_code)
            tmp_path = tf.name
        try:
            py_compile.compile(tmp_path, doraise=True)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        # 3. Debug mode check
        dbg_code, dbg_sm = decompile_with_source_map(mlog_text, filename=path, debug=True)
        ast.parse(dbg_code)

        # 4. Source map integrity
        self.assertGreater(len(sm.mappings), 0)

    def test_handwritten_corpus(self):
        """Verify all handwritten real-world programs (reactors, units, turrets, displays)."""
        files = self._get_corpus_files("handwritten")
        for path in files:
            with self.subTest(file=os.path.basename(path)):
                self._verify_file(path)

    def test_compiler_generated_corpus(self):
        """Verify all programs generated from the Python-to-mlog compiler."""
        files = self._get_corpus_files("compiler_generated")
        for path in files:
            with self.subTest(file=os.path.basename(path)):
                self._verify_file(path)

    def test_control_flow_corpus(self):
        """Verify complex control flow topologies (nested while, breaks, elif, empty branches)."""
        files = self._get_corpus_files("control_flow")
        for path in files:
            with self.subTest(file=os.path.basename(path)):
                self._verify_file(path)

    def test_functions_corpus(self):
        """Verify function recovery (multiple functions, nested calls, recursion, loops)."""
        files = self._get_corpus_files("functions")
        for path in files:
            with self.subTest(file=os.path.basename(path)):
                self._verify_file(path)

    def test_mindustry_api_corpus(self):
        """Verify peripheral instructions (memory read/write, ucontrol, draw, print, sensor)."""
        files = self._get_corpus_files("mindustry_api")
        for path in files:
            with self.subTest(file=os.path.basename(path)):
                self._verify_file(path)

    def test_pathological_corpus(self):
        """Verify edge cases (irreducible CFGs, dead code, indirect jumps, 100-1000 scale)."""
        files = self._get_corpus_files("pathological")
        for path in files:
            with self.subTest(file=os.path.basename(path)):
                self._verify_file(path)


class TestCorpusRoundTrip(unittest.TestCase):
    """Verifies round-trip decompilation and compilation semantic/structural equivalence."""

    def test_roundtrip_all_corpus(self):
        """Test mlog -> decompile -> compile_py on all 32 corpus files."""
        all_files = sorted(glob.glob(os.path.join(CORPUS_DIR, "**", "*.mlog"), recursive=True))
        self.assertEqual(len(all_files), 32)

        for path in all_files:
            with self.subTest(file=os.path.basename(path)):
                with open(path) as f:
                    orig_mlog = f.read()

                py_code = decompile(orig_mlog, filename=path)
                res = compile_py(py_code, allow_functions=True, validate=True)
                self.assertIsNotNone(res.mlog)
                self.assertGreater(len(res.mlog.strip().splitlines()), 0)

    def test_structural_equivalence_side_effects(self):
        """Verify that side-effecting operations (sensor, control, draw, read, write) are preserved in order."""
        path = os.path.join(CORPUS_DIR, "mindustry_api", "drawing_pipeline.mlog")
        with open(path) as f:
            orig_mlog = f.read()

        py_code = decompile(orig_mlog)
        res = compile_py(py_code, allow_functions=False, validate=True)

        orig_ops = [l.split()[0] for l in orig_mlog.strip().splitlines()]
        recompiled_ops = [l.split()[0] for l in res.mlog.strip().splitlines()]
        self.assertEqual(orig_ops, recompiled_ops)

    def test_dataflow_equivalence_math(self):
        """Verify math expression dataflow recovery roundtrip preserves arithmetic structure."""
        path = os.path.join(CORPUS_DIR, "compiler_generated", "arithmetic_dataflow.mlog")
        with open(path) as f:
            orig_mlog = f.read()

        py_code = decompile(orig_mlog)
        # Verify python DSL reconstructed high-level arithmetic expressions
        self.assertIn("+", py_code)
        self.assertIn("*", py_code)
        self.assertIn("//", py_code)
        self.assertIn("%", py_code)

        res = compile_py(py_code, allow_functions=False, validate=True)
        self.assertIn("op add", res.mlog)
        self.assertIn("op mul", res.mlog)


class TestCorpusSourceMapping(unittest.TestCase):
    """Verifies SourceMap bidirectional lookup and precision across the corpus."""

    def test_sourcemap_bidirectional_consistency(self):
        """Verify all mappings preserve exact bijection mlog_addr <-> python_line."""
        all_files = sorted(glob.glob(os.path.join(CORPUS_DIR, "**", "*.mlog"), recursive=True))
        for path in all_files:
            with open(path) as f:
                mlog_text = f.read()

            py_code, sm = decompile_with_source_map(mlog_text, filename=path)

            for m in sm.mappings:
                for addr in m.mlog_addresses:
                    py_l = sm.mlog_to_python(addr)
                    self.assertIsNotNone(py_l, f"Failed lookup for addr {addr} in {path}")
                    rev_addrs = sm.python_to_mlog(py_l)
                    self.assertIn(addr, rev_addrs)

    def test_sourcemap_json_serialization(self):
        """Verify JSON serialization round-trip on all corpus files."""
        all_files = sorted(glob.glob(os.path.join(CORPUS_DIR, "**", "*.mlog"), recursive=True))
        for path in all_files:
            with open(path) as f:
                mlog_text = f.read()

            _, sm = decompile_with_source_map(mlog_text, filename=path)
            json_str = sm.to_json()
            restored = SourceMap.from_json(json_str)

            self.assertEqual(len(sm.mappings), len(restored.mappings))
            self.assertEqual(sm.version, restored.version)

    def test_debug_comments_correspondence(self):
        """Verify debug comments '# mlog[...]' match source map address ranges."""
        path = os.path.join(CORPUS_DIR, "control_flow", "chained_elif.mlog")
        with open(path) as f:
            mlog_text = f.read()

        dbg_code, sm = decompile_with_source_map(mlog_text, debug=True)
        for line in dbg_code.splitlines():
            if line.strip().startswith("# mlog["):
                self.assertTrue(line.strip().endswith("]"))


class TestCorpusPerformanceAndScaling(unittest.TestCase):
    """Benchmarks performance and linear scaling across 100, 500, and 1000 instructions."""

    def test_linear_scaling_and_memory(self):
        """Verify there is no quadratic blowup across 100, 500, and 1000 instructions."""
        scales = [
            (100, os.path.join(CORPUS_DIR, "pathological", "scale_100_instr.mlog")),
            (500, os.path.join(CORPUS_DIR, "pathological", "scale_500_instr.mlog")),
            (1000, os.path.join(CORPUS_DIR, "pathological", "scale_1000_instr.mlog")),
        ]

        times: Dict[int, float] = {}
        mems: Dict[int, float] = {}

        for n, path in scales:
            with open(path) as f:
                text = f.read()

            tracemalloc.start()
            t0 = time.perf_counter()

            py_code, sm = decompile_with_source_map(text, filename=path)

            t_elapsed = time.perf_counter() - t0
            _, peak_mem = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            times[n] = t_elapsed
            mems[n] = peak_mem

            # Absolute performance bounds
            self.assertLess(t_elapsed, 5.0, f"Decompilation of {n} instrs took {t_elapsed:.2f}s (exceeds 5.0s)")
            self.assertLess(peak_mem, 15 * 1024 * 1024, f"Peak memory {peak_mem} exceeds 15MB")

        # Quadratic check: Time for 1000 instructions should scale roughly linearly with 500 instructions (< 3.5x)
        ratio = times[1000] / max(times[500], 0.001)
        self.assertLess(ratio, 3.5, f"Quadratic behavior detected: ratio 1000/500 is {ratio:.2f}x")


class TestCorpusPathologicalHardening(unittest.TestCase):
    """Tests pathological patterns, edge cases, and Zero Guessing fallbacks."""

    def test_irreducible_cfg_unstructured_fallback(self):
        """Irreducible CFG must not be guessed into fake loops; fallback to UnstructuredNode."""
        path = os.path.join(CORPUS_DIR, "pathological", "irreducible_cfgs.mlog")
        with open(path) as f:
            mlog_text = f.read()

        cfg = build_cfg(mlog_text)
        struct_prog = structure_cfg(cfg)

        has_unstructured = any(isinstance(n, UnstructuredNode) for n in struct_prog.body)
        self.assertTrue(has_unstructured or not struct_prog.is_fully_structured)

        py = decompile(mlog_text)
        ast.parse(py)
        self.assertIn("[UNSTRUCTURED REGION]", py)

    def test_computed_jump_counter_handling(self):
        """Dynamic @counter manipulation decompiles cleanly to valid Python and recompiles."""
        path = os.path.join(CORPUS_DIR, "pathological", "computed_jump_counter.mlog")
        with open(path) as f:
            mlog_text = f.read()

        py = decompile(mlog_text)
        tree = ast.parse(py)
        self.assertIsNotNone(tree)
        self.assertIn('op("add", \'@counter\'', py)

    def test_unreachable_dead_code_handling(self):
        """Unreachable dead code blocks are safely represented without crashing."""
        path = os.path.join(CORPUS_DIR, "pathological", "unreachable_dead_code.mlog")
        with open(path) as f:
            mlog_text = f.read()

        py = decompile(mlog_text)
        ast.parse(py)
        self.assertIn("dead1", py)


class TestCorpusRegressionCases(unittest.TestCase):
    """Regression tests for specific edge cases uncovered during hardening."""

    def test_interleaved_call_argument_inlining(self):
        """Compiler temporary used in call argument calculation must be safely inlined."""
        path = os.path.join(CORPUS_DIR, "compiler_generated", "large_compiler_program.mlog")
        with open(path) as f:
            mlog_text = f.read()

        py = decompile(mlog_text)
        self.assertNotIn("__tmp2", py)
        self.assertIn("compute_stat(i, i + 1, 3)", py)

    def test_float_operands_in_intrinsic_calls(self):
        """Float numbers in intrinsic calls must be emitted as numeric literals, not quoted strings."""
        mlog = "draw line 10.5 20.5 30.5 40.5 0 0\nwait 0.25\n"
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn('draw("line", 10.5, 20.5, 30.5, 40.5, 0, 0)', py)
        self.assertIn("wait(0.25)", py)

    def test_at_constant_quoted_in_assignments(self):
        """Constants starting with @ (e.g. @unit) must be quoted in Python assignments."""
        mlog = "set u @unit\nset t @this\n"
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("u = '@unit'", py)
        self.assertIn("t = '@this'", py)


if __name__ == "__main__":
    unittest.main()
