#!/usr/bin/env python3
"""Test runner with tiered execution support for mlog-py.

Provides fast feedback loops for development and full validation suites:
- Fast tier: Pure Python tests (compiler, decompiler, AST, dataflow, optimizer, CLI) in ~6s.
- JVM tier: Real Mindustry v160.7 engine integration tests in ~45s.
- Full suite: All 1,224 tests discovered via unittest in ~88s.
"""

import argparse
import os
import sys
import time
import unittest

JVM_TEST_MODULES = {
    "test_tier3_runtime",
    "test_tier4_world_state",
    "test_tier4_combat_spawning",
    "test_tier4_rules_and_queries",
    "test_tier4_weather_and_effects",
    "test_tier4_messaging_and_cutscene",
    "test_tier4_audio_markers_and_final",
    "test_phase2_control_flow",
    "test_phase2_semantics",
    "test_phase2_golden",
    "test_print_buffer_semantics",
    "test_min_max_support",
    "test_bitwise_support",
    "test_for_loop",
    "test_array",
    "test_constant_folding",
    "test_aug_assign",
    "test_builtins_and_properties",
    "test_vars_api",
    "test_modulo_semantics",
    "test_fstring_formatting",
    "test_select_and_ternary",
    "test_memory_bank_header_protocol",
    "test_noop",
}


def _split_suite(suite, pure_suite, jvm_suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            _split_suite(item, pure_suite, jvm_suite)
        else:
            mod = item.__class__.__module__
            if mod.startswith("tests."):
                mod = mod[len("tests."):]
            if mod in JVM_TEST_MODULES:
                jvm_suite.addTest(item)
            else:
                pure_suite.addTest(item)


def main():
    parser = argparse.ArgumentParser(description="mlog-py tiered test runner")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--fast", "-f",
        action="store_true",
        help="Run pure Python unit tests only (~600+ tests in ~6s)",
    )
    group.add_argument(
        "--jvm", "-j",
        action="store_true",
        help="Run Mindustry JVM-backed runtime & validation tests (~600+ tests)",
    )
    group.add_argument(
        "--all", "-a",
        action="store_true",
        help="Run full test suite (all 1,224 tests)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose test output",
    )
    parser.add_argument(
        "-k",
        dest="pattern",
        default=None,
        help="Only run tests matching pattern/substring",
    )
    args = parser.parse_args()

    # Discover all tests
    loader = unittest.defaultTestLoader
    discovered = loader.discover("tests", pattern="test_*.py")

    pure_suite = unittest.TestSuite()
    jvm_suite = unittest.TestSuite()
    _split_suite(discovered, pure_suite, jvm_suite)

    if args.fast:
        selected_suite = pure_suite
        mode_label = f"FAST TIER (Pure Python: {pure_suite.countTestCases()} tests)"
    elif args.jvm:
        selected_suite = jvm_suite
        mode_label = f"JVM TIER (Mindustry Engine: {jvm_suite.countTestCases()} tests)"
    else:
        selected_suite = discovered
        mode_label = f"FULL SUITE (All: {discovered.countTestCases()} tests)"

    print(f"=== Running {mode_label} ===")
    t0 = time.time()
    runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
    result = runner.run(selected_suite)
    elapsed = time.time() - t0

    print(f"\nCompleted in {elapsed:.2f}s | Ran: {result.testsRun} | Passed: {result.testsRun - len(result.failures) - len(result.errors)} | Failures: {len(result.failures)} | Errors: {len(result.errors)}")

    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
