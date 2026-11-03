"""Regression tests for P2 API Ergonomics:
A. lookup callable namespace methods (item, block, unit, liquid)
B. query callable namespace methods (circle, rect)
C. message callable namespace methods (announce, notify, toast)
"""

import unittest
import mlog
from mlog import compile_py, lookup, LookupType, query, QueryType, QueryShape, Teams, message, MessageType
from mlog.errors import CompileError
from mlog.validator import MlogValidator
from mlog.mindustry_validator import is_mindustry_available, validate_with_mindustry


class TestP2Ergonomics(unittest.TestCase):
    """Test suite for P2 Ergonomics additions and backward compatibility."""

    def compile_code(self, source: str) -> str:
        """Compile DSL source and validate syntax."""
        res = compile_py(source, validate=True)
        mlog_text = res.mlog.strip()
        MlogValidator.validate(mlog_text)
        return mlog_text

    def validate_with_jvm(self, mlog_text: str):
        """Validate generated mlog against real Mindustry v160.7 engine if available."""
        if is_mindustry_available():
            world_opcodes = ("query", "message", "spawn", "setrule", "weather", "effect", "explosion")
            if any(op in mlog_text for op in world_opcodes) and "#processor" not in mlog_text:
                test_mlog = "#processor: world\n" + mlog_text
            else:
                test_mlog = mlog_text
            valid, err, *_ = validate_with_mindustry(test_mlog)
            self.assertTrue(valid, f"JVM validation failed: {err}")

    # =========================================================================
    # A. lookup namespace methods
    # =========================================================================

    def test_lookup_item_expression_and_statement(self):
        source = (
            "from mlog import lookup\n"
            "it = lookup.item(0)\n"
            "lookup.item(1, out_it)\n"
        )
        mlog = self.compile_code(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "lookup item it 0")
        self.assertEqual(lines[1], "lookup item out_it 1")
        self.validate_with_jvm(mlog)

    def test_lookup_block_expression_and_statement(self):
        source = (
            "from mlog import lookup\n"
            "b = lookup.block(5)\n"
            "lookup.block(10, out_b)\n"
        )
        mlog = self.compile_code(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "lookup block b 5")
        self.assertEqual(lines[1], "lookup block out_b 10")
        self.validate_with_jvm(mlog)

    def test_lookup_unit_expression_and_statement(self):
        source = (
            "from mlog import lookup\n"
            "u = lookup.unit(2)\n"
            "lookup.unit(3, out_u)\n"
        )
        mlog = self.compile_code(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "lookup unit u 2")
        self.assertEqual(lines[1], "lookup unit out_u 3")
        self.validate_with_jvm(mlog)

    def test_lookup_liquid_expression_and_statement(self):
        source = (
            "from mlog import lookup\n"
            "liq = lookup.liquid(1)\n"
            "lookup.liquid(2, out_liq)\n"
        )
        mlog = self.compile_code(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "lookup liquid liq 1")
        self.assertEqual(lines[1], "lookup liquid out_liq 2")
        self.validate_with_jvm(mlog)

    def test_lookup_team_expression_and_statement(self):
        source = (
            "from mlog import lookup\n"
            "t = lookup.team(1)\n"
            "lookup.team(2, out_t)\n"
        )
        mlog = self.compile_code(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "lookup team t 1")
        self.assertEqual(lines[1], "lookup team out_t 2")
        self.validate_with_jvm(mlog)

    def test_lookup_nested_expression(self):
        source = (
            "from mlog import lookup, print\n"
            "print(lookup.item(0))\n"
        )
        mlog = self.compile_code(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "lookup item __tmp0 0")
        self.assertEqual(lines[1], "print __tmp0")
        self.validate_with_jvm(mlog)

    def test_lookup_backward_compatibility(self):
        source = (
            "from mlog import lookup, LookupType\n"
            "res = lookup(LookupType.ITEM, 0)\n"
            "lookup(LookupType.BLOCK, out_b, 1)\n"
            "res2 = lookup('unit', 2)\n"
            "lookup('liquid', out_l, 3)\n"
        )
        mlog = self.compile_code(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "lookup item res 0")
        self.assertEqual(lines[1], "lookup block out_b 1")
        self.assertEqual(lines[2], "lookup unit res2 2")
        self.assertEqual(lines[3], "lookup liquid out_l 3")
        self.validate_with_jvm(mlog)

    def test_lookup_invalid_calls(self):
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import lookup\nlookup.item()\n")
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import lookup\nlookup.item(1, 2, 3)\n")
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import lookup\nlookup.item(idx=0)\n")
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import lookup\nlookup.unknown(0)\n")

    def test_lookup_pure_python_runtime(self):
        self.assertEqual(lookup.item(0), 0)
        self.assertEqual(lookup.block(0), 0)
        self.assertEqual(lookup.unit(0), 0)
        self.assertEqual(lookup.liquid(0), 0)
        self.assertEqual(lookup.team(0), 0)
        self.assertEqual(lookup(LookupType.ITEM, 0), 0)

    # =========================================================================
    # B. query namespace methods
    # =========================================================================

    def test_query_circle(self):
        source = (
            "from mlog import query, QueryType, Teams\n"
            "query.circle(QueryType.UNIT, Teams.SHARDED, 10, 20, 50)\n"
            "query.circle('building', '@crux', x, y, r)\n"
            "query.circle(QueryType.UNIT, None, 0, 0, 100)\n"
            "query.circle(QueryType.UNIT, 'null', 0, 0, 100)\n"
            "query.circle(QueryType.UNIT, team_var, 0, 0, 100)\n"
            "sharded = 42\n"
            "query.circle(QueryType.UNIT, sharded, 0, 0, 100)\n"
        )
        mlog = self.compile_code(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "query circle unit @sharded 10 20 50 0")
        self.assertEqual(lines[1], "query circle building @crux x y r 0")
        self.assertEqual(lines[2], "query circle unit null 0 0 100 0")
        self.assertEqual(lines[3], "query circle unit null 0 0 100 0")
        self.assertEqual(lines[4], "query circle unit team_var 0 0 100 0")
        self.assertEqual(lines[5], "set sharded 42")
        self.assertEqual(lines[6], "query circle unit sharded 0 0 100 0")
        self.validate_with_jvm(mlog)

    def test_query_rect(self):
        source = (
            "from mlog import query, QueryType, Teams\n"
            "query.rect(QueryType.BUILDING, Teams.CRUX, 10, 20, 30, 40)\n"
            "query.rect('unit', '@sharded', x, y, w, h)\n"
            "query.rect(QueryType.BUILDING, None, 1, 2, 3, 4)\n"
            "crux = 99\n"
            "query.rect(QueryType.BUILDING, crux, 1, 2, 3, 4)\n"
        )
        mlog = self.compile_code(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "query rect building @crux 10 20 30 40")
        self.assertEqual(lines[1], "query rect unit @sharded x y w h")
        self.assertEqual(lines[2], "query rect building null 1 2 3 4")
        self.assertEqual(lines[3], "set crux 99")
        self.assertEqual(lines[4], "query rect building crux 1 2 3 4")
        self.validate_with_jvm(mlog)

    def test_query_expression_fallback(self):
        source = (
            "from mlog import query, QueryType, Teams\n"
            "res = query.circle(QueryType.UNIT, Teams.SHARDED, 0, 0, 10)\n"
        )
        mlog = self.compile_code(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "query circle unit @sharded 0 0 10 0")
        self.assertEqual(lines[1], "set res 0")
        self.validate_with_jvm(mlog)

    def test_query_backward_compatibility(self):
        source = (
            "from mlog import query, QueryShape, QueryType, Teams\n"
            "query(QueryShape.CIRCLE, QueryType.UNIT, Teams.SHARDED, 10, 20, 50, 0)\n"
            "query('rect', 'unit', '@crux', 0, 0, 10, 20)\n"
        )
        mlog = self.compile_code(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "query circle unit @sharded 10 20 50 0")
        self.assertEqual(lines[1], "query rect unit @crux 0 0 10 20")
        self.validate_with_jvm(mlog)

    def test_query_invalid_calls(self):
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import query, QueryType, Teams\nquery.circle()\n")
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import query, QueryType, Teams\nquery.circle(QueryType.UNIT, Teams.SHARDED, 0, 0, 10, 20)\n")
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import query, QueryType, Teams\nquery.circle(type=QueryType.UNIT)\n")
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import query, QueryType, Teams\nquery.rect(QueryType.UNIT, Teams.SHARDED, 0, 0, 10)\n")
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import query, QueryType, Teams\nquery.unknown(0, 0)\n")
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import query, Teams\nquery.circle('invalid_type', Teams.SHARDED, 0, 0, 10)\n")
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import query, QueryType\nquery.circle(QueryType.UNIT, 'invalid_team', 0, 0, 10)\n")

    def test_query_pure_python_runtime(self):
        self.assertIsNone(query.circle("unit", "@sharded", 0, 0, 10))
        self.assertIsNone(query.rect("building", "@crux", 0, 0, 10, 20))
        self.assertIsNone(query("circle", "unit", "@sharded", 0, 0, 10, 0))

    # =========================================================================
    # C. message namespace methods
    # =========================================================================

    def test_message_announce(self):
        source = (
            "from mlog import message\n"
            "message.announce()\n"
            "message.announce(5)\n"
            "message.announce(10, my_success)\n"
            "message.announce(duration=2, out_success='@wait')\n"
            "message.announce(outSuccess=done)\n"
            "res = message.announce()\n"
            "res2 = message.announce(4)\n"
        )
        mlog = self.compile_code(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "message announce 3 @wait")
        self.assertEqual(lines[1], "message announce 5 @wait")
        self.assertEqual(lines[2], "message announce 10 my_success")
        self.assertEqual(lines[3], "message announce 2 @wait")
        self.assertEqual(lines[4], "message announce 3 done")
        self.assertEqual(lines[5], "message announce 3 res")
        self.assertEqual(lines[6], "message announce 4 res2")
        self.validate_with_jvm(mlog)

    def test_message_toast(self):
        source = (
            "from mlog import message\n"
            "message.toast()\n"
            "message.toast(2)\n"
            "message.toast(5, out_s)\n"
            "success = message.toast(2)\n"
        )
        mlog = self.compile_code(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "message toast 3 @wait")
        self.assertEqual(lines[1], "message toast 2 @wait")
        self.assertEqual(lines[2], "message toast 5 out_s")
        self.assertEqual(lines[3], "message toast 2 success")
        self.validate_with_jvm(mlog)

    def test_message_notify(self):
        source = (
            "from mlog import message\n"
            "message.notify()\n"
            "message.notify(4, out_s)\n"
            "done = message.notify()\n"
        )
        mlog = self.compile_code(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "message notify 3 @wait")
        self.assertEqual(lines[1], "message notify 4 out_s")
        self.assertEqual(lines[2], "message notify 3 done")
        self.validate_with_jvm(mlog)

    def test_message_reject_mission_and_invalid_calls(self):
        # Specifically verify message.mission() is rejected per upstream contract
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import message\nmessage.mission()\n")
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import message\nmessage.mission('objective')\n")
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import message\nmessage.unknown()\n")
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import message\nmessage.announce(1, 2, 3)\n")
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import message\nmessage.announce(timeout=5)\n")

    def test_message_backward_compatibility(self):
        source = (
            "from mlog import message, MessageType\n"
            "message(MessageType.ANNOUNCE, 3, '@wait')\n"
            "message('toast', 5)\n"
            "res = message('notify')\n"
        )
        mlog = self.compile_code(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "message announce 3 @wait")
        self.assertEqual(lines[1], "message toast 5 @wait")
        self.assertEqual(lines[2], "message notify 3 res")
        self.validate_with_jvm(mlog)

    def test_message_pure_python_runtime(self):
        self.assertEqual(message.announce(), 1)
        self.assertEqual(message.toast(5), 1)
        self.assertEqual(message.notify(), 1)
        self.assertEqual(message("announce", 3), 1)


if __name__ == "__main__":
    unittest.main()
