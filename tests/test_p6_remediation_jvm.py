"""JVM-backed regression tests for P6 remediation.

Runs decompiled/recompiled programs on the real Mindustry v160.7 LExecutor to
prove semantic equivalence, not just parser acceptance.
"""

import os
import unittest

from src.decompiler import decompile, decompile_with_source_map
from src.errors import CompileError
from src.mindustry_validator import is_mindustry_available, run_with_mindustry
from src.mlog import compile_py

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(REPO_ROOT, "tests", "corpus")


class TestP6RemediationJvm(unittest.TestCase):
    def setUp(self):
        if not is_mindustry_available():
            self.skipTest("Mindustry JVM harness is not available in this environment")

    def _roundtrip(self, mlog, max_steps=100):
        py = decompile(mlog)
        recompiled = compile_py(py, allow_functions=True, validate=True).mlog
        original_run = run_with_mindustry(mlog, max_steps=max_steps)
        recompiled_run = run_with_mindustry(recompiled, max_steps=max_steps)
        self.assertTrue(original_run.success, original_run.message)
        self.assertTrue(recompiled_run.success, recompiled_run.message)
        return recompiled, original_run, recompiled_run

    # ------------------------------------------------------------------
    # P6-CRIT-01
    # ------------------------------------------------------------------

    def test_crit01_program_terminator_runtime(self):
        mlog = "set a 1\njump 5 always 0 0\nset a 2\nset a 3\nprint a\n"
        recompiled, original, new = self._roundtrip(mlog)
        self.assertEqual(recompiled.strip().splitlines()[1], "end")
        self.assertEqual(original.vars.get("a"), 1.0)
        self.assertEqual(new.vars.get("a"), 1.0)
        self.assertEqual(original.text_buffer, new.text_buffer)
        self.assertEqual(original.ticks, new.ticks)

    def test_crit01_branch_boundary_runtime(self):
        mlog = (
            "set x 1\n"
            "jump 4 equal x 0\n"
            "jump 7 always 0 0\n"
            "set dead1 99\n"
            "set y 2\n"
            "set z 3\n"
            "set w 4\n"
            "print y\n"
            "print z\n"
        )
        _, original, new = self._roundtrip(mlog)
        for name in ("dead1", "y", "z", "w"):
            self.assertEqual(original.vars.get(name), new.vars.get(name), name)
        self.assertNotEqual(new.vars.get("dead1"), 99.0)
        self.assertEqual(original.text_buffer, new.text_buffer)

    def test_crit01_base_manager_loop_exit_runtime(self):
        path = os.path.join(CORPUS, "handwritten", "base_manager_120.mlog")
        with open(path, "r", encoding="utf-8") as handle:
            mlog = handle.read()
        py, source_map = decompile_with_source_map(mlog, filename=path)
        recompiled = compile_py(py, allow_functions=True, validate=True).mlog
        original = run_with_mindustry(mlog, max_steps=200)
        new = run_with_mindustry(recompiled, max_steps=200)
        self.assertTrue(original.success, original.message)
        self.assertTrue(new.success, new.message)

        changed = sorted(
            name
            for name in set(original.vars) | set(new.vars)
            if not name.startswith("__") and original.vars.get(name) != new.vars.get(name)
        )
        self.assertEqual(changed, [])
        self.assertEqual(original.messages, new.messages)

        mapped = set()
        for mapping in source_map.mappings:
            mapped.update(mapping.mlog_addresses)
        self.assertTrue({15, 20, 21} <= mapped)

    # ------------------------------------------------------------------
    # P6-CRIT-02
    # ------------------------------------------------------------------

    def test_crit02_call_in_expression_runtime(self):
        mlog = compile_py(
            "def inc(x):\n"
            "    return x + 1\n"
            "\n"
            "res = inc(4) + 1\n",
            allow_functions=True,
            validate=True,
        ).mlog
        run = run_with_mindustry(mlog)
        self.assertTrue(run.success, run.message)
        self.assertEqual(run.vars.get("res"), 6.0)

    def test_crit02_nested_call_runtime(self):
        mlog = compile_py(
            "def inc(x):\n"
            "    return x + 1\n"
            "\n"
            "res = inc(inc(4))\n",
            allow_functions=True,
            validate=True,
        ).mlog
        run = run_with_mindustry(mlog)
        self.assertTrue(run.success, run.message)
        self.assertEqual(run.vars.get("res"), 6.0)

    def test_crit02_multiple_calls_in_expression_runtime(self):
        mlog = compile_py(
            "def add(a, b):\n"
            "    return a + b\n"
            "\n"
            "def twice(x):\n"
            "    return add(x, x)\n"
            "\n"
            "res = twice(3) + add(1, 2)\n",
            allow_functions=True,
            validate=True,
        ).mlog
        run = run_with_mindustry(mlog)
        self.assertTrue(run.success, run.message)
        self.assertEqual(run.vars.get("res"), 9.0)

    def test_crit02_call_inside_return_runtime(self):
        mlog = compile_py(
            "def inc(x):\n"
            "    return x + 1\n"
            "\n"
            "def inc_twice(x):\n"
            "    return inc(inc(x))\n"
            "\n"
            "res = inc_twice(4)\n",
            allow_functions=True,
            validate=True,
        ).mlog
        run = run_with_mindustry(mlog)
        self.assertTrue(run.success, run.message)
        self.assertEqual(run.vars.get("res"), 6.0)

    def test_crit02_decompiled_call_expression_recompiles_and_runs(self):
        original = compile_py(
            "def inc(x):\n"
            "    return x + 1\n"
            "\n"
            "res = inc(4) + 1\n",
            allow_functions=True,
            validate=True,
        ).mlog
        py = decompile(original)
        self.assertIn("inc(", py)
        recompiled = compile_py(py, allow_functions=True, validate=True).mlog
        original_run = run_with_mindustry(original)
        new_run = run_with_mindustry(recompiled)
        self.assertTrue(original_run.success, original_run.message)
        self.assertTrue(new_run.success, new_run.message)
        self.assertEqual(original_run.vars.get("res"), 6.0)
        self.assertEqual(new_run.vars.get("res"), 6.0)

    # ------------------------------------------------------------------
    # P6-CRIT-03
    # ------------------------------------------------------------------

    def test_crit03_source_map_goto_runtime(self):
        path = os.path.join(CORPUS, "pathological", "spaghetti_goto.mlog")
        with open(path, "r", encoding="utf-8") as handle:
            mlog = handle.read()
        py, _ = decompile_with_source_map(mlog, filename=path)
        recompiled = compile_py(py, allow_functions=True, validate=True).mlog
        self.assertEqual(
            [line.strip() for line in recompiled.strip().splitlines()],
            [line.strip() for line in mlog.strip().splitlines()],
        )

        original = run_with_mindustry(mlog, max_steps=100)
        new = run_with_mindustry(recompiled, max_steps=100)
        self.assertTrue(original.success, original.message)
        self.assertTrue(new.success, new.message)
        self.assertEqual(original.message, new.message)
        self.assertEqual(original.message, "RUN_OK:100")
        for name in ("a", "b", "c", "d"):
            self.assertEqual(original.vars.get(name), new.vars.get(name), name)

    # ------------------------------------------------------------------
    # P6-HIGH-01
    # ------------------------------------------------------------------

    def test_high01_nested_non_recursive_calls_runtime(self):
        mlog = compile_py(
            "def inner(x):\n"
            "    return x * 2\n"
            "\n"
            "def outer(x):\n"
            "    return inner(x) + 1\n"
            "\n"
            "result = outer(4)\n",
            allow_functions=True,
            validate=True,
        ).mlog
        run = run_with_mindustry(mlog)
        self.assertTrue(run.success, run.message)
        self.assertEqual(run.vars.get("result"), 9.0)

    def test_high01_recursion_never_reaches_the_engine(self):
        with self.assertRaises(CompileError):
            compile_py(
                "def fact(n):\n"
                "    if n <= 1:\n"
                "        return 1\n"
                "    return n * fact(n - 1)\n"
                "\n"
                "result = fact(5)\n",
                allow_functions=True,
                validate=True,
            )


if __name__ == "__main__":
    unittest.main()
