"""Unit and integration tests for Semantic Argument Recovery in Mindustry Logic decompiler.

Verifies:
- Named block/device references (display1, cell1, message1, vault1, reactor1, cyclone1) are emitted
  as Python string literals ("display1", "cell1", etc.) instead of bare undefined variables.
- Program-defined variables holding blocks (e.g. from getlink) remain unquoted variable identifiers.
- Normal variables (x, y, total, val, idx) are NEVER converted to strings.
- Special constants (@unit, @counter, @health, @copper) are quoted string literals.
- Polymorphic opcodes (ucontrol itemDrop, itemTake, build, getBlock) properly resolve roles.
- Zero Guessing: unknown opcodes fallback safely without inventing device semantics.
- Full round-trip validation: MLog -> decompile -> ast.parse -> compile_py -> identical MLog.
"""

import ast
import unittest

from src.mlog import compile_py
from src.decompiler import (
    ArgumentSemanticRole,
    collect_program_defined_variables,
    decompile,
    format_semantic_argument,
    get_argument_semantic_role,
    get_instruction_dest_vars,
    get_instruction_read_vars,
    instruction_to_python,
    MlogInstruction,
    parse_mlog,
)


class TestSemanticArgumentRecovery(unittest.TestCase):
    """Test semantic role classification and argument formatting."""

    # -----------------------------------------------------------------------
    # 1. Semantic Role Classification
    # -----------------------------------------------------------------------

    def test_semantic_role_metadata_grounding(self):
        """Verify semantic roles directly grounded in INTRINSIC_DEFINITIONS."""
        # drawflush display
        self.assertEqual(get_argument_semantic_role("drawflush", 0), ArgumentSemanticRole.BLOCK_OR_DEVICE)

        # printflush message
        self.assertEqual(get_argument_semantic_role("printflush", 0), ArgumentSemanticRole.BLOCK_OR_DEVICE)

        # read dest cell address
        self.assertEqual(get_argument_semantic_role("read", 0, ("val", "cell1", "0")), ArgumentSemanticRole.VARIABLE_DEF)
        self.assertEqual(get_argument_semantic_role("read", 1, ("val", "cell1", "0")), ArgumentSemanticRole.BLOCK_OR_DEVICE)
        self.assertEqual(get_argument_semantic_role("read", 2, ("val", "cell1", "0")), ArgumentSemanticRole.OPERAND)

        # write input cell address
        self.assertEqual(get_argument_semantic_role("write", 0, ("total", "cell1", "63")), ArgumentSemanticRole.OPERAND)
        self.assertEqual(get_argument_semantic_role("write", 1, ("total", "cell1", "63")), ArgumentSemanticRole.BLOCK_OR_DEVICE)
        self.assertEqual(get_argument_semantic_role("write", 2, ("total", "cell1", "63")), ArgumentSemanticRole.OPERAND)

        # sensor dest block prop
        self.assertEqual(get_argument_semantic_role("sensor", 0, ("hp", "vault1", "@health")), ArgumentSemanticRole.VARIABLE_DEF)
        self.assertEqual(get_argument_semantic_role("sensor", 1, ("hp", "vault1", "@health")), ArgumentSemanticRole.BLOCK_OR_DEVICE)
        self.assertEqual(get_argument_semantic_role("sensor", 2, ("hp", "vault1", "@health")), ArgumentSemanticRole.KEYWORD_OR_ENUM)

        # control type target p1 p2 p3 p4
        self.assertEqual(get_argument_semantic_role("control", 0), ArgumentSemanticRole.KEYWORD_OR_ENUM)
        self.assertEqual(get_argument_semantic_role("control", 1), ArgumentSemanticRole.BLOCK_OR_DEVICE)

        # radar target1 target2 target3 sort turret sort_order output
        self.assertEqual(get_argument_semantic_role("radar", 4, ("enemy", "any", "any", "distance", "cyclone1", "1", "out")), ArgumentSemanticRole.BLOCK_OR_DEVICE)
        self.assertEqual(get_argument_semantic_role("radar", 6, ("enemy", "any", "any", "distance", "cyclone1", "1", "out")), ArgumentSemanticRole.VARIABLE_DEF)

    def test_ucontrol_polymorphic_roles(self):
        """Verify polymorphic ucontrol argument roles based on action."""
        # itemDrop to amount -> to is BLOCK_OR_DEVICE
        self.assertEqual(
            get_argument_semantic_role("ucontrol", 1, ("itemDrop", "container1", "10", "0", "0", "0")),
            ArgumentSemanticRole.BLOCK_OR_DEVICE,
        )
        # itemTake from item amount -> from is BLOCK_OR_DEVICE
        self.assertEqual(
            get_argument_semantic_role("ucontrol", 1, ("itemTake", "core", "@copper", "10", "0", "0")),
            ArgumentSemanticRole.BLOCK_OR_DEVICE,
        )
        # move x y -> x, y are OPERAND
        self.assertEqual(
            get_argument_semantic_role("ucontrol", 1, ("move", "10", "20", "0", "0", "0")),
            ArgumentSemanticRole.OPERAND,
        )
        self.assertEqual(
            get_argument_semantic_role("ucontrol", 2, ("move", "10", "20", "0", "0", "0")),
            ArgumentSemanticRole.OPERAND,
        )

    # -----------------------------------------------------------------------
    # 2. Decompilation of Named Block / Device References
    # -----------------------------------------------------------------------

    def test_drawflush_named_device(self):
        """drawflush display1 must decompile to drawflush('display1') with import."""
        mlog = "drawflush display1\n"
        py = decompile(mlog).strip()
        ast.parse(py)
        self.assertEqual(py, 'from mlog import drawflush\n\ndrawflush("display1")')

    def test_printflush_named_device(self):
        """printflush message1 must decompile to printflush('message1') with import."""
        mlog = "printflush message1\n"
        py = decompile(mlog).strip()
        ast.parse(py)
        self.assertEqual(py, 'from mlog import printflush\n\nprintflush("message1")')

    def test_read_named_cell(self):
        """read val cell1 idx must decompile to read(val, 'cell1', idx) with import."""
        mlog = "read val cell1 idx\n"
        py = decompile(mlog).strip()
        ast.parse(py)
        self.assertEqual(py, 'from mlog import read\n\nread(val, "cell1", idx)')

    def test_write_named_cell(self):
        """write total cell1 63 must decompile to write(total, 'cell1', 63) with import."""
        mlog = "write total cell1 63\n"
        py = decompile(mlog).strip()
        ast.parse(py)
        self.assertEqual(py, 'from mlog import write\n\nwrite(total, "cell1", 63)')

    def test_sensor_named_building(self):
        """sensor hp vault1 @health must decompile to sensor(hp, 'vault1', '@health') with import."""
        mlog = "sensor hp vault1 @health\n"
        py = decompile(mlog).strip()
        ast.parse(py)
        self.assertEqual(py, 'from mlog import sensor\n\nsensor(hp, "vault1", "@health")')

    def test_control_named_building(self):
        """control enabled reactor1 1 0 0 0 must decompile to control(enabled, 'reactor1', ...) with import."""
        mlog = "control enabled reactor1 1 0 0 0\n"
        py = decompile(mlog).strip()
        ast.parse(py)
        self.assertEqual(py, 'from mlog import control\n\ncontrol(enabled, "reactor1", 1, 0, 0, 0)')

    def test_radar_named_turret(self):
        """radar with cyclone1 must decompile with cyclone1 as quoted string with import."""
        mlog = "radar enemy any any distance cyclone1 1 target\n"
        py = decompile(mlog).strip()
        ast.parse(py)
        self.assertEqual(py, 'from mlog import radar\n\nradar(enemy, any, any, distance, "cyclone1", 1, target)')

    def test_ucontrol_named_container(self):
        """ucontrol itemDrop container1 must decompile with container1 as quoted string with import."""
        mlog = "ucontrol itemDrop container1 10 0 0 0\n"
        py = decompile(mlog).strip()
        ast.parse(py)
        self.assertEqual(py, 'from mlog import ucontrol\n\nucontrol(itemDrop, "container1", 10, 0, 0, 0)')

    # -----------------------------------------------------------------------
    # 3. Variable Holding Block (getlink) Remains Unquoted
    # -----------------------------------------------------------------------

    def test_variable_holding_block_not_quoted(self):
        """When block comes from getlink, it is a variable and must NOT be quoted."""
        mlog = """getlink b 0
sensor hp b @health
read val b 0
write val b 1
drawflush b
"""
        py = decompile(mlog).strip()
        ast.parse(py)
        # b must be emitted as identifier b, not "b"
        self.assertIn("getlink(b, 0)", py)
        self.assertIn('sensor(hp, b, "@health")', py)
        self.assertIn("read(val, b, 0)", py)
        self.assertIn("write(val, b, 1)", py)
        self.assertIn("drawflush(b)", py)

    # -----------------------------------------------------------------------
    # 4. Normal Variables Are Never Converted to Strings
    # -----------------------------------------------------------------------

    def test_normal_variables_never_converted_to_strings(self):
        """General operands and variables must remain unquoted Python identifiers."""
        mlog = """set x 10
set y 20
op add z x y
wait t
print msg
"""
        py = decompile(mlog).strip()
        ast.parse(py)
        self.assertIn("x = 10", py)
        self.assertIn("y = 20", py)
        self.assertIn("z = x + y", py)
        self.assertIn("wait(t)", py)
        self.assertIn("print(msg)", py)

    # -----------------------------------------------------------------------
    # 5. Zero Guessing: Unknown Opcodes Fallback Safely
    # -----------------------------------------------------------------------

    def test_zero_guessing_unknown_opcode(self):
        """Unknown opcodes have no metadata evidence of device arguments -> operands remain as-is."""
        from src.decompiler.errors import SourceLocation
        instr = MlogInstruction(
            address=0,
            opcode="customop",
            args=("foo", "bar", "123"),
            loc=SourceLocation(filename="<test>", line=1, col=1),
        )
        py = instruction_to_python(instr)
        ast.parse(py)
        self.assertEqual(py, "customop(foo, bar, 123)")

    # -----------------------------------------------------------------------
    # 6. Def-Use and Dataflow Integration
    # -----------------------------------------------------------------------

    def test_dataflow_does_not_treat_hardware_devices_as_variable_uses(self):
        """Dataflow analysis must not treat display1 or message1 as uninitialized variable reads."""
        instrs = parse_mlog("drawflush display1\nprintflush message1\n")
        read_vars_0 = get_instruction_read_vars(instrs[0])
        read_vars_1 = get_instruction_read_vars(instrs[1])
        self.assertEqual(read_vars_0, [])
        self.assertEqual(read_vars_1, [])

    def test_def_vars_tracks_all_destination_opcodes(self):
        """get_instruction_dest_vars must track getlink, packcolor, radar, ulocate destinations."""
        instrs = parse_mlog("""getlink b 0
packcolor col 1 0 0 1
radar enemy any any distance cyclone1 1 target
ulocate ore core true @copper ox oy ofound obuild
""")
        self.assertEqual(get_instruction_dest_vars(instrs[0]), ["b"])
        self.assertEqual(get_instruction_dest_vars(instrs[1]), ["col"])
        self.assertEqual(get_instruction_dest_vars(instrs[2]), ["target"])
        self.assertEqual(get_instruction_dest_vars(instrs[3]), ["ox", "oy", "ofound", "obuild"])

    # -----------------------------------------------------------------------
    # 7. Round-Trip Validation (MLog -> Python DSL -> MLog)
    # -----------------------------------------------------------------------

    def test_full_roundtrip_device_references(self):
        """Verify MLog -> decompile -> compile_py preserves exact canonical MLog instructions."""
        original_mlog = """read val cell1 idx
write total cell1 63
printflush message1
drawflush display1
sensor hp vault1 @health
control enabled reactor1 1 0 0 0
radar enemy any any distance cyclone1 1 target
"""
        decompiled_py = decompile(original_mlog)
        # 1. Must parse cleanly in Python
        ast.parse(decompiled_py)

        # 2. Must recompile to exact original MLog lines
        recompiled = compile_py(decompiled_py, allow_functions=False, validate=True).mlog

        orig_lines = [l.strip() for l in original_mlog.strip().splitlines() if l.strip()]
        recompiled_lines = [l.strip() for l in recompiled.strip().splitlines() if l.strip()]
        self.assertEqual(orig_lines, recompiled_lines)


if __name__ == "__main__":
    unittest.main()
