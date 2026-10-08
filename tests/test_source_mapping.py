"""Unit tests for Phase 4.5: Source Mapping & Debug Mode in mlog decompiler.

Tests cover:
1. Simple assignment mapping
2. Binary expression mapping
3. Multi-instruction expression mapping
4. Temporary elimination mapping
5. If mapping
6. If/else mapping
7. Elif mapping
8. While mapping
9. Break mapping
10. Continue mapping
11. Nested control-flow mapping
12. FunctionDef mapping
13. CallNode mapping
14. ReturnNode mapping
15. Multiple call sites
16. UnstructuredNode fallback mapping
17. Python -> MLog reverse lookup
18. MLog -> Python reverse lookup
19. Debug output syntax validation
20. Deterministic JSON SourceMap
21. Round-trip SourceMap regression
"""

import ast
import json
import py_compile
import tempfile
import unittest
from pathlib import Path

from src.decompiler import (
    MlogInstruction,
    MlogSourceLocation,
    SourceMap,
    SourceMapping,
    decompile,
    decompile_program,
    decompile_with_source_map,
    format_mlog_address_comment,
)


class TestSourceMappingPhase45(unittest.TestCase):
    """Test suite for Phase 4.5 Source Mapping and Debug Mode."""

    def _verify_python_syntax(self, code: str) -> ast.AST:
        """Helper to ensure generated code is valid Python syntax and compiles cleanly."""
        tree = ast.parse(code)
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = f.name
        try:
            py_compile.compile(temp_path, doraise=True)
        finally:
            Path(temp_path).unlink(missing_ok=True)
        return tree

    # -----------------------------------------------------------------------
    # 1. Simple Assignment Mapping
    # -----------------------------------------------------------------------

    def test_simple_assignment_mapping(self):
        """Test mapping a single 'set x 10' instruction to Python assignment."""
        mlog = "set x 10\n"
        code, sm = decompile_with_source_map(mlog)
        self._verify_python_syntax(code)
        self.assertIn("x = 10", code)

        # Address 0 should map to line 1
        line = sm.mlog_to_python(0)
        self.assertIsNotNone(line)
        self.assertEqual(sm.python_to_mlog(line), [0])

        m = sm.get_mapping_by_python_line(line)
        self.assertIsNotNone(m)
        self.assertEqual(m.node_type, "Assign")
        self.assertEqual(m.mlog_addresses, [0])
        self.assertEqual(m.instructions, ["set x 10"])

    # -----------------------------------------------------------------------
    # 2. Binary Expression Mapping
    # -----------------------------------------------------------------------

    def test_binary_expression_mapping(self):
        """Test mapping a single 'op add z a b' instruction."""
        mlog = "op add z a b\n"
        code, sm = decompile_with_source_map(mlog)
        self._verify_python_syntax(code)
        self.assertIn("z = a + b", code)

        line = sm.mlog_to_python(0)
        self.assertIsNotNone(line)
        self.assertEqual(sm.python_to_mlog(line), [0])

        m = sm.get_mapping_by_python_line(line)
        self.assertEqual(m.node_type, "Assign")
        self.assertEqual(m.mlog_addresses, [0])

    # -----------------------------------------------------------------------
    # 3. Multi-Instruction Expression Mapping
    # -----------------------------------------------------------------------

    def test_multi_instruction_expression_mapping(self):
        """Test expression tree folded from multiple instructions retains all addresses."""
        mlog = """
set __tmp0 a
op mul __tmp1 __tmp0 b
op add result __tmp1 c
"""
        code, sm = decompile_with_source_map(mlog)
        self._verify_python_syntax(code)
        self.assertIn("result = a * b + c", code)

        # All 3 instructions (0, 1, 2) must be preserved in the resulting assignment
        line = sm.mlog_to_python(2)
        self.assertIsNotNone(line)
        addrs = sm.python_to_mlog(line)
        self.assertEqual(addrs, [0, 1, 2])

        m = sm.get_mapping_by_python_line(line)
        self.assertEqual(len(m.instructions), 3)

    # -----------------------------------------------------------------------
    # 4. Temporary Elimination Mapping
    # -----------------------------------------------------------------------

    def test_temporary_elimination_mapping(self):
        """Verify compiler temporaries preserve provenance of eliminated instructions."""
        mlog = """
set __tmp0 a
op add __tmp1 __tmp0 1
set x __tmp1
"""
        code, sm = decompile_with_source_map(mlog)
        self._verify_python_syntax(code)
        self.assertIn("x = a + 1", code)

        line = sm.mlog_to_python(0)
        self.assertIsNotNone(line)
        # All eliminated temporary instructions (0, 1, 2) must map to the output assignment
        self.assertEqual(sm.python_to_mlog(line), [0, 1, 2])
        self.assertEqual(sm.mlog_to_python(0), line)
        self.assertEqual(sm.mlog_to_python(1), line)
        self.assertEqual(sm.mlog_to_python(2), line)

    # -----------------------------------------------------------------------
    # 5. If Mapping
    # -----------------------------------------------------------------------

    def test_if_mapping(self):
        """Test mapping an if statement."""
        mlog = """
jump 2 lessThan x 10
print "greater"
"""
        code, sm = decompile_with_source_map(mlog)
        self._verify_python_syntax(code)
        self.assertIn("if x >= 10:", code)

        if_line = sm.mlog_to_python(0)
        self.assertIsNotNone(if_line)
        self.assertIn(0, sm.python_to_mlog(if_line))

        m = sm.get_mapping_by_python_line(if_line)
        self.assertEqual(m.node_type, "If")

    # -----------------------------------------------------------------------
    # 6. If / Else Mapping
    # -----------------------------------------------------------------------

    def test_if_else_mapping(self):
        """Test mapping an if/else construct with merge jump."""
        mlog = """
set x 10
jump 4 greaterThan x 5
set y 1
jump 5 always 0 0
set y 2
print y
"""
        code, sm = decompile_with_source_map(mlog)
        self._verify_python_syntax(code)
        self.assertIn("else:", code)

        # Instruction 1 (conditional jump) and 3 (skip-else jump) belong to the branch structure
        if_line = sm.mlog_to_python(1)
        self.assertIsNotNone(if_line)
        m = sm.get_mapping_by_python_line(if_line)
        self.assertEqual(m.node_type, "If")
        self.assertTrue(1 in m.mlog_addresses)

    # -----------------------------------------------------------------------
    # 7. Elif Mapping
    # -----------------------------------------------------------------------

    def test_elif_mapping(self):
        """Test mapping chained if-elif branches."""
        mlog = """
set x 5
jump 4 equal x 1
set res 10
jump 8 always 0 0
jump 7 equal x 2
set res 20
jump 8 always 0 0
set res 30
print res
"""
        code, sm = decompile_with_source_map(mlog)
        self._verify_python_syntax(code)

        # Check that mappings include If or Elif node types
        node_types = [m.node_type for m in sm.mappings]
        self.assertIn("If", node_types)

    # -----------------------------------------------------------------------
    # 8. While Mapping
    # -----------------------------------------------------------------------

    def test_while_mapping(self):
        """Test mapping while loop header and back-edge latch."""
        mlog = """
set i 0
jump 4 greaterThanEq i 10
op add i i 1
jump 1 always 0 0
print i
"""
        code, sm = decompile_with_source_map(mlog)
        self._verify_python_syntax(code)
        self.assertIn("while i < 10:", code)

        while_line = sm.mlog_to_python(1)
        self.assertIsNotNone(while_line)
        m = sm.get_mapping_by_python_line(while_line)
        self.assertEqual(m.node_type, "While")
        # Header exit jump is 1, latch jump is 3
        self.assertIn(1, m.mlog_addresses)
        self.assertIn(3, m.mlog_addresses)

    # -----------------------------------------------------------------------
    # 9. Break Mapping
    # -----------------------------------------------------------------------

    def test_break_mapping(self):
        """Test mapping break jump inside a loop."""
        mlog = """
set i 0
jump 6 greaterThanEq i 10
jump 5 notEqual i 5
jump 6 always 0 0
op add i i 1
jump 1 always 0 0
print "done"
"""
        code, sm = decompile_with_source_map(mlog)
        self._verify_python_syntax(code)
        self.assertIn("break", code)

        # Jump 3 is the break statement targeting loop exit (6)
        break_line = sm.mlog_to_python(3)
        self.assertIsNotNone(break_line)
        m = sm.get_mapping_by_python_line(break_line)
        self.assertEqual(m.node_type, "Break")
        self.assertEqual(m.mlog_addresses, [3])

    # -----------------------------------------------------------------------
    # 10. Continue Mapping
    # -----------------------------------------------------------------------

    def test_continue_mapping(self):
        """Test mapping continue jump inside a loop."""
        mlog = """
set i 0
jump 6 greaterThanEq i 10
jump 4 notEqual i 2
jump 1 always 0 0
op add i i 1
jump 1 always 0 0
print "done"
"""
        code, sm = decompile_with_source_map(mlog)
        self._verify_python_syntax(code)

        # Jump 3 targets header (1), representing a continue
        cont_line = sm.mlog_to_python(3)
        self.assertIsNotNone(cont_line)
        m = sm.get_mapping_by_python_line(cont_line)
        self.assertIn(3, m.mlog_addresses)

    # -----------------------------------------------------------------------
    # 11. Nested Control-Flow Mapping
    # -----------------------------------------------------------------------

    def test_nested_control_flow_mapping(self):
        """Test mapping with nested loops and if conditions."""
        mlog = """
set outer 0
jump 7 greaterThanEq outer 3
set inner 0
jump 5 greaterThanEq inner 3
op add inner inner 1
jump 3 always 0 0
op add outer outer 1
jump 1 always 0 0
print "finished"
"""
        code, sm = decompile_with_source_map(mlog)
        self._verify_python_syntax(code)

        # Verify outer while loop
        outer_line = sm.mlog_to_python(1)
        self.assertIsNotNone(outer_line)
        # Verify inner while loop
        inner_line = sm.mlog_to_python(3)
        self.assertIsNotNone(inner_line)
        self.assertNotEqual(outer_line, inner_line)

    # -----------------------------------------------------------------------
    # 12. FunctionDef Mapping
    # -----------------------------------------------------------------------

    def test_function_def_mapping(self):
        """Test mapping a function definition to its body range."""
        mlog = """
jump 5 always 0 0
op add res a b
set __retval_add res
set @counter __ret_add
set @counter __ret_add
set a 10
set b 20
set __ret_add 9
jump 1 always 0 0
set out __retval_add
print out
"""
        code, sm = decompile_with_source_map(mlog)
        self._verify_python_syntax(code)
        self.assertIn("def add(a, b):", code)

        fn_mappings = [m for m in sm.mappings if m.node_type == "FunctionDef"]
        self.assertEqual(len(fn_mappings), 1)
        m = fn_mappings[0]
        self.assertEqual(m.node_type, "FunctionDef")
        self.assertEqual(m.python_line, 1)
        self.assertTrue(1 in m.mlog_addresses)
        self.assertTrue(1 in sm.python_to_mlog(m.python_line))

    # -----------------------------------------------------------------------
    # 13. CallNode Mapping
    # -----------------------------------------------------------------------

    def test_call_node_mapping(self):
        """Test mapping a function call site with arguments and return retrieval."""
        mlog = """
jump 5 always 0 0
op add res a b
set __retval_add res
set @counter __ret_add
set @counter __ret_add
set a 10
set b 20
set __ret_add 9
jump 1 always 0 0
set out __retval_add
print out
"""
        code, sm = decompile_with_source_map(mlog)
        self._verify_python_syntax(code)
        self.assertIn("out = add(10, 20)", code)

        # Call site spans parameter sets (5, 6), return address set (7), jump (8), retval set (9)
        call_line = sm.mlog_to_python(8)
        self.assertIsNotNone(call_line)
        m = sm.get_mapping_by_python_line(call_line)
        self.assertEqual(m.node_type, "Call")
        self.assertIn(5, m.mlog_addresses)
        self.assertIn(6, m.mlog_addresses)
        self.assertIn(7, m.mlog_addresses)
        self.assertIn(8, m.mlog_addresses)
        self.assertIn(9, m.mlog_addresses)

    # -----------------------------------------------------------------------
    # 14. ReturnNode Mapping
    # -----------------------------------------------------------------------

    def test_return_node_mapping(self):
        """Test mapping a return statement to return value computation and link register jump."""
        mlog = """
jump 5 always 0 0
op add res a b
set __retval_add res
set @counter __ret_add
set @counter __ret_add
set a 1
set b 2
set __ret_add 9
jump 1 always 0 0
set out __retval_add
"""
        code, sm = decompile_with_source_map(mlog)
        self._verify_python_syntax(code)

        # Return instruction at 3 (set @counter __ret_add)
        ret_line = sm.mlog_to_python(3)
        self.assertIsNotNone(ret_line)
        m = sm.get_mapping_by_python_line(ret_line)
        self.assertEqual(m.node_type, "Return")
        self.assertIn(3, m.mlog_addresses)

    # -----------------------------------------------------------------------
    # 15. Multiple Call Sites Mapping
    # -----------------------------------------------------------------------

    def test_multiple_call_sites(self):
        """Test two distinct call sites map to their respective instruction ranges."""
        mlog = """
jump 5 always 0 0
op mul doubled x 2
set __retval_twice doubled
set @counter __ret_twice
set @counter __ret_twice
set x 5
set __ret_twice 8
jump 1 always 0 0
set a __retval_twice
set x 20
set __ret_twice 12
jump 1 always 0 0
set b __retval_twice
"""
        code, sm = decompile_with_source_map(mlog)
        self._verify_python_syntax(code)

        # Call site 1 (jump at 7)
        cs1_line = sm.mlog_to_python(7)
        # Call site 2 (jump at 11)
        cs2_line = sm.mlog_to_python(11)

        self.assertIsNotNone(cs1_line)
        self.assertIsNotNone(cs2_line)
        self.assertNotEqual(cs1_line, cs2_line)

        m1 = sm.get_mapping_by_python_line(cs1_line)
        m2 = sm.get_mapping_by_python_line(cs2_line)
        self.assertIn(7, m1.mlog_addresses)
        self.assertIn(11, m2.mlog_addresses)

    # -----------------------------------------------------------------------
    # 16. UnstructuredNode Fallback Mapping
    # -----------------------------------------------------------------------

    def test_unstructured_fallback_mapping(self):
        """Test that unstructured fallback retains exact original instruction addresses."""
        mlog = """
set x 10
set @counter unknown_reg
print x
"""
        code, sm = decompile_with_source_map(mlog)
        self._verify_python_syntax(code)

        # Address 1 is 'set @counter unknown_reg'
        line = sm.mlog_to_python(1)
        self.assertIsNotNone(line)
        self.assertIn(1, sm.python_to_mlog(line))

    # -----------------------------------------------------------------------
    # 17. Python -> MLog Reverse Lookup
    # -----------------------------------------------------------------------

    def test_python_to_mlog_lookup(self):
        """Test query python_to_mlog returns correct sorted list of addresses."""
        mlog = """
set a 10
set b 20
op add c a b
"""
        code, sm = decompile_with_source_map(mlog)
        self._verify_python_syntax(code)

        # Non-existent line should return empty list
        self.assertEqual(sm.python_to_mlog(9999), [])

        # Valid lines should return non-empty lists
        addrs_1 = sm.python_to_mlog(1)
        self.assertTrue(len(addrs_1) > 0)

    # -----------------------------------------------------------------------
    # 18. MLog -> Python Reverse Lookup
    # -----------------------------------------------------------------------

    def test_mlog_to_python_lookup(self):
        """Test query mlog_to_python returns correct line and handles non-existent addresses."""
        mlog = "set x 1\nset y 2\n"
        code, sm = decompile_with_source_map(mlog)
        self._verify_python_syntax(code)

        line_0 = sm.mlog_to_python(0)
        line_1 = sm.mlog_to_python(1)
        self.assertIsNotNone(line_0)
        self.assertIsNotNone(line_1)
        self.assertLess(line_0, line_1)

        # Address outside program bounds should return None
        self.assertIsNone(sm.mlog_to_python(9999))

    # -----------------------------------------------------------------------
    # 19. Debug Output Syntax Validation
    # -----------------------------------------------------------------------

    def test_debug_output_syntax_validation(self):
        """Test debug mode output contains # mlog comments and passes Python AST parser."""
        mlog = """
set a 10
set b 20
op add c a b
jump 5 greaterThan c 15
print "small"
jump 6 always 0 0
print "large"
"""
        # Decompile with debug=True
        debug_code = decompile(mlog, debug=True)
        self._verify_python_syntax(debug_code)

        # Must contain # mlog comments
        self.assertIn("# mlog[", debug_code)

        # Clean code (debug=False) must NOT contain debug comments
        clean_code = decompile(mlog, debug=False)
        self._verify_python_syntax(clean_code)
        self.assertNotIn("# mlog[", clean_code)

    # -----------------------------------------------------------------------
    # 20. Deterministic JSON SourceMap
    # -----------------------------------------------------------------------

    def test_deterministic_json_sourcemap(self):
        """Test serializing SourceMap to JSON produces deterministic, valid output."""
        mlog = """
set x 1
op add y x 2
print y
"""
        code1, sm1 = decompile_with_source_map(mlog)
        code2, sm2 = decompile_with_source_map(mlog)

        json1 = sm1.to_json()
        json2 = sm2.to_json()

        # Deterministic byte-for-byte identical output
        self.assertEqual(json1, json2)

        data = json.loads(json1)
        self.assertEqual(data["version"], "1.0")
        self.assertIn("mappings", data)
        self.assertIn("python_to_mlog", data)
        self.assertIn("mlog_to_python", data)

    # -----------------------------------------------------------------------
    # 21. Round-Trip SourceMap Regression
    # -----------------------------------------------------------------------

    def test_round_trip_sourcemap_regression(self):
        """Test serialization and deserialization round-trip of SourceMap."""
        mlog = """
set x 100
set y 200
op mul z x y
print z
"""
        code, sm = decompile_with_source_map(mlog)
        json_str = sm.to_json()

        # Restore SourceMap from JSON
        restored = SourceMap.from_json(json_str, instruction_by_address=sm.instruction_by_address)

        self.assertEqual(len(sm.mappings), len(restored.mappings))
        for m_orig, m_rest in zip(sm.mappings, restored.mappings):
            self.assertEqual(m_orig.python_line, m_rest.python_line)
            self.assertEqual(m_orig.node_type, m_rest.node_type)
            self.assertEqual(m_orig.mlog_addresses, m_rest.mlog_addresses)

        # Bidirectional lookups must be identical
        for addr in [0, 1, 2, 3]:
            self.assertEqual(sm.mlog_to_python(addr), restored.mlog_to_python(addr))


if __name__ == "__main__":
    unittest.main()
