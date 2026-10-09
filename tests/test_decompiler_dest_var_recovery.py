"""Regression tests for destination variable recovery in Mindustry Logic decompiler.

Verifies:
- All opcodes with destination variables (read, sensor, op, set, getlink, lookup, packcolor, radar, uradar)
  are decompiled to Python assignment form (dest = ...).
- Destination variables are defined as ast.Store targets before being read as ast.Load, preventing NameError.
- Program variables are unquoted identifiers; hardware links remain quoted string literals.
- Multiple definitions, re-assignments, and branch assignments work correctly.
- Roundtrip decompilation and compilation preserves semantic equivalence.
"""

import ast
import unittest

from src.decompiler import decompile
from src.mlog import compile_py


class TestDecompilerDestVarRecovery(unittest.TestCase):
    """Verify destination variables are properly recovered as assignment targets."""

    def _assert_no_undefined_variables(self, code: str, allowed_globals=None):
        """Analyze AST to guarantee every loaded variable is defined via Store or Import."""
        tree = ast.parse(code)
        defined = set(allowed_globals or set())
        used = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                defined.add(node.name)
                for a in node.args.args:
                    defined.add(a.arg)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    defined.add(alias.asname or alias.name)
            elif isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Store):
                    defined.add(node.id)
                elif isinstance(node.ctx, ast.Load):
                    used.add(node.id)

        undefined = used - defined
        self.assertEqual(
            undefined,
            set(),
            f"Found undefined variables {undefined} in generated code:\n{code}",
        )

    def test_read_destination_assignment(self):
        """read dest cell addr must decompile to dest = read(cell, addr)."""
        mlog = "read val cell1 0\n"
        py = decompile(mlog)
        self._assert_no_undefined_variables(py)
        self.assertIn('val = read("cell1", 0)', py)
        self.assertNotIn('read(val', py)

        # Recompile check
        recompiled = compile_py(py).mlog.strip()
        self.assertEqual(recompiled, "read val cell1 0")

    def test_sensor_destination_assignment(self):
        """sensor dest block prop must decompile to dest = sensor(block, prop)."""
        mlog = "sensor hp reactor1 @heat\n"
        py = decompile(mlog)
        self._assert_no_undefined_variables(py)
        self.assertIn('hp = sensor("reactor1", \'@heat\')', py)
        self.assertNotIn('sensor(hp', py)

        # Recompile check
        recompiled = compile_py(py).mlog.strip()
        self.assertEqual(recompiled, "sensor hp reactor1 @heat")

    def test_getlink_destination_assignment(self):
        """getlink dest index must decompile to dest = getlink(index)."""
        mlog = "getlink b 0\n"
        py = decompile(mlog)
        self._assert_no_undefined_variables(py)
        self.assertIn("b = getlink(0)", py)
        self.assertNotIn("getlink(b", py)

        # Recompile check
        recompiled = compile_py(py).mlog.strip()
        self.assertEqual(recompiled, "getlink b 0")

    def test_lookup_destination_assignment(self):
        """lookup type dest index must decompile to dest = lookup(type, index)."""
        mlog = "lookup item it 0\n"
        py = decompile(mlog)
        self._assert_no_undefined_variables(py)
        self.assertIn('it = lookup("item", 0)', py)
        self.assertNotIn("lookup(item, it", py)

        # Recompile check
        recompiled = compile_py(py).mlog.strip()
        self.assertEqual(recompiled, "lookup item it 0")

    def test_packcolor_destination_assignment(self):
        """packcolor dest r g b a must decompile to dest = packcolor(r, g, b, a)."""
        mlog = "packcolor col 1 0 0 1\n"
        py = decompile(mlog)
        self._assert_no_undefined_variables(py)
        self.assertIn("col = packcolor(1, 0, 0, 1)", py)
        self.assertNotIn("packcolor(col", py)

        # Recompile check
        recompiled = compile_py(py).mlog.strip()
        self.assertEqual(recompiled, "packcolor col 1 0 0 1")

    def test_radar_destination_assignment(self):
        """radar filters turret order dest must decompile to dest = radar(...)."""
        mlog = "radar enemy any any distance cyclone1 1 target\n"
        py = decompile(mlog)
        self._assert_no_undefined_variables(py)
        self.assertIn('target = radar("enemy", "any", "any", "distance", "cyclone1", 1)', py)
        self.assertNotIn("radar(enemy, any, any, distance, \"cyclone1\", 1, target)", py)

        # Recompile check
        recompiled = compile_py(py).mlog.strip()
        self.assertEqual(recompiled, "radar enemy any any distance cyclone1 1 target")

    def test_uradar_destination_assignment(self):
        """uradar filters order dest must decompile to dest = uradar(...)."""
        mlog = "uradar enemy any any distance 0 1 target\n"
        py = decompile(mlog)
        self._assert_no_undefined_variables(py)
        self.assertIn('target = uradar("enemy", "any", "any", "distance", 1)', py)
        self.assertNotIn("uradar(enemy, any, any, distance, 0, 1, target)", py)

        # Recompile check
        recompiled = compile_py(py).mlog.strip()
        self.assertEqual(recompiled, "uradar enemy any any distance 0 1 target")

    def test_op_destination_assignment(self):
        """op with logic functions must decompile to dest = op(...) or expression."""
        mlog = "op max res a b\n"
        py = decompile(mlog, filename="<test>")
        # In a scope with existing operands a and b
        full_mlog = """set a 10
set b 20
op max res a b
"""
        py = decompile(full_mlog)
        self._assert_no_undefined_variables(py)
        self.assertIn('res = op("max", a, b)', py)
        self.assertNotIn('op("max", res', py)

    def test_variable_reassigned_multiple_times(self):
        """Variables overwritten multiple times must be assigned sequentially."""
        mlog = """read val cell1 0
op add val val 1
write val cell1 0
op add val val 2
write val cell1 1
"""
        py = decompile(mlog)
        self._assert_no_undefined_variables(py)
        self.assertIn('val = read("cell1", 0)', py)
        self.assertIn("val = val + 1", py)
        self.assertIn("val = val + 2", py)

        recompiled = compile_py(py).mlog.strip().splitlines()
        self.assertEqual(len(recompiled), 5)

    def test_variable_assigned_in_branches(self):
        """Variables assigned within if/else branches must be validly scoped."""
        mlog = """sensor heat reactor1 @heat
jump 4 greaterThan heat 0.8
set status 0
jump 5 always 0 0
set status 1
write status cell1 0
"""
        py = decompile(mlog)
        self._assert_no_undefined_variables(py)
        self.assertIn('heat = sensor("reactor1", \'@heat\')', py)
        self.assertIn("status = 1", py)
        self.assertIn("status = 0", py)
        self.assertIn('write(status, "cell1", 0)', py)


    def test_unary_op_dummy_operand_removal_rand_round(self):
        """Unary operations like rand and round must omit the dummy b operand and prevent NameError."""
        mlog = """set wB 100
op rand xM wB b
op round xM xM b
"""
        py = decompile(mlog)
        self._assert_no_undefined_variables(py)
        self.assertIn('xM = op("rand", wB)', py)
        self.assertIn('xM = op("round", xM)', py)
        self.assertNotIn('op("rand", wB, b)', py)
        self.assertNotIn('op("round", xM, b)', py)

        recompiled = compile_py(py).mlog.strip()
        self.assertIn("op rand xM wB", recompiled)
        self.assertIn("op round xM xM", recompiled)

    def test_draw_stroke_and_control_enabled_no_undefined_names(self):
        """draw(stroke, ...) and control(enabled, ...) must emit quoted strings to avoid undefined NameErrors."""
        mlog = """draw stroke 1 0 255 255 0 0
control enabled reactor1 1 0 0 0
"""
        py = decompile(mlog)
        self._assert_no_undefined_variables(py)
        self.assertIn('draw("stroke", 1, 0, 255, 255, 0, 0)', py)
        self.assertIn('control("enabled", "reactor1", 1, 0, 0, 0)', py)

        recompiled = compile_py(py).mlog.strip()
        self.assertIn("draw stroke 1 0 255 255 0 0", recompiled)
        self.assertIn("control enabled reactor1 1 0 0 0", recompiled)

    def test_ucontrol_action_keyword_never_confused_with_variable(self):
        """ucontrol action keyword must always remain quoted even if a variable with same name exists."""
        mlog = """sensor flag @unit @flag
jump 2 equal flag 1
ucontrol flag 1 0 0 0 0
"""
        py = decompile(mlog)
        self.assertIn('ucontrol("flag", 1, 0, 0, 0, 0)', py)
        self.assertNotIn('ucontrol(flag,', py)
        recompiled = compile_py(py).mlog.strip()
        self.assertIn("ucontrol flag 1 0 0 0 0", recompiled)

    def test_ulocate_flag_building_type_quoted_no_undefined_name(self):
        """ulocate building types like 'container' and 'core' must be quoted string literals."""
        mlog = """ulocate building container 0 @copper cx cy found cblock
ulocate building core 0 @copper kx ky kfound kblock
"""
        py = decompile(mlog)
        self.assertIn('ulocate("building", "container", 0, "@copper", cx, cy, found, cblock)', py)
        self.assertIn('ulocate("building", "core", 0, "@copper", kx, ky, kfound, kblock)', py)
        recompiled = compile_py(py).mlog.strip()
        self.assertIn("ulocate building container 0 @copper cx cy found cblock", recompiled)
        self.assertIn("ulocate building core 0 @copper kx ky kfound kblock", recompiled)

    def test_control_properties_and_draw_types_always_quoted(self):
        """All ControlProperty and DrawType keywords must always be quoted string literals."""
        from src.mlog_registry_data import CONTROL_PROPERTIES, GRAPHICS_TYPES
        for prop in CONTROL_PROPERTIES:
            mlog = f"control {prop} reactor1 1 0 0 0\n"
            py = decompile(mlog)
            self.assertIn(f'control("{prop}", "reactor1", 1, 0, 0, 0)', py)

        for dtype in ("clear", "color", "stroke", "line", "rect"):
            mlog = f"draw {dtype} 0 0 0 0 0 0\n"
            py = decompile(mlog)
            self.assertIn(f'draw("{dtype}", 0, 0, 0, 0, 0, 0)', py)

    def test_unpackcolor_dest_variable_recovery(self):
        """unpackcolor destination variables must be tracked in dest vars."""
        from src.decompiler.parser import parse_mlog
        from src.decompiler.semantics import collect_program_defined_variables
        instrs = parse_mlog("unpackcolor r g b a col\n")
        defined = collect_program_defined_variables(instrs)
        self.assertEqual(defined, {"r", "g", "b", "a"})


if __name__ == "__main__":
    unittest.main()

