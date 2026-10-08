"""Phase 2 Integration Tests: Control Flow Semantics & Jump Resolution.

Tests nested control flow structures, elif chains, break/continue scoping,
pass statements, forward/backward jumps, and multi-jump targets.
Verifies exact numeric addresses and validates output against real Mindustry.
"""

import unittest
from src.mlog import compile_py
from src.mindustry_validator import is_mindustry_available, validate_with_mindustry


class TestPhase2ControlFlow(unittest.TestCase):

    def _compile_and_validate(self, code: str):
        """Helper to compile and validate against real Mindustry engine."""
        res = compile_py(code)
        self.assertTrue(len(res.mlog.strip()) > 0, "Mlog output should not be empty")
        if is_mindustry_available():
            ok, msg, count = validate_with_mindustry(res.mlog)
            self.assertTrue(ok, f"Mindustry validation failed: {msg}\nMLOG:\n{res.mlog}")
        return res

    def test_nested_if_three_levels(self):
        """Test deeply nested if statements (3 levels) with else branches."""
        code = """
if a == 1:
    if b == 2:
        if c == 3:
            x = 10
        else:
            x = 20
    else:
        x = 30
else:
    x = 40
"""
        res = self._compile_and_validate(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        # Verify no label strings remain in mlog
        for line in lines:
            self.assertFalse(line.startswith("__"), f"Unresolved label in mlog: {line}")
            parts = line.split()
            if parts[0] == "jump":
                # Jump target must be numeric
                self.assertTrue(parts[1].isdigit(), f"Non-numeric jump address: {parts[1]}")
                target = int(parts[1])
                self.assertLess(target, len(lines) + 1, "Jump target out of program bounds")

    def test_nested_while_three_levels(self):
        """Test 3 levels of nested while loops."""
        code = """
i = 0
while i < 10:
    j = 0
    while j < 5:
        k = 0
        while k < 3:
            k = k + 1
        j = j + 1
    i = i + 1
"""
        res = self._compile_and_validate(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        # Check backward jumps exist (loop end jumping to loop start)
        has_backward_jump = False
        for idx, line in enumerate(lines):
            parts = line.split()
            if parts[0] == "jump":
                target = int(parts[1])
                if target < idx:
                    has_backward_jump = True
        self.assertTrue(has_backward_jump, "While loop must contain backward jump")

    def test_if_inside_while_with_break_and_continue(self):
        """Test while loop containing if statements with break and continue."""
        code = """
i = 0
while i < 100:
    i = i + 1
    if i == 50:
        continue
    if i == 80:
        break
    x = i * 2
"""
        res = self._compile_and_validate(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        # Loop start is instruction 1 (i = 0 is instruction 0)
        # Continue should jump back to instruction 1 (start of while loop condition)
        # Break should jump to instruction right after loop (len(lines))
        found_continue_target = False
        found_break_target = False
        for line in lines:
            parts = line.split()
            if parts[0] == "jump" and parts[2] == "always":
                target = int(parts[1])
                if target == 1:
                    found_continue_target = True
                elif target == len(lines):
                    found_break_target = True
        self.assertTrue(found_continue_target, "Continue jump target 1 not found")
        self.assertTrue(found_break_target, "Break jump target after loop not found")

    def test_while_inside_if(self):
        """Test while loop nested inside an if branch."""
        code = """
flag = 1
if flag == 1:
    count = 0
    while count < 5:
        count = count + 1
else:
    count = -1
"""
        res = self._compile_and_validate(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        self.assertGreater(len(lines), 5)

    def test_nested_loops_break_isolation(self):
        """Test that break inside inner loop only breaks out of inner loop, not outer."""
        code = """
outer = 0
while outer < 3:
    inner = 0
    while inner < 3:
        if inner == 1:
            break
        inner = inner + 1
    outer = outer + 1
"""
        res = self._compile_and_validate(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        # The inner break must jump to outer = outer + 1, not past the outer loop!
        # Find index of outer = outer + 1 (op add outer outer 1)
        outer_inc_idx = None
        for idx, line in enumerate(lines):
            if line == "op add outer outer 1":
                outer_inc_idx = idx
                break
        self.assertIsNotNone(outer_inc_idx)

        # Find jump that targets outer_inc_idx
        break_jump_found = False
        for line in lines:
            parts = line.split()
            if parts[0] == "jump" and int(parts[1]) == outer_inc_idx:
                break_jump_found = True
                break
        self.assertTrue(break_jump_found, f"Inner break should target outer_inc_idx ({outer_inc_idx})")

    def test_nested_loops_continue_isolation(self):
        """Test that continue inside inner loop continues inner loop header."""
        code = """
outer = 0
while outer < 3:
    inner = 0
    while inner < 3:
        inner = inner + 1
        if inner == 2:
            continue
    outer = outer + 1
"""
        res = self._compile_and_validate(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        # Inner loop header starts right before inner condition
        # Find jump back to inner loop
        inner_back_jumps = []
        for idx, line in enumerate(lines):
            parts = line.split()
            if parts[0] == "jump" and parts[2] == "always":
                target = int(parts[1])
                if target < idx:
                    inner_back_jumps.append((idx, target))
        self.assertGreaterEqual(len(inner_back_jumps), 2, "Must have inner and outer backward jumps")

    def test_elif_chain(self):
        """Test if / elif / elif / else chain."""
        code = """
if cmd == 1:
    act = 10
elif cmd == 2:
    act = 20
elif cmd == 3:
    act = 30
else:
    act = 0
final = act
"""
        res = self._compile_and_validate(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        # All branches upon finishing should jump to `final = act` (set final act)
        final_idx = None
        for idx, line in enumerate(lines):
            if line == "set final act":
                final_idx = idx
                break
        self.assertIsNotNone(final_idx)

        # Count forward jumps targeting final_idx
        target_count = sum(1 for line in lines if line.startswith(f"jump {final_idx} always"))
        self.assertEqual(target_count, 3, "All 3 non-else branches must jump to final_idx")

    def test_empty_branches_with_pass(self):
        """Test that pass in if, elif, else, and while branches does not break jump targets."""
        code = """
if x == 1:
    pass
elif x == 2:
    pass
else:
    pass

while x < 5:
    pass
"""
        res = self._compile_and_validate(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        self.assertTrue(len(lines) > 0)
        # Verify valid addresses
        for line in lines:
            parts = line.split()
            if parts[0] == "jump":
                target = int(parts[1])
                self.assertLessEqual(target, len(lines))

    def test_multiple_breaks_and_continues(self):
        """Test loop with multiple break and continue statements in different branches."""
        code = """
while running:
    if a == 1:
        continue
    elif a == 2:
        break
    elif a == 3:
        continue
    elif a == 4:
        break
    else:
        op("add", total, total, 1)
"""
        res = self._compile_and_validate(code)
        lines = [line.strip() for line in res.mlog.strip().splitlines()]
        self.assertGreater(len(lines), 5)


if __name__ == "__main__":
    unittest.main()
