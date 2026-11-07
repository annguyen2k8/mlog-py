"""Regression suite for P7 remediation.

Covers five independently reproduced findings:

- P7-CRIT-01: a nested conditional that exits to the enclosing else entry must
  not be emitted as a one-sided ``if``. The false edge is either flattened into
  a combined ``and`` condition or preserved as a raw conditional jump.
- P7-CRIT-02: bare ``@`` registers are emitted through ``raw()`` while quoted
  ``"@..."`` tokens stay Python string literals.
- P7-HIGH-01: a loop whose exit skips instructions is preserved as a raw region
  that resumes exactly at the recorded exit address.
- P7-MED-01: address 0 (the function-table preamble) has a coarse source
  mapping, so every instruction has provenance.
- P7-MED-02: ``FunctionDef`` mappings are coarse and do not inflate
  statement-level coverage.
"""

import ast
import os
import unittest

from src.decompiler import decompile, decompile_with_source_map
from src.decompiler.expression import ConstantExpr
from src.decompiler.parser import parse_mlog
from src.decompiler.structured_ir import format_operand
from src.mlog import compile_py

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(REPO_ROOT, "tests", "corpus")

FUNCTION_CORPUS = (
    "compiler_generated/large_compiler_program.mlog",
    "compiler_generated/multi_func_math.mlog",
    "compiler_generated/recursive_factorial.mlog",
    "functions/func_with_loop.mlog",
    "functions/nested_calls.mlog",
    "functions/recursion.mlog",
    "functions/two_functions.mlog",
)


def _read_corpus(relative_path):
    with open(os.path.join(CORPUS, relative_path), "r", encoding="utf-8") as handle:
        return handle.read()


def _normalized_lines(text):
    return [line.strip() for line in text.strip().splitlines()]


def _recompile(py):
    return compile_py(py, allow_functions=True, validate=True).mlog


class TestP7Crit01DroppedElse(unittest.TestCase):
    """The nested false edge must reach the enclosing else entry."""

    def test_arithmetic_dataflow_variant_flattens_else_edge(self):
        original = _read_corpus("compiler_generated/arithmetic_dataflow.mlog")
        variant = original.replace("set a 10", "set a 30")

        py, source_map = decompile_with_source_map(variant)
        ast.parse(py)
        self.assertIn("if y > 100 and x < 500:", py)
        self.assertIn("    res = 1", py)
        self.assertIn("    res = 0", py)

        # Address 16 is the inner conditional; address 19 is the else entry.
        self.assertIn("jump 19 greaterThanEq x 500", _recompile(py))
        mapped = {
            address
            for mapping in source_map.mappings
            for address in mapping.mlog_addresses
        }
        self.assertIn(16, mapped)
        self.assertIn(19, mapped)

        recompiled = _recompile(py)
        self.assertEqual(_normalized_lines(recompiled), _normalized_lines(variant))

    def test_short_circuit_variant_preserves_inner_false_edge(self):
        original = _read_corpus("control_flow/short_circuit_ladder.mlog")
        variant = original.replace("set a 1", "set a 5").replace("set d 4", "set d 5")

        py = decompile(variant)
        ast.parse(py)
        self.assertIn("# [UNSTRUCTURED REGION]", py)
        self.assertIn('jump(9, "lessThan", b, c)', py)
        self.assertIn("if c < d and d == 4:", py)
        self.assertIn('flag = op("sub", 0, 1)', py)

        recompiled = _recompile(py)
        self.assertEqual(_normalized_lines(recompiled), _normalized_lines(variant))

    def test_reactor_safety_variant_keeps_alert_else(self):
        original = _read_corpus("handwritten/reactor_safety.mlog")
        variant = original.replace(
            "sensor heat reactor1 @heat", "set heat 0.5"
        ).replace("sensor cryo reactor1 @cryofluid", "set cryo 20")

        py = decompile(variant)
        ast.parse(py)
        self.assertIn("if cryo >= 10 and heat <= 0.2:", py)
        self.assertIn('print("ALERT: Reactor Overheating")', py)
        self.assertIn('print("Reactor Status: Nominal")', py)

        recompiled = _recompile(py)
        self.assertEqual(_normalized_lines(recompiled), _normalized_lines(variant))

    def test_deferred_conditional_materializes_without_dropping_edge(self):
        # The then-body contains a statement before the deferred conditional,
        # so flattening into one condition would change execution order. The
        # conditional must stay a raw jump whose false edge still reaches the
        # enclosing else entry at address 8.
        mlog = (
            "set a 10\n"
            "jump 8 lessThanEq a 0\n"
            "set t 1\n"
            "jump 8 greaterThan b 0\n"
            "set r 1\n"
            "set z 2\n"
            "set w 3\n"
            "jump 9 always 0 0\n"
            "set r 0\n"
            "end\n"
        )
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("Deferred conditional jump to enclosing else entry at address 8", py)
        self.assertIn('jump(8, "greaterThan", b, 0)', py)
        self.assertIn("    t = 1", py)
        self.assertIn("    r = 0", py)

        self.assertEqual(_normalized_lines(_recompile(py)), _normalized_lines(mlog))


class TestP7Crit02BareRegisters(unittest.TestCase):
    """Bare @ tokens are registers; quoted "@..." tokens are strings."""

    def test_format_operand_marks_bare_registers_raw(self):
        self.assertEqual(format_operand("@counter"), 'raw("@counter")')
        self.assertEqual(format_operand("@unit"), 'raw("@unit")')
        self.assertEqual(format_operand("@time"), 'raw("@time")')
        # Non-register operands keep their existing formatting.
        self.assertEqual(format_operand("true"), "True")
        self.assertEqual(format_operand("null"), "None")
        self.assertEqual(format_operand("value"), "value")

    def test_constant_expr_distinguishes_bare_and_quoted_registers(self):
        bare = ConstantExpr(value="@unit", raw_str="@unit")
        quoted = ConstantExpr(value="@unit", raw_str='"@unit"')
        self.assertEqual(bare.to_python(), 'raw("@unit")')
        self.assertEqual(quoted.to_python(), "'@unit'")

    def test_set_register_value_roundtrips(self):
        mlog = "set x @counter\n"
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn('x = raw("@counter")', py)
        self.assertNotIn("'@counter'", py)
        self.assertEqual(_recompile(py).strip(), mlog.strip())

    def test_set_register_destination_roundtrips(self):
        mlog = "set @counter 10\n"
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn('set(raw("@counter"), 10)', py)
        self.assertEqual(_recompile(py).strip(), mlog.strip())

    def test_quoted_destination_stays_valid_python(self):
        mlog = 'set "@foo" 1\n'
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn('set("\\"@foo\\"", 1)', py)
        self.assertEqual(_recompile(py).strip(), mlog.strip())

    def test_op_register_operand_roundtrips(self):
        mlog = "op add x @time 1\n"
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn('x = raw("@time") + 1', py)
        self.assertEqual(_recompile(py).strip(), mlog.strip())

    def test_computed_jump_counter_uses_live_register(self):
        mlog = _read_corpus("pathological/computed_jump_counter.mlog")
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn(
            'op("add", raw("@counter"), raw("@counter"), offset)', py
        )
        self.assertNotIn("'@counter'", py)
        self.assertEqual(_normalized_lines(_recompile(py)), _normalized_lines(mlog))

    def test_jump_condition_register_is_not_a_string(self):
        mlog = "jump 2 equal @unit null\nset x 1\nset x 2\n"
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn('if raw("@unit") != None:', py)
        self.assertNotIn("'@unit'", py)
        self.assertEqual(_normalized_lines(_recompile(py)), _normalized_lines(mlog))

    def test_quoted_register_literal_stays_a_string(self):
        mlog = 'set x "@unit"\n'
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("x = '@unit'", py)
        self.assertNotIn("raw(", py)
        self.assertEqual(_recompile(py).strip(), mlog.strip())


class TestP7High01LoopGap(unittest.TestCase):
    """Loop exits that skip instructions must resume at exit_address."""

    def test_base_manager_gaps_are_raw_and_resume_at_exit(self):
        mlog = _read_corpus("handwritten/base_manager_120.mlog")
        py, source_map = decompile_with_source_map(mlog)
        ast.parse(py)

        self.assertIn(
            "Loop exit at address 22 skips instructions [20, 22)", py
        )
        self.assertIn(
            "Loop exit at address 36 skips instructions [33, 36)", py
        )
        # The raw region keeps the exact guard and latch targets.
        self.assertIn('jump(22, "greaterThanEq", turret_idx, 4)', py)
        self.assertIn('jump(18, "always", 0, 0)  # addr 15', py)
        self.assertIn('jump(8, "always", 0, 0)  # addr 19', py)
        self.assertIn('jump(36, "greaterThanEq", cell_idx, 8)', py)
        self.assertIn('jump(27, "always", 0, 0)  # addr 32', py)

        instructions = parse_mlog(mlog)
        self.assertEqual(source_map.missing_addresses(len(instructions)), [])
        self.assertEqual(source_map.missing_addresses(len(instructions), include_coarse=False), [])

        recompiled = _recompile(py)
        self.assertEqual(len(recompiled.strip().splitlines()), 120)
        self.assertEqual(_normalized_lines(recompiled), _normalized_lines(mlog))

    def test_normal_loop_without_gap_stays_structured(self):
        mlog = _read_corpus("control_flow/nested_while_breaks.mlog")
        py = decompile(mlog)
        ast.parse(py)
        self.assertIn("while outer < 5:", py)
        self.assertIn("while inner < 4:", py)
        self.assertNotIn("Loop exit at address", py)


class TestP7Low02CorpusValidity(unittest.TestCase):
    """The corpus must exercise the intended paths and be engine-valid."""

    def test_base_manager_counter_path_exits_and_roundtrips(self):
        mlog = _read_corpus("handwritten/base_manager_120.mlog")
        self.assertIn("jump 18 always 0 0", mlog)

        py = decompile(mlog)
        ast.parse(py)
        recompiled = _recompile(py)
        self.assertEqual(_normalized_lines(recompiled), _normalized_lines(mlog))

    def test_flare_miner_uses_valid_storage_group(self):
        mlog = _read_corpus("handwritten/flare_miner.mlog")
        self.assertIn("ulocate building storage", mlog)
        self.assertNotIn("ulocate building container", mlog)

        py = decompile(mlog)
        ast.parse(py)
        self.assertIn('ulocate.building("storage", 0)', py)
        recompiled = _recompile(py)
        self.assertIn(
            "ulocate building storage 0 @copper cx cy found cblock", recompiled
        )


class TestP7SourceMapCoverage(unittest.TestCase):
    """Address-level and statement-level coverage are reported separately."""

    def test_function_files_map_every_address_including_preamble(self):
        for relative_path in FUNCTION_CORPUS:
            with self.subTest(file=relative_path):
                mlog = _read_corpus(relative_path)
                total = len(parse_mlog(mlog))
                _, source_map = decompile_with_source_map(mlog, filename=relative_path)

                self.assertEqual(source_map.missing_addresses(total), [])
                self.assertIsNotNone(source_map.mlog_to_python(0))

                summary = source_map.coverage_summary(total)
                self.assertEqual(summary["total_instructions"], total)
                self.assertEqual(summary["address_missing"], [])
                self.assertEqual(summary["address_coverage"], 1.0)

                # Only the structural address 0 lacks a statement-level map.
                self.assertEqual(summary["statement_missing"], [0])
                self.assertEqual(summary["statement_mapped"], total - 1)

                statement_addresses = set(
                    source_map.mapped_addresses(include_coarse=False)
                )
                self.assertEqual(statement_addresses, set(range(1, total)))

    def test_function_def_mappings_are_coarse(self):
        for relative_path in FUNCTION_CORPUS:
            with self.subTest(file=relative_path):
                mlog = _read_corpus(relative_path)
                _, source_map = decompile_with_source_map(mlog, filename=relative_path)

                function_defs = [
                    mapping
                    for mapping in source_map.mappings
                    if mapping.node_type == "FunctionDef"
                ]
                self.assertTrue(function_defs)
                for mapping in function_defs:
                    self.assertTrue(mapping.is_coarse)
                    self.assertTrue(mapping.mlog_addresses)

    def test_reverse_map_prefers_statement_over_coarse_function_def(self):
        mlog = _read_corpus("functions/two_functions.mlog")
        py, source_map = decompile_with_source_map(mlog)
        lines = py.splitlines()

        # Address 1 belongs to `add`; the precise `Return` mapping wins over
        # the coarse FunctionDef mapping for the same range.
        self.assertEqual(source_map.mlog_to_python(0), 1)
        self.assertEqual(source_map.mlog_to_python(1), 2)
        self.assertEqual(lines[1].strip(), "return a + b")

        data = source_map.to_dict()
        self.assertIn("0", data["mlog_to_python"])
        self.assertEqual(data["mlog_to_python"]["0"], 1)
        self.assertEqual(data["mlog_to_python"]["1"], 2)

        preamble = [
            mapping
            for mapping in data["mappings"]
            if mapping["mlog_addresses"] == [0]
        ]
        self.assertEqual(len(preamble), 1)
        self.assertTrue(preamble[0].get("is_coarse"))


if __name__ == "__main__":
    unittest.main()
