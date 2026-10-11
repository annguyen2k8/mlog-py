"""Comprehensive regression tests for the Mindustry Vars API in mlog-py.

Verifies:
1. All 5 variable groups from Mindustry source:
   - Processor: Vars.this, Vars.thisx, Vars.thisy, Vars.links, Vars.ipt, Vars.counter, Vars.unit
   - General: Vars.pi, Vars.e, Vars.degToRad, Vars.radToDeg, Vars.ctrlProcessor, Vars.ctrlPlayer, Vars.ctrlCommand
   - Map: Vars.time, Vars.tick, Vars.second, Vars.minute, Vars.waveNumber, Vars.waveTime, Vars.mapw, Vars.maph, Vars.wait
   - Network/Clientside: Vars.server, Vars.client, Vars.clientLocale, Vars.clientUnit, Vars.clientName, Vars.clientTeam, Vars.clientMobile, Vars.clientMusicPlaying, Vars.clientCurrentMusic
   - Lookup: Vars.blockCount, Vars.unitCount, Vars.itemCount, Vars.liquidCount
2. Expressions involving Vars (arithmetic, comparisons, loops, intrinsic calls).
3. String literal disambiguation: strings starting with '@' vs Vars tokens.
4. Read/Write semantics: Vars.counter is writable, all other Vars tokens are strictly read-only.
5. Invalid/unknown token rejection (CompileError and runtime AttributeError).
6. Backward compatibility with existing at_* identifiers and string constants.
7. Execution verification on real Mindustry Java harness.
"""

import unittest
from src.errors import CompileError
from src.mindustry_validator import is_mindustry_available, run_with_mindustry, validate_with_mindustry
from src.mlog import compile_py
from src.mlog_registry import (
    BuiltinVarToken,
    LookupType,
    Vars,
)
from src.validator import MlogValidator


class TestVarsAPI(unittest.TestCase):
    """Test suite for the Mindustry Logic Vars API."""

    def check_compile(self, source: str) -> str:
        """Compile source and validate emitted mlog syntax."""
        res = compile_py(source, filename="test_vars.py", validate=True)
        MlogValidator.validate(res.mlog)
        return res.mlog.strip()

    # -----------------------------------------------------------------------
    # 1. Verification of All 5 Variable Groups (36 Tokens)
    # -----------------------------------------------------------------------

    def test_processor_group(self):
        """Processor group variables compile to exact Mindustry tokens."""
        source = """
from mlog import Vars
th = Vars.this
tx = Vars.thisx
ty = Vars.thisy
lnk = Vars.links
speed = Vars.ipt
c = Vars.counter
u = Vars.unit
"""
        mlog = self.check_compile(source)
        lines = [line.strip() for line in mlog.splitlines()]
        self.assertIn("set th @this", lines)
        self.assertIn("set tx @thisx", lines)
        self.assertIn("set ty @thisy", lines)
        self.assertIn("set lnk @links", lines)
        self.assertIn("set speed @ipt", lines)
        self.assertIn("set c @counter", lines)
        self.assertIn("set u @unit", lines)

    def test_general_group(self):
        """General group variables compile to exact Mindustry tokens."""
        source = """
from mlog import Vars
p = Vars.pi
ev = Vars.e
d2r = Vars.degToRad
r2d = Vars.radToDeg
cp = Vars.ctrlProcessor
cpl = Vars.ctrlPlayer
cc = Vars.ctrlCommand
"""
        mlog = self.check_compile(source)
        lines = [line.strip() for line in mlog.splitlines()]
        self.assertIn("set p @pi", lines)
        self.assertIn("set ev @e", lines)
        self.assertIn("set d2r @degToRad", lines)
        self.assertIn("set r2d @radToDeg", lines)
        self.assertIn("set cp @ctrlProcessor", lines)
        self.assertIn("set cpl @ctrlPlayer", lines)
        self.assertIn("set cc @ctrlCommand", lines)

    def test_map_group(self):
        """Map group variables compile to exact Mindustry tokens."""
        source = """
from mlog import Vars
tm = Vars.time
tk = Vars.tick
sec = Vars.second
mn = Vars.minute
wn = Vars.waveNumber
wt = Vars.waveTime
mw = Vars.mapw
mh = Vars.maph
wt_marker = Vars.wait
"""
        mlog = self.check_compile(source)
        lines = [line.strip() for line in mlog.splitlines()]
        self.assertIn("set tm @time", lines)
        self.assertIn("set tk @tick", lines)
        self.assertIn("set sec @second", lines)
        self.assertIn("set mn @minute", lines)
        self.assertIn("set wn @waveNumber", lines)
        self.assertIn("set wt @waveTime", lines)
        self.assertIn("set mw @mapw", lines)
        self.assertIn("set mh @maph", lines)
        self.assertIn("set wt_marker @wait", lines)

    def test_network_clientside_group(self):
        """Network and Clientside variables compile to exact Mindustry tokens."""
        source = """
from mlog import Vars
srv = Vars.server
cli = Vars.client
loc = Vars.clientLocale
cu = Vars.clientUnit
cname = Vars.clientName
cteam = Vars.clientTeam
mob = Vars.clientMobile
mus = Vars.clientMusicPlaying
cmus = Vars.clientCurrentMusic
"""
        mlog = self.check_compile(source)
        lines = [line.strip() for line in mlog.splitlines()]
        self.assertIn("set srv @server", lines)
        self.assertIn("set cli @client", lines)
        self.assertIn("set loc @clientLocale", lines)
        self.assertIn("set cu @clientUnit", lines)
        self.assertIn("set cname @clientName", lines)
        self.assertIn("set cteam @clientTeam", lines)
        self.assertIn("set mob @clientMobile", lines)
        self.assertIn("set mus @clientMusicPlaying", lines)
        self.assertIn("set cmus @clientCurrentMusic", lines)

    def test_lookup_group(self):
        """Lookup group variables compile to exact Mindustry tokens."""
        source = """
from mlog import Vars
bc = Vars.blockCount
uc = Vars.unitCount
ic = Vars.itemCount
lc = Vars.liquidCount
"""
        mlog = self.check_compile(source)
        lines = [line.strip() for line in mlog.splitlines()]
        self.assertIn("set bc @blockCount", lines)
        self.assertIn("set uc @unitCount", lines)
        self.assertIn("set ic @itemCount", lines)
        self.assertIn("set lc @liquidCount", lines)

    # -----------------------------------------------------------------------
    # 2. Expressions and Control Flow
    # -----------------------------------------------------------------------

    def test_arithmetic_with_vars(self):
        """Vars tokens can be used directly in arithmetic operations."""
        source = """
from mlog import Vars
next_tick = Vars.tick + 60
elapsed = Vars.time * 0.001
scaled_pi = Vars.pi * 2.0
rem = Vars.waveNumber % 10
"""
        mlog = self.check_compile(source)
        lines = [line.strip() for line in mlog.splitlines()]
        self.assertIn("op add next_tick @tick 60", lines)
        self.assertIn("op mul elapsed @time 0.001", lines)
        self.assertIn("op mul scaled_pi @pi 2.0", lines)
        self.assertIn("op emod rem @waveNumber 10", lines)

    def test_conditionals_and_comparisons(self):
        """Vars tokens can be compared against literals and variables."""
        source = """
from mlog import Vars, null
if Vars.unit == null:
    has_unit = 0
else:
    has_unit = 1

if Vars.tick >= 6000:
    is_late = 1

if Vars.server == 1:
    is_host = 1
"""
        mlog = self.check_compile(source)
        lines = [line.strip() for line in mlog.splitlines()]
        self.assertTrue(any("notEqual @unit null" in l for l in lines))
        self.assertTrue(any("lessThan @tick 6000" in l for l in lines))
        self.assertTrue(any("notEqual @server 1" in l for l in lines))

    def test_intrinsics_with_vars(self):
        """Vars tokens pass cleanly into print and lookup intrinsics."""
        source = """
from mlog import Vars, print, lookup, LookupType
print(Vars.clientName)
print(Vars.tick)
b = lookup(LookupType.BLOCK, Vars.blockCount)
"""
        mlog = self.check_compile(source)
        lines = [line.strip() for line in mlog.splitlines()]
        self.assertIn("print @clientName", lines)
        self.assertIn("print @tick", lines)
        self.assertIn("lookup block b @blockCount", lines)

    # -----------------------------------------------------------------------
    # 3. String Literal Disambiguation
    # -----------------------------------------------------------------------

    def test_string_literal_vs_vars_token(self):
        """String literals starting with '@' are quoted, while Vars tokens are unquoted."""
        source = """
from mlog import Vars, print
s_tick = "@tick"
s_wave = "@waveNumber"
s_name = "@clientName"
s_block = "@blockCount"
s_hello = "@hello"

t_tick = Vars.tick
t_name = Vars.clientName

print("@tick")
print(Vars.tick)
"""
        mlog = self.check_compile(source)
        lines = [line.strip() for line in mlog.splitlines()]
        # String literals must be quoted
        self.assertIn('set s_tick "@tick"', lines)
        self.assertIn('set s_wave "@waveNumber"', lines)
        self.assertIn('set s_name "@clientName"', lines)
        self.assertIn('set s_block "@blockCount"', lines)
        self.assertIn('set s_hello "@hello"', lines)
        self.assertIn('print "@tick"', lines)

        # Vars tokens must be unquoted
        self.assertIn("set t_tick @tick", lines)
        self.assertIn("set t_name @clientName", lines)
        self.assertIn("print @tick", lines)

    def test_comparison_with_at_string_literal_vs_vars(self):
        """Comparing against a string literal preserves quotes, while Vars token is unquoted."""
        source = """
from mlog import Vars
if msg == "@clientName":
    res1 = 1

if msg == Vars.clientName:
    res2 = 1
"""
        mlog = self.check_compile(source)
        lines = [line.strip() for line in mlog.splitlines()]
        self.assertTrue(any('notEqual msg "@clientName"' in l for l in lines))
        self.assertTrue(any('notEqual msg @clientName' in l for l in lines))

    # -----------------------------------------------------------------------
    # 4. Read / Write Semantics
    # -----------------------------------------------------------------------

    def test_writable_counter_assignment(self):
        """Vars.counter can be assigned and augmented-assigned."""
        source = """
from mlog import Vars
Vars.counter = 10
Vars.counter += 2
Vars.counter *= 3
"""
        mlog = self.check_compile(source)
        lines = [line.strip() for line in mlog.splitlines()]
        self.assertIn("set @counter 10", lines)
        self.assertIn("op add @counter @counter 2", lines)
        self.assertIn("op mul @counter @counter 3", lines)

    def test_readonly_vars_assignment_rejected(self):
        """Assigning to read-only Vars variables raises CompileError."""
        readonly_cases = [
            "Vars.tick = 10\n",
            "Vars.time = 0.0\n",
            "Vars.unit = None\n",
            "Vars.this = None\n",
            "Vars.waveNumber = 5\n",
            "Vars.blockCount = 100\n",
            "Vars.clientName = 'player'\n",
            "Vars.server = 1\n",
            "Vars.pi = 3.14\n",
        ]
        for case in readonly_cases:
            with self.subTest(case=case.strip()):
                code = f"from mlog import Vars\n{case}"
                with self.assertRaises(CompileError) as ctx:
                    compile_py(code, filename="bad.py")
                self.assertIn("cannot assign to read-only built-in variable", str(ctx.exception))

    def test_readonly_vars_aug_assign_rejected(self):
        """Augmented assignment on read-only Vars variables raises CompileError."""
        readonly_cases = [
            "Vars.tick += 1\n",
            "Vars.time -= 10\n",
            "Vars.unit += 1\n",
            "Vars.waveNumber += 1\n",
            "Vars.blockCount += 1\n",
            "Vars.links *= 2\n",
        ]
        for case in readonly_cases:
            with self.subTest(case=case.strip()):
                code = f"from mlog import Vars\n{case}"
                with self.assertRaises(CompileError) as ctx:
                    compile_py(code, filename="bad.py")
                self.assertIn("cannot assign to read-only built-in variable", str(ctx.exception))

    def test_runtime_python_readonly_protection(self):
        """In native Python runtime, modifying read-only Vars raises AttributeError."""
        with self.assertRaises(AttributeError) as ctx:
            Vars.tick = 100
        self.assertIn("Cannot assign to read-only", str(ctx.exception))

        with self.assertRaises(AttributeError) as ctx:
            Vars.unit = None
        self.assertIn("Cannot assign to read-only", str(ctx.exception))

    # -----------------------------------------------------------------------
    # 5. Invalid / Unknown Token Rejection
    # -----------------------------------------------------------------------

    def test_unknown_vars_attribute_rejected_at_compile_time(self):
        """Accessing non-existent attribute on Vars raises CompileError."""
        bad_cases = [
            "x = Vars.unknownVariable\n",
            "Vars.nonExistent = 10\n",
            "Vars.fakeToken += 1\n",
        ]
        for case in bad_cases:
            with self.subTest(case=case.strip()):
                code = f"from mlog import Vars\n{case}"
                with self.assertRaises(CompileError) as ctx:
                    compile_py(code, filename="bad.py")
                self.assertIn("unknown Mindustry built-in variable", str(ctx.exception))

    def test_runtime_python_unknown_attribute(self):
        """In native Python runtime, accessing unknown Vars raises AttributeError."""
        with self.assertRaises(AttributeError) as ctx:
            _ = Vars.nonExistent
        self.assertIn("Unknown Mindustry built-in variable", str(ctx.exception))

    # -----------------------------------------------------------------------
    # 6. Legacy at_* Aliases Removal Verification
    # -----------------------------------------------------------------------

    def test_legacy_at_aliases_completely_removed(self):
        """Legacy at_* aliases are rejected from imports and do not map to @ registers."""
        # 1. Importing at_* is rejected
        for name in ("at_tick", "at_time", "at_counter", "at_unit", "at_this"):
            with self.assertRaises(CompileError) as ctx:
                compile_py(f"from mlog import {name}\n")
            self.assertIn(f"cannot import name '{name}' from 'mlog'", str(ctx.exception))

        # 2. Identifier at_* is treated as a normal variable name, not @ token
        res = compile_py("at_tick = 42\nx = at_tick")
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        self.assertIn("set at_tick 42", lines)
        self.assertIn("set x at_tick", lines)

    # -----------------------------------------------------------------------
    # 7. Real Mindustry Java Harness Execution
    # -----------------------------------------------------------------------

    def test_mindustry_harness_vars_execution(self):
        """Verify bytecode generated via Vars API executes accurately in Mindustry VM."""
        if not is_mindustry_available():
            self.skipTest("Mindustry Java harness is not available in environment.")

        source = """
from mlog import Vars, print, printflush
t = Vars.tick
w = Vars.waveNumber
msg = "@tick"
print(Vars.tick)
print("@hello")
Vars.counter = 7
print("skipped")
x = 42
"""
        res = compile_py(source, filename="vars_harness.py", validate=True)
        # 1. Validate assembler accept
        valid, val_err, _ = validate_with_mindustry(res.mlog)
        self.assertTrue(valid, f"Mindustry assembler rejected code: {val_err}")

        # 2. Run in Mindustry engine
        success, vars_dict, err = run_with_mindustry(res.mlog, max_steps=50)
        self.assertTrue(success, f"Mindustry engine failed: {err}")
        self.assertEqual(vars_dict.get("x"), 42.0)
        self.assertEqual(vars_dict.get("msg"), "@tick")

    def test_mindustry_harness_counter_aug_assign_jump(self):
        """Verify Vars.counter augmented assignment relative jump semantics in Mindustry VM."""
        if not is_mindustry_available():
            self.skipTest("Mindustry Java harness is not available in environment.")

        source = """
from mlog import Vars
s1 = 0
s2 = 0
dest = 0
Vars.counter += 2
s1 = 1
s2 = 1
dest = 100
"""
        res = compile_py(source, filename="counter_aug_jump.py", validate=True)
        valid, val_err, _ = validate_with_mindustry(res.mlog)
        self.assertTrue(valid, f"Mindustry assembler rejected code: {val_err}")

        success, vars_dict, err = run_with_mindustry(res.mlog, max_steps=50)
        self.assertTrue(success, f"Mindustry engine failed: {err}")
        self.assertEqual(vars_dict.get("s1"), 0.0)
        self.assertEqual(vars_dict.get("s2"), 0.0)
        self.assertEqual(vars_dict.get("dest"), 100.0)


if __name__ == "__main__":
    unittest.main()
