"""Regression tests for compiler-temporary handling in the decompiler.

Background
----------
The compiler allocates scratch registers named ``__tmp0``, ``__tmp1``, ... The parser
rejects those names in user source (``Compiler.format_name``), so any decompiled
program that preserved a temporary under its raw name produced Python the compiler
refused to recompile, breaking the MLog -> Python -> MLog round-trip.

Two cooperating mechanisms now guarantee a round-trippable result:

1. Expression recovery (:mod:`src.decompiler.dataflow`) folds a single-use temporary
   into a raw instruction operand when the operand position is a plain ``OPERAND`` and
   the rendered value is a pure arithmetic expression. The renderer
   (:func:`src.decompiler.semantics.format_semantic_argument`) accepts that operand via
   the shared ``is_safe_inline_expression`` predicate instead of re-quoting it as text.
2. Any temporary that survives folding is renamed to a valid DSL identifier
   (:mod:`src.decompiler.naming`), one-to-one and consistently across every use.
"""

import ast
import glob
import os
import re
import unittest

from src.decompiler import decompile
from src.decompiler.naming import RENAMED_TEMPORARY_PREFIX
from src.decompiler.semantics import format_semantic_argument, is_safe_inline_expression
from src.mlog import compile_py


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RESERVED_PREFIX = "__tmp"

# Compiler examples whose MLog -> Python -> MLog round-trip is byte-for-byte exact.
EXPECTED_BYTE_EXACT = (
    "bitwise.mlog",
    "block_vs_variable.mlog",
    "color_channels.mlog",
    "conditionals.mlog",
    "constant_folding.mlog",
    "control_building.mlog",
    "display_graphics.mlog",
    "for_loop.mlog",
    "functions.mlog",
    "memory_cell.mlog",
    "min_max.mlog",
    "nested_loops.mlog",
    "print_message.mlog",
    "reactor_safety.mlog",
    "unit_operations.mlog",
    "while_loop.mlog",
)

# Compiler examples that round-trip to valid, semantically equivalent Python but not
# to byte-identical MLog. See the test that uses this tuple for the per-case reasons.
EXPECTED_VALID_ONLY = (
    "arithmetic.mlog",
    "array_memory.mlog",
    "aug_assign.mlog",
    "special_constants.mlog",
)


def _roundtrip_status(mlog: str) -> str:
    """Return 'RT-OK' when decompiled+recompiled mlog is byte-identical, else 'RT-VALID'."""
    py = decompile(mlog, filename="t.mlog")
    recompiled = compile_py(py, filename="t.py", allow_functions=True).mlog
    return "RT-OK" if recompiled.strip() == mlog.strip() else "RT-VALID"


def _assert_no_reserved_temporaries(case, py: str) -> None:
    """Fail if any '__tmp' identifier survives outside of a string literal."""
    tree = ast.parse(py)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            case.assertFalse(
                node.id.startswith(RESERVED_PREFIX),
                f"reserved compiler temporary {node.id!r} leaked into decompiled output",
            )
        if isinstance(node, ast.Attribute):
            case.assertFalse(
                node.attr.startswith(RESERVED_PREFIX),
                f"reserved compiler temporary {node.attr!r} leaked into decompiled output",
            )
        if isinstance(node, ast.FunctionDef):
            case.assertFalse(node.name.startswith(RESERVED_PREFIX))


class TestStatusBooleanLiteralRoundTrip(unittest.TestCase):
    """status token 1 is a Java boolean literal, not a numeric flag."""

    def test_status_boolean_literals_roundtrip_byte_exact(self):
        for mlog in (
            "status true @status-burning u 5\n",
            "status false @status-burning u 5\n",
            "status true @status-wet u 0\n",
            "status false @status-wet u 0\n",
        ):
            with self.subTest(mlog=mlog.strip()):
                self.assertEqual(_roundtrip_status(mlog), "RT-OK")


class TestInlineExpressionPredicate(unittest.TestCase):
    """The renderer/inliner predicate deciding what may be emitted as an expression."""

    def test_arithmetic_and_bitwise_expressions_accepted(self):
        for token in (
            "r + g + b + a",
            "2*3",
            "-x",
            "~y",
            "x ** 2",
            "a // b",
            "a % b",
            "a << 2",
            "a | b",
            "a & b",
            "a ^ b",
            "x - y - z",
        ):
            with self.subTest(token=token):
                self.assertTrue(is_safe_inline_expression(token))

    def test_bare_identifier_is_not_an_expression(self):
        # Handled by the earlier identifier branch of the renderer.
        self.assertFalse(is_safe_inline_expression("x"))

    def test_rejected_tokens(self):
        for token in (
            "",
            "  x + 1  ",
            "f(x)",
            "x[0]",
            '"s"',
            "'s'",
            "x > 1",
            "x and y",
            "True",
            "x.y",
            "1 if x else 2",
            "x; y",
            "x + ",
        ):
            with self.subTest(token=token):
                self.assertFalse(is_safe_inline_expression(token))

    def test_renderer_emits_expression_unquoted(self):
        args = ("r + g + b + a",)
        out = format_semantic_argument("print", 0, args[0], None, args)
        self.assertEqual(out, "r + g + b + a")

    def test_renderer_still_quotes_real_string_literals(self):
        self.assertEqual(format_semantic_argument("print", 0, '"hello"', None, ('"hello"',)), '"hello"')

    def test_renderer_still_quotes_enum_selectors(self):
        args = ("ore", "core", "true", "@copper")
        out = format_semantic_argument("ulocate", 1, args[1], None, args)
        self.assertEqual(out, '"core"')


class TestTemporaryInliningIntoInstructions(unittest.TestCase):
    """Single-use temporaries feeding a raw instruction operand are recovered."""

    def test_multi_operator_expression_into_print_is_byte_exact(self):
        mlog = "op add __tmp0 a b\nop sub __tmp1 __tmp0 c\nop mul __tmp2 __tmp1 2\nprint __tmp2\n"
        py = decompile(mlog, filename="t.mlog")
        self.assertIn("print((a + b - c) * 2)", py)
        self.assertEqual(_roundtrip_status(mlog), "RT-OK")

    def test_nested_expression_chain_fully_folded(self):
        mlog = "op mul __tmp0 a b\nop add __tmp1 __tmp0 1\nop sub res __tmp1 a\n"
        py = decompile(mlog, filename="t.mlog")
        self.assertEqual(py.strip().splitlines()[-1], "res = a * b + 1 - a")
        self.assertEqual(_roundtrip_status(mlog), "RT-OK")

    def test_unary_operator_expression_into_print_is_byte_exact(self):
        mlog = "op add __tmp0 a b\nop not __tmp1 __tmp0 0\nprint __tmp1\n"
        py = decompile(mlog, filename="t.mlog")
        self.assertIn("print(~(a + b))", py)
        self.assertEqual(_roundtrip_status(mlog), "RT-OK")

    def test_write_operand_expression_is_byte_exact(self):
        mlog = "op add __tmp0 a b\nwrite __tmp0 cell1 0\n"
        py = decompile(mlog, filename="t.mlog")
        self.assertIn('write(a + b, "cell1", 0)', py)
        self.assertEqual(_roundtrip_status(mlog), "RT-OK")

    def test_comparison_operand_is_not_folded_into_string(self):
        """A comparison is not an inline expression, so it must stay an assignment."""
        mlog = "op greaterThanEq __tmp0 i 3\nwrite __tmp0 cell1 0\n"
        py = decompile(mlog, filename="t.mlog")
        self.assertNotIn('"i >= 3"', py)
        _assert_no_reserved_temporaries(self, py)
        self.assertEqual(_roundtrip_status(mlog), "RT-VALID")

    def test_control_flow_operand_is_never_rewritten(self):
        """Jump operands are instruction addresses/conditions, never expressions."""
        from src.decompiler.dataflow import inline_temporary_into_instruction
        from src.decompiler.expression import BinaryExpr, VariableExpr
        from src.decompiler.instruction import MlogInstruction
        from src.errors import SourceLocation

        expr = BinaryExpr(op="+", left=VariableExpr(name="a"), right=VariableExpr(name="b"))
        for opcode, args in (
            ("jump", ("__tmp0", "always", "0", "0")),
            ("stop", ()),
            ("end", ()),
        ):
            with self.subTest(opcode=opcode):
                instr = MlogInstruction(
                    address=0,
                    opcode=opcode,
                    args=args,
                    loc=SourceLocation(filename="t", line=1, col=1),
                )
                self.assertIsNone(inline_temporary_into_instruction(instr, "__tmp0", expr))

    def test_control_flow_program_keeps_condition_intact(self):
        mlog = "op add __tmp0 i 1\nset x __tmp0\nop add y i 2\njump 0 greaterThanEq __tmp0 5\n"
        py = decompile(mlog, filename="t.mlog")
        _assert_no_reserved_temporaries(self, py)
        self.assertEqual(_roundtrip_status(mlog), "RT-VALID")

    def test_destination_operand_is_never_replaced_by_expression(self):
        """'set __tmp0 7' is a write; it must stay a plain variable reference."""
        mlog = "op add __tmp0 a b\nset __tmp0 7\nprint __tmp0\n"
        py = decompile(mlog, filename="t.mlog")
        _assert_no_reserved_temporaries(self, py)
        self.assertEqual(_roundtrip_status(mlog), "RT-VALID")


class TestSharedTemporaryRenaming(unittest.TestCase):
    """A temporary used more than once is preserved and renamed consistently."""

    def test_shared_temporary_preserved_and_renamed(self):
        mlog = "op add __tmp0 a b\nop mul x __tmp0 2\nop add y __tmp0 3\n"
        py = decompile(mlog, filename="t.mlog")
        names = re.findall(rf"^({RENAMED_TEMPORARY_PREFIX}\d+) = ", py, flags=re.MULTILINE)
        self.assertEqual(len(names), 1)
        temp = names[0]
        self.assertIn(f"{temp} = a + b", py)
        self.assertIn(f"x = {temp} * 2", py)
        self.assertIn(f"y = {temp} + 3", py)
        _assert_no_reserved_temporaries(self, py)

    def test_multiple_distinct_temporaries_get_distinct_names(self):
        mlog = (
            "read __tmp0 cell1 0\nop add __tmp1 __tmp0 1\nwrite __tmp1 cell1 0\n"
            "read __tmp2 cell1 0\nop sub __tmp3 __tmp2 1\nwrite __tmp3 cell1 0\n"
        )
        py = decompile(mlog, filename="t.mlog")
        _assert_no_reserved_temporaries(self, py)
        names = set(re.findall(rf"({RENAMED_TEMPORARY_PREFIX}\d+)", py))
        self.assertEqual(len(names), 2, py)
        self.assertEqual(_roundtrip_status(mlog), "RT-VALID")

    def test_renamed_name_never_collides_with_existing_variable(self):
        mlog = "set tmp_val_0 99\nread __tmp0 cell1 0\nwrite __tmp0 cell1 0\n"
        py = decompile(mlog, filename="t.mlog")
        _assert_no_reserved_temporaries(self, py)
        temp = re.findall(r"(\w+) = read\(", py)
        self.assertEqual(len(temp), 1)
        self.assertNotEqual(temp[0], "tmp_val_0")
        self.assertEqual(_roundtrip_status(mlog), "RT-VALID")

    def test_ulocate_discarded_output_stays_elided(self):
        """The 4th ulocate output is scratch; the renderer drops it, round-trip stays exact."""
        mlog = "ulocate ore core true @copper ore_x ore_y found_ore __tmp0\n"
        py = decompile(mlog, filename="t.mlog")
        self.assertIn("ore_x, ore_y, found_ore = ulocate.ore(\"@copper\")", py)
        self.assertEqual(_roundtrip_status(mlog), "RT-OK")

    def test_ulocate_with_real_building_target_keeps_four_targets(self):
        mlog = "ulocate building core false @copper ore_x ore_y found_ore core_build\n"
        py = decompile(mlog, filename="t.mlog")
        self.assertIn("core_build", py)
        self.assertEqual(_roundtrip_status(mlog), "RT-OK")

    def test_temporaries_inside_while_body_are_renamed(self):
        mlog = (
            "set i 0\n"
            "jump 7 greaterThanEq i 4\n"
            "read __tmp0 cell1 i\n"
            "op add __tmp1 __tmp0 1\n"
            "write __tmp1 cell1 i\n"
            "op add i i 1\n"
            "jump 2 always 0 0\n"
        )
        py = decompile(mlog, filename="t.mlog")
        _assert_no_reserved_temporaries(self, py)
        self.assertEqual(_roundtrip_status(mlog), "RT-VALID")

    def test_temporaries_inside_function_body_are_renamed(self):
        mlog = (
            "jump 6 always 0 0\n"
            "read __tmp0 cell1 0\n"
            "op add __retval_helper __tmp0 1\n"
            "set @counter __ret_helper\n"
            "set cell1 0\n"
            "set @counter 4\n"
        )
        py = decompile(mlog, filename="t.mlog")
        ast.parse(py)
        _assert_no_reserved_temporaries(self, py)


class TestCompilerExampleRoundtrip(unittest.TestCase):
    """Every shipped compiler example must decompile to valid, recompilable Python."""

    @classmethod
    def setUpClass(cls):
        cls.examples = sorted(glob.glob(os.path.join(REPO_ROOT, "examples", "compiler", "*.mlog")))

    def test_examples_discovered(self):
        self.assertGreaterEqual(len(self.examples), 19)

    def test_every_example_roundtrips_to_recompilable_python(self):
        for mlog_path in self.examples:
            with self.subTest(example=os.path.basename(mlog_path)):
                with open(mlog_path, "r", encoding="utf-8") as f:
                    mlog = f.read()
                py = decompile(mlog, filename=mlog_path)
                ast.parse(py)
                _assert_no_reserved_temporaries(self, py)
                # Must recompile without raising CompileError.
                compile_py(py, filename="rt.py", allow_functions=True)

    def test_color_channels_roundtrips_byte_for_byte(self):
        mlog_path = os.path.join(REPO_ROOT, "examples", "compiler", "color_channels.mlog")
        with open(mlog_path, "r", encoding="utf-8") as f:
            mlog = f.read()
        py = decompile(mlog, filename=mlog_path)
        self.assertIn("print(r + g + b + a)", py)
        recompiled = compile_py(py, filename="rt.py").mlog
        self.assertEqual(recompiled.strip(), mlog.strip())

    def test_examples_without_preserved_temporaries_roundtrip_byte_for_byte(self):
        """Golden split between byte-exact and semantically-valid-only round-trips.

        The four RT-VALID entries are not caused by temporaries:
          * arithmetic, special_constants -- pre-existing divergences unrelated to
            temporary handling (redundant 'set' elimination and '@'-token quoting).
          * array_memory, aug_assign -- a read feeding a write inside a loop cannot be
            proven side-effect-free, so the temporary is preserved under a renamed
            identifier and the recompile gains an explicit 'set'.
        """
        for basename in sorted(EXPECTED_BYTE_EXACT):
            with self.subTest(example=basename):
                mlog_path = os.path.join(REPO_ROOT, "examples", "compiler", basename)
                with open(mlog_path, "r", encoding="utf-8") as f:
                    self.assertEqual(_roundtrip_status(f.read()), "RT-OK", basename)

        for basename in sorted(EXPECTED_VALID_ONLY):
            with self.subTest(example=basename):
                mlog_path = os.path.join(REPO_ROOT, "examples", "compiler", basename)
                with open(mlog_path, "r", encoding="utf-8") as f:
                    self.assertEqual(_roundtrip_status(f.read()), "RT-VALID", basename)

        covered = set(EXPECTED_BYTE_EXACT) | set(EXPECTED_VALID_ONLY)
        discovered = {os.path.basename(p) for p in self.examples}
        self.assertEqual(covered, discovered, "example round-trip classification is stale")


class TestRenamingDoesNotAffectCompilerDirection(unittest.TestCase):
    """Renaming is a decompiler concern; Python -> MLog output must be untouched."""

    def test_color_channels_python_still_compiles_byte_for_byte(self):
        py_path = os.path.join(REPO_ROOT, "examples", "compiler", "color_channels.py")
        mlog_path = os.path.join(REPO_ROOT, "examples", "compiler", "color_channels.mlog")
        with open(py_path, "r", encoding="utf-8") as f:
            source = f.read()
        with open(mlog_path, "r", encoding="utf-8") as f:
            expected = f.read()
        self.assertEqual(compile_py(source, filename="color_channels.py").mlog.strip(), expected.strip())

    def test_user_code_may_still_use_tmp_val_prefix(self):
        res = compile_py("tmp_val_0 = 5\ny = tmp_val_0 + 1\n")
        self.assertIn("set tmp_val_0 5", res.mlog)


if __name__ == "__main__":
    unittest.main()