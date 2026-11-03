"""Regression tests for P1 API Ergonomics:
1. status.apply and status.clear helpers.
2. fetch callable namespace methods with automatic dummy operands.
3. uradar default arguments matching Mindustry v160.7 semantics.
"""

import unittest
import mlog
from mlog import compile_py, status, fetch, uradar
from mlog.errors import CompileError
from mlog.validator import MlogValidator
from mlog.mindustry_validator import is_mindustry_available, validate_with_mindustry


class TestP1Ergonomics(unittest.TestCase):
    """Test suite for P1 Ergonomics additions and backward compatibility."""

    def compile_code(self, source: str) -> str:
        """Compile DSL source and validate syntax."""
        res = compile_py(source, validate=True)
        mlog_text = res.mlog.strip()
        MlogValidator.validate(mlog_text)
        return mlog_text

    def validate_with_jvm(self, mlog_text: str):
        """Validate generated mlog against real Mindustry v160.7 engine if available."""
        if is_mindustry_available():
            valid, err, *_ = validate_with_mindustry(mlog_text)
            self.assertTrue(valid, f"JVM validation failed: {err}")

    # =========================================================================
    # 1. status.apply and status.clear
    # =========================================================================

    def test_status_apply_defaults(self):
        source = (
            "from mlog import status, StatusEffects\n"
            "status.apply(unit, StatusEffects.BURNING)\n"
        )
        mlog = self.compile_code(source)
        self.assertEqual(mlog, "status false @status-burning unit 0")
        self.validate_with_jvm(mlog)

    def test_status_apply_with_duration(self):
        source = (
            "from mlog import status, StatusEffects\n"
            "status.apply(unit, '@status-freezing', 10)\n"
        )
        mlog = self.compile_code(source)
        self.assertEqual(mlog, "status false @status-freezing unit 10")
        self.validate_with_jvm(mlog)

    def test_status_apply_with_keywords(self):
        source = (
            "from mlog import status, StatusEffects\n"
            "status.apply(unit=my_unit, effect=StatusEffects.SHOCKED, duration=5.5)\n"
        )
        mlog = self.compile_code(source)
        self.assertEqual(mlog, "status false @status-shocked my_unit 5.5")
        self.validate_with_jvm(mlog)

    def test_status_clear(self):
        source = (
            "from mlog import status, StatusEffects\n"
            "status.clear(unit, StatusEffects.BURNING)\n"
        )
        mlog = self.compile_code(source)
        self.assertEqual(mlog, "status true @status-burning unit 0")
        self.validate_with_jvm(mlog)

    def test_status_clear_with_keywords(self):
        source = (
            "from mlog import status, StatusEffects\n"
            "status.clear(unit=unit, effect='@status-melting')\n"
        )
        mlog = self.compile_code(source)
        self.assertEqual(mlog, "status true @status-melting unit 0")
        self.validate_with_jvm(mlog)

    def test_status_backward_compatibility(self):
        source = (
            "from mlog import status, StatusEffects\n"
            "status(False, StatusEffects.BURNING, unit, 10)\n"
            "status(True, '@status-melting', unit)\n"
            "status(0, StatusEffects.FREEZING, unit, 2.5)\n"
            "status(1, '@status-shocked', unit)\n"
        )
        mlog = self.compile_code(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "status false @status-burning unit 10")
        self.assertEqual(lines[1], "status true @status-melting unit 0")
        self.assertEqual(lines[2], "status false @status-freezing unit 2.5")
        self.assertEqual(lines[3], "status true @status-shocked unit 0")
        self.validate_with_jvm(mlog)

    def test_status_invalid_calls(self):
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import status\nstatus.apply(unit)\n")
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import status\nstatus.clear(unit)\n")
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import status\nstatus.clear(unit, '@status-burning', 10)\n")
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import status\nstatus.unknown(unit)\n")

    # =========================================================================
    # 2. fetch namespace methods
    # =========================================================================

    def test_fetch_unit_expression_and_statement(self):
        source = (
            "from mlog import fetch, Teams, Units\n"
            "u1 = fetch.unit(Teams.SHARDED, 0)\n"
            "u2 = fetch.unit(Teams.CRUX, 1, Units.DAGGER)\n"
            "fetch.unit(Teams.SHARDED, 2, u3)\n"
            "fetch.unit(Teams.CRUX, 3, Units.FLARE, u4)\n"
        )
        mlog = self.compile_code(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "fetch unit u1 @sharded 0 0")
        self.assertEqual(lines[1], "fetch unit u2 @crux 1 @dagger")
        self.assertEqual(lines[2], "fetch unit u3 @sharded 2 0")
        self.assertEqual(lines[3], "fetch unit u4 @crux 3 @flare")
        self.validate_with_jvm(mlog)

    def test_fetch_unit_count(self):
        source = (
            "from mlog import fetch, Teams, Units\n"
            "cnt1 = fetch.unit_count(Teams.SHARDED)\n"
            "cnt2 = fetch.unit_count(Teams.CRUX, Units.DAGGER)\n"
            "cnt3 = fetch.unitCount(Teams.SHARDED)\n"
            "fetch.unit_count(Teams.SHARDED, cnt4)\n"
            "fetch.unitCount(Teams.CRUX, Units.FLARE, cnt5)\n"
        )
        mlog = self.compile_code(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "fetch unitCount cnt1 @sharded 0 0")
        self.assertEqual(lines[1], "fetch unitCount cnt2 @crux 0 @dagger")
        self.assertEqual(lines[2], "fetch unitCount cnt3 @sharded 0 0")
        self.assertEqual(lines[3], "fetch unitCount cnt4 @sharded 0 0")
        self.assertEqual(lines[4], "fetch unitCount cnt5 @crux 0 @flare")
        self.validate_with_jvm(mlog)

    def test_fetch_player_and_player_count(self):
        source = (
            "from mlog import fetch, Teams\n"
            "p1 = fetch.player(Teams.SHARDED, 0)\n"
            "fetch.player(Teams.SHARDED, 1, p2)\n"
            "cnt1 = fetch.player_count(Teams.SHARDED)\n"
            "fetch.playerCount(Teams.SHARDED, cnt2)\n"
        )
        mlog = self.compile_code(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "fetch player p1 @sharded 0 0")
        self.assertEqual(lines[1], "fetch player p2 @sharded 1 0")
        self.assertEqual(lines[2], "fetch playerCount cnt1 @sharded 0 0")
        self.assertEqual(lines[3], "fetch playerCount cnt2 @sharded 0 0")
        self.validate_with_jvm(mlog)

    def test_fetch_core_and_core_count(self):
        source = (
            "from mlog import fetch, Teams\n"
            "c1 = fetch.core(Teams.SHARDED, 0)\n"
            "fetch.core(Teams.SHARDED, 1, c2)\n"
            "cnt1 = fetch.core_count(Teams.SHARDED)\n"
            "fetch.coreCount(Teams.SHARDED, cnt2)\n"
        )
        mlog = self.compile_code(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "fetch core c1 @sharded 0 0")
        self.assertEqual(lines[1], "fetch core c2 @sharded 1 0")
        self.assertEqual(lines[2], "fetch coreCount cnt1 @sharded 0 0")
        self.assertEqual(lines[3], "fetch coreCount cnt2 @sharded 0 0")
        self.validate_with_jvm(mlog)

    def test_fetch_build_and_build_count(self):
        source = (
            "from mlog import fetch, Teams\n"
            "b1 = fetch.build(Teams.SHARDED, 0, '@router')\n"
            "fetch.build(Teams.SHARDED, 1, '@conveyor', b2)\n"
            "bc1 = fetch.build_count(Teams.SHARDED, '@router')\n"
            "fetch.buildCount(Teams.SHARDED, '@conveyor', bc2)\n"
        )
        mlog = self.compile_code(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "fetch build b1 @sharded 0 @router")
        self.assertEqual(lines[1], "fetch build b2 @sharded 1 @conveyor")
        self.assertEqual(lines[2], "fetch buildCount bc1 @sharded 0 @router")
        self.assertEqual(lines[3], "fetch buildCount bc2 @sharded 0 @conveyor")
        self.validate_with_jvm(mlog)

    def test_fetch_backward_compatibility(self):
        source = (
            "from mlog import fetch, FetchType, Teams, Units\n"
            "u = fetch(FetchType.UNIT, Teams.SHARDED, 0, Units.DAGGER)\n"
            "fetch(FetchType.CORE, c, Teams.SHARDED)\n"
        )
        mlog = self.compile_code(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "fetch unit u @sharded 0 @dagger")
        self.assertEqual(lines[1], "fetch core c @sharded 0 0")
        self.validate_with_jvm(mlog)

    def test_fetch_invalid_calls(self):
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import fetch\nfetch.unit()\n")
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import fetch, Teams\nfetch.build(Teams.SHARDED, 0)\n")
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import fetch, Teams\nfetch.build_count(Teams.SHARDED)\n")
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import fetch, Teams\nfetch.core(Teams.SHARDED)\n")
        with self.assertRaises(CompileError):
            self.compile_code("from mlog import fetch\nfetch.unknown(1)\n")

    # =========================================================================
    # 3. uradar default arguments
    # =========================================================================

    def test_uradar_zero_args(self):
        source = (
            "from mlog import uradar\n"
            "target = uradar()\n"
        )
        mlog = self.compile_code(source)
        self.assertEqual(mlog, "uradar enemy any any distance 0 1 target")
        self.validate_with_jvm(mlog)

    def test_uradar_one_arg(self):
        source = (
            "from mlog import uradar, RadarTarget\n"
            "target = uradar(RadarTarget.PLAYER)\n"
        )
        mlog = self.compile_code(source)
        self.assertEqual(mlog, "uradar player any any distance 0 1 target")
        self.validate_with_jvm(mlog)

    def test_uradar_two_args(self):
        source = (
            "from mlog import uradar, RadarTarget\n"
            "target = uradar(RadarTarget.ENEMY, RadarTarget.ATTACKER)\n"
        )
        mlog = self.compile_code(source)
        self.assertEqual(mlog, "uradar enemy attacker any distance 0 1 target")
        self.validate_with_jvm(mlog)

    def test_uradar_three_args(self):
        source = (
            "from mlog import uradar, RadarTarget\n"
            "target = uradar(RadarTarget.ENEMY, RadarTarget.ANY, RadarTarget.FLYING)\n"
        )
        mlog = self.compile_code(source)
        self.assertEqual(mlog, "uradar enemy any flying distance 0 1 target")
        self.validate_with_jvm(mlog)

    def test_uradar_four_args(self):
        source = (
            "from mlog import uradar, RadarTarget, RadarSort\n"
            "target = uradar(RadarTarget.ENEMY, RadarTarget.ANY, RadarTarget.FLYING, RadarSort.MAX_HEALTH)\n"
        )
        mlog = self.compile_code(source)
        self.assertEqual(mlog, "uradar enemy any flying maxHealth 0 1 target")
        self.validate_with_jvm(mlog)

    def test_uradar_five_args(self):
        source = (
            "from mlog import uradar, RadarTarget, RadarSort\n"
            "target = uradar(RadarTarget.ENEMY, RadarTarget.ANY, RadarTarget.FLYING, RadarSort.MAX_HEALTH, 0)\n"
        )
        mlog = self.compile_code(source)
        self.assertEqual(mlog, "uradar enemy any flying maxHealth 0 0 target")
        self.validate_with_jvm(mlog)

    def test_uradar_backward_compatibility(self):
        source = (
            "from mlog import uradar, RadarTarget, RadarSort\n"
            "uradar(RadarTarget.ENEMY, RadarTarget.ANY, RadarTarget.ANY, RadarSort.DISTANCE, 1, t1)\n"
            "uradar(RadarTarget.ENEMY, RadarTarget.ANY, RadarTarget.ANY, RadarSort.DISTANCE, 0, 1, t2)\n"
        )
        mlog = self.compile_code(source)
        lines = mlog.splitlines()
        self.assertEqual(lines[0], "uradar enemy any any distance 0 1 t1")
        self.assertEqual(lines[1], "uradar enemy any any distance 0 1 t2")
        self.validate_with_jvm(mlog)

    def test_uradar_invalid_calls(self):
        with self.assertRaises(CompileError):
            # 8 arguments exceeds maximum 7
            self.compile_code("from mlog import uradar\nt = uradar(1, 2, 3, 4, 5, 6, 7, 8)\n")

    # =========================================================================
    # 4. Pure Python runtime execution
    # =========================================================================

    def test_pure_python_runtime_callability(self):
        self.assertIsNone(status.apply("unit", "@status-burning"))
        self.assertIsNone(status.apply("unit", "@status-burning", duration=10))
        self.assertIsNone(status.clear("unit", "@status-burning"))
        self.assertIsNone(status(False, "@status-burning", "unit", 10))

        self.assertIsNone(fetch.unit("team", 0))
        self.assertEqual(fetch.unit_count("team"), 0)
        self.assertEqual(fetch.unitCount("team"), 0)
        self.assertIsNone(fetch.player("team", 0))
        self.assertEqual(fetch.player_count("team"), 0)
        self.assertEqual(fetch.playerCount("team"), 0)
        self.assertIsNone(fetch.core("team", 0))
        self.assertEqual(fetch.core_count("team"), 0)
        self.assertEqual(fetch.coreCount("team"), 0)
        self.assertIsNone(fetch.build("team", 0, "@router"))
        self.assertEqual(fetch.build_count("team", "@router"), 0)
        self.assertEqual(fetch.buildCount("team", "@router"), 0)
        self.assertIsNone(fetch("unit", "team", 0))

        self.assertEqual(uradar(), 0)
        self.assertEqual(uradar("enemy"), 0)


if __name__ == "__main__":
    unittest.main()
