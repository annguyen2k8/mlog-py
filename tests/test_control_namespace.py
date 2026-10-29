"""Tests for the Mindustry v160.7 building-control callable namespace.

Covers all five ``LAccess`` control modes (enabled, shoot, shootp, config, color),
legacy ``control(...)`` compatibility, dummy-argument injection, object/content
operands, validation errors, opcode serialization, and decompiler round-trips.
"""

import unittest

from src.decompiler import decompile
from src.errors import CompileError
from src.ir import IRRaw
from src.mlog import ControlProperty, Items, compile_py
import src.mlog as mlog


class TestControlNamespaceCompilation(unittest.TestCase):
    """Compile ``control.<method>(...)`` into canonical v160.7 control opcodes."""

    def compile(self, source: str) -> str:
        return compile_py(source, filename="control_namespace.py").mlog.strip()

    def test_enabled(self):
        mlog_out = self.compile(
            "from mlog import control\n"
            "control.enabled(reactor1, 1)\n"
            "control.enabled(reactor1, False)\n"
        )
        self.assertEqual(
            mlog_out.splitlines(),
            [
                "control enabled reactor1 1 0 0 0",
                "control enabled reactor1 false 0 0 0",
            ],
        )

    def test_shoot(self):
        mlog_out = self.compile(
            "from mlog import control\n"
            "control.shoot(turret1, 10, 20, 1)\n"
            "control.shoot(turret1, tx, ty, shoot)\n"
        )
        self.assertEqual(
            mlog_out.splitlines(),
            [
                "control shoot turret1 10 20 1 0",
                "control shoot turret1 tx ty shoot 0",
            ],
        )

    def test_shootp_object_and_variable(self):
        mlog_out = self.compile(
            "from mlog import control\n"
            'control.shootp(turret1, "@unit", 1)\n'
            "control.shootp(turret1, unit1, 1)\n"
        )
        self.assertEqual(
            mlog_out.splitlines(),
            [
                "control shootp turret1 @unit 1 0 0",
                "control shootp turret1 unit1 1 0 0",
            ],
        )

    def test_config_content_token_and_numeric(self):
        mlog_out = self.compile(
            "from mlog import control, Items\n"
            'control.config(sorter1, "@copper")\n'
            "control.config(sorter1, Items.COPPER)\n"
            "control.config(sorter1, 3)\n"
        )
        self.assertEqual(
            mlog_out.splitlines(),
            [
                "control config sorter1 @copper 0 0 0",
                "control config sorter1 @copper 0 0 0",
                "control config sorter1 3 0 0 0",
            ],
        )

    def test_config_plain_string_stays_quoted(self):
        mlog_out = self.compile(
            "from mlog import control\n"
            'control.config(message1, "hello")\n'
        )
        self.assertEqual(mlog_out, 'control config message1 "hello" 0 0 0')

    def test_color(self):
        mlog_out = self.compile(
            "from mlog import control\n"
            "control.color(light1, 12345)\n"
            "control.color(light1, packed)\n"
        )
        self.assertEqual(
            mlog_out.splitlines(),
            [
                "control color light1 12345 0 0 0",
                "control color light1 packed 0 0 0",
            ],
        )

    def test_string_link_target(self):
        mlog_out = self.compile(
            "from mlog import control\n"
            'control.enabled("reactor1", 1)\n'
        )
        self.assertEqual(mlog_out, "control enabled reactor1 1 0 0 0")

    def test_ir_opcode_serialization(self):
        res = compile_py(
            "from mlog import control\n"
            'control.config(sorter1, "@copper")\n'
        )
        raw = [node for node in res.ir if isinstance(node, IRRaw) and node.opcode == "control"]
        self.assertEqual(len(raw), 1)
        self.assertEqual(
            raw[0].args,
            ["config", "sorter1", "@copper", "0", "0", "0"],
        )


class TestControlLegacyCompatibility(unittest.TestCase):
    """Legacy ``control(type, target, p1..p4)`` remains fully supported."""

    def test_legacy_all_modes(self):
        source = (
            "from mlog import control, ControlProperty\n"
            'control("enabled", reactor1, 1)\n'
            "control(ControlProperty.SHOOT, turret1, 10, 20, 1)\n"
            'control("shootp", turret1, "@unit", 1)\n'
            'control("config", sorter1, "@copper")\n'
            'control("color", light1, 12345)\n'
        )
        lines = compile_py(source).mlog.strip().splitlines()
        self.assertEqual(
            lines,
            [
                "control enabled reactor1 1 0 0 0",
                "control shoot turret1 10 20 1 0",
                "control shootp turret1 @unit 1 0 0",
                "control config sorter1 @copper 0 0 0",
                "control color light1 12345 0 0 0",
            ],
        )

    def test_legacy_default_dummy_arguments(self):
        lines = compile_py(
            "from mlog import control\n"
            'control("shoot", turret1, 10, 20)\n'
        ).mlog.strip()
        self.assertEqual(lines, "control shoot turret1 10 20 0 0")

    def test_legacy_plain_string_config_stays_quoted(self):
        lines = compile_py(
            "from mlog import control\n"
            'control("config", message1, "hello")\n'
        ).mlog.strip()
        self.assertEqual(lines, 'control config message1 "hello" 0 0 0')

    def test_legacy_unknown_property_rejected(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py('from mlog import control\ncontrol("bogus", block1, 1)\n')
        self.assertIn("unknown control property 'bogus'", str(ctx.exception))


class TestControlValidation(unittest.TestCase):
    """Invalid namespace calls produce descriptive CompileError messages."""

    def test_invalid_arity(self):
        cases = [
            ("control.enabled(reactor1)", "expected control.enabled(target, value)"),
            ("control.enabled(reactor1, 1, 0)", "expected control.enabled(target, value)"),
            ("control.shoot(turret1, 1, 2)", "expected control.shoot(target, x, y, shoot)"),
            ("control.shootp(turret1, 1)", "expected control.shootp(target, unit, shoot)"),
            ("control.config(sorter1)", "expected control.config(target, value)"),
            ("control.color(light1)", "expected control.color(target, value)"),
        ]
        for call, message in cases:
            with self.subTest(call=call):
                with self.assertRaises(CompileError) as ctx:
                    compile_py(f"from mlog import control\n{call}\n")
                self.assertIn(message, str(ctx.exception))

    def test_keyword_arguments_rejected(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py(
                "from mlog import control\n"
                "control.enabled(reactor1, value=1)\n"
            )
        self.assertIn("expected control.enabled(target, value)", str(ctx.exception))

    def test_unknown_method_rejected(self):
        with self.assertRaises(CompileError) as ctx:
            compile_py(
                "from mlog import control\n"
                "control.toggle(reactor1, 1)\n"
            )
        self.assertIn("unknown control method", str(ctx.exception))


class TestControlDecompiler(unittest.TestCase):
    """Decompiler recognizes canonical control modes and round-trips exactly."""

    def test_all_modes_decompile_to_methods_and_roundtrip(self):
        mlog_in = (
            "control enabled reactor1 1 0 0 0\n"
            "control shoot turret1 10 20 1 0\n"
            "control shootp turret1 @unit 1 0 0\n"
            "control config sorter1 @copper 0 0 0\n"
            "control color light1 12345 0 0 0\n"
        )
        py = decompile(mlog_in)
        self.assertIn('control.enabled("reactor1", 1)', py)
        self.assertIn('control.shoot("turret1", 10, 20, 1)', py)
        self.assertIn('control.shootp("turret1", "@unit", 1)', py)
        self.assertIn('control.config("sorter1", "@copper")', py)
        self.assertIn('control.color("light1", 12345)', py)

        recompiled = compile_py(py).mlog.strip().splitlines()
        self.assertEqual(recompiled, mlog_in.strip().splitlines())

    def test_noncanonical_dummy_arguments_use_generic_fallback(self):
        py = decompile("control enabled reactor1 1 5 0 0\n")
        self.assertIn('control("enabled", "reactor1", 1, 5, 0, 0)', py)
        self.assertNotIn("control.enabled(", py)

        recompiled = compile_py(py).mlog.strip()
        self.assertEqual(recompiled, "control enabled reactor1 1 5 0 0")

    def test_generic_shoot_with_nonzero_p4_uses_fallback(self):
        py = decompile("control shoot turret1 1 2 1 9\n")
        self.assertIn('control("shoot", "turret1", 1, 2, 1, 9)', py)
        self.assertNotIn("control.shoot(", py)


class TestControlRuntimeCallability(unittest.TestCase):
    """Runtime stubs are directly executable in pure Python."""

    def test_runtime_calls_return_none(self):
        self.assertIsNone(mlog.control("enabled", "reactor1", 1))
        self.assertIsNone(mlog.control.enabled("reactor1", 1))
        self.assertIsNone(mlog.control.shoot("turret1", 10, 20, 1))
        self.assertIsNone(mlog.control.shootp("turret1", "@unit", 1))
        self.assertIsNone(mlog.control.config("sorter1", "@copper"))
        self.assertIsNone(mlog.control.color("light1", 12345))

    def test_runtime_namespace_shape(self):
        for method in ("enabled", "shoot", "shootp", "config", "color"):
            self.assertTrue(callable(getattr(mlog.control, method)))


class TestControlReviewRegressions(unittest.TestCase):
    """Regressions for quoted @ operands, color literals, and dummy token spelling."""

    def compile(self, source: str) -> str:
        return compile_py(source, filename="control_regressions.py").mlog.strip()

    def test_invalid_at_token_rejected_at_source_argument(self):
        cases = [
            'control.config(message1, "@not a content")\n',
            'control.enabled("@not a content", 1)\n',
            'control("config", message1, "@not a content")\n',
            'control.config(message1, "@bad#token")\n',
            'control.config(message1, "@bad;token")\n',
        ]
        for call in cases:
            with self.subTest(call=call):
                with self.assertRaises(CompileError) as ctx:
                    compile_py("from mlog import control\n" + call)
                self.assertIn("invalid control '@' token", str(ctx.exception))
                self.assertEqual(ctx.exception.loc.line, 2)
                self.assertGreater(ctx.exception.loc.col, 1)

    def test_quoted_at_string_allowed_via_raw(self):
        mlog_out = self.compile(
            "from mlog import control, raw\n"
            "control.config(message1, raw('\"@not a content\"'))\n"
        )
        self.assertEqual(mlog_out, 'control config message1 "@not a content" 0 0 0')

    def test_quoted_at_operands_roundtrip_with_raw(self):
        mlog_in = (
            'control shootp turret1 "@unit" 1 0 0\n'
            'control config sorter1 "@copper" 0 0 0\n'
            'control config message1 "@not a content" 0 0 0\n'
            'control shootp turret1 "@unit" 1 5 0\n'
        )
        py = decompile(mlog_in)
        self.assertIn("from mlog import control, raw", py)
        self.assertIn("raw('\"@unit\"')", py)
        self.assertIn("raw('\"@copper\"')", py)
        self.assertIn("raw('\"@not a content\"')", py)
        self.assertEqual(compile_py(py).mlog.strip(), mlog_in.strip())

    def test_bare_at_operands_stay_bare(self):
        mlog_in = (
            "control shootp turret1 @unit 1 0 0\n"
            "control config sorter1 @copper 0 0 0\n"
        )
        py = decompile(mlog_in)
        self.assertNotIn("raw(", py)
        self.assertEqual(compile_py(py).mlog.strip(), mlog_in.strip())

    def test_plain_quoted_string_config_roundtrip(self):
        mlog_in = 'control config message1 "hello world" 0 0 0\n'
        py = decompile(mlog_in)
        self.assertIn('control.config("message1", "hello world")', py)
        self.assertEqual(compile_py(py).mlog.strip(), mlog_in.strip())

    def test_color_literal_roundtrip(self):
        mlog_in = "control color light1 %ffffffff 0 0 0\n"
        py = decompile(mlog_in)
        self.assertIn("raw('%ffffffff')", py)
        self.assertEqual(compile_py(py).mlog.strip(), mlog_in.strip())

    def test_noncanonical_zero_dummies_preserve_spelling(self):
        for dummy in ("0.0", "-0.0", "0e0", "00"):
            with self.subTest(dummy=dummy):
                mlog_in = f"control shoot turret1 1 2 1 {dummy}\n"
                py = decompile(mlog_in)
                self.assertNotIn("control.shoot(", py)
                self.assertIn('control("shoot"', py)
                self.assertEqual(compile_py(py).mlog.strip(), mlog_in.strip())


if __name__ == "__main__":
    unittest.main()
