"""Phase 2 Golden Tests: End-to-End Real-World Mindustry Logic Programs.

Tests realistic automation scripts across Unit Control, Reactor Management,
Display Rendering, Memory Cell Operations, and Turret Radar Targeting.
Validates exact behavior and executes through Mindustry's real LParser & LAssembler.
"""

import unittest
from src.errors import CompileError
from src.mlog import compile_py
from src.mindustry_validator import is_mindustry_available, validate_with_mindustry


class TestPhase2Golden(unittest.TestCase):

    def _compile_and_validate(self, code: str):
        """Helper to compile and validate against real Mindustry engine."""
        res = compile_py(code)
        self.assertTrue(len(res.mlog.strip()) > 0)
        if is_mindustry_available():
            ok, msg, count = validate_with_mindustry(res.mlog)
            self.assertTrue(ok, f"Mindustry validation failed: {msg}\nMLOG:\n{res.mlog}")
        return res

    def test_golden_reactor_monitor(self):
        """Golden Test 1: Thorium reactor heat/cryofluid failsafe controller."""
        code = """
heat = sensor(reactor1, "@heat")
cryo = sensor(reactor1, "@cryofluid")

if heat > 0.5 or cryo < 10:
    control("enabled", reactor1, 0)
else:
    control("enabled", reactor1, 1)

wait(0.5)
"""
        res = self._compile_and_validate(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        # Verify instructions
        self.assertEqual(lines[0], "sensor heat reactor1 @heat")
        self.assertEqual(lines[1], "sensor cryo reactor1 @cryofluid")
        self.assertTrue(any("control enabled reactor1 0" in l for l in lines))
        self.assertTrue(any("control enabled reactor1 1" in l for l in lines))
        self.assertEqual(lines[-1], "wait 0.5")

    def test_golden_unit_controller(self):
        """Golden Test 2: Unit binding and move order loop."""
        code = """
ubind("@flare")
flag = 1
ucontrol("flag", flag)
ucontrol("move", 150, 200)
ucontrol("approach", 150, 200, 5)
"""
        res = self._compile_and_validate(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        self.assertEqual(lines[0], "ubind @flare")
        self.assertEqual(lines[1], "set flag 1")
        self.assertEqual(lines[2], "ucontrol flag flag 0 0 0 0")
        self.assertEqual(lines[3], "ucontrol move 150 200 0 0 0")
        self.assertEqual(lines[4], "ucontrol approach 150 200 5 0 0")

    def test_golden_display_renderer(self):
        """Golden Test 3: Display canvas drawing sequence."""
        code = """
draw("clear", 0, 0, 0)
draw("color", 255, 128, 0, 255)
draw("line", 10, 10, 80, 80)
draw("rect", 20, 20, 40, 40)
drawflush(display1)
"""
        res = self._compile_and_validate(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        self.assertEqual(lines[0], "draw clear 0 0 0 0 0 0")
        self.assertEqual(lines[1], "draw color 255 128 0 255 0 0")
        self.assertEqual(lines[2], "draw line 10 10 80 80 0 0")
        self.assertEqual(lines[3], "draw rect 20 20 40 40 0 0")
        self.assertEqual(lines[4], "drawflush display1")

    def test_golden_memory_cell_accumulator(self):
        """Golden Test 4: Memory cell loop summing values and reporting to message block."""
        code = """
idx = 0
total = 0
while idx < 64:
    val = read(cell1, idx)
    total = total + val
    idx = idx + 1

write(total, cell1, 63)
print("Total: ")
print(total)
printflush(message1)
"""
        res = self._compile_and_validate(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        self.assertEqual(lines[0], "set idx 0")
        self.assertEqual(lines[1], "set total 0")
        self.assertTrue(any("read val cell1 idx" in l for l in lines))
        self.assertTrue(any("write total cell1 63" in l for l in lines))
        self.assertTrue(any('print "Total: "' in l for l in lines))
        self.assertTrue(any("print total" in l for l in lines))
        self.assertEqual(lines[-1], "printflush message1")

    def test_golden_radar_turret_targeting(self):
        """Golden Test 5: Radar scanning and turret aim targeting."""
        code = """
target = radar("enemy", "any", "any", "distance", turret1, 1)
if target != null:
    tx = sensor(target, "@x")
    ty = sensor(target, "@y")
    control("shoot", turret1, tx, ty, 1)
else:
    control("shoot", turret1, 0, 0, 0)
"""
        res = self._compile_and_validate(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        self.assertEqual(lines[0], "radar enemy any any distance turret1 1 target")
        self.assertTrue(any("sensor tx target @x" in l for l in lines))
        self.assertTrue(any("sensor ty target @y" in l for l in lines))
        self.assertTrue(any("control shoot turret1 tx ty 1" in l for l in lines))
        self.assertTrue(any("control shoot turret1 0 0 0" in l for l in lines))


if __name__ == "__main__":
    unittest.main()
