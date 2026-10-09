"""Demonstration of Python-to-MLog compilation workflow.

Usage:
    python3 examples/compiler/roundtrip_demo.py
"""

from src.mlog import compile_py

DEMOS = [
    (
        "Reactor Safety System (Sensors & Conditionals)",
        """from mlog import sensor, control, wait, SensorProperty, ControlProperty

heat = sensor("reactor1", SensorProperty.HEAT)
if heat > 0.5:
    control(ControlProperty.ENABLED, "reactor1", 0)
else:
    control(ControlProperty.ENABLED, "reactor1", 1)
wait(0.5)
""",
    ),
    (
        "For-Range Loop with Break & Continue in If Branches",
        """total = 0
for i in range(1, 10, 2):
    if i == 5:
        continue
    if i > 7:
        break
    total = total + i
""",
    ),
    (
        "Bitwise Operations & Min/Max Built-ins",
        """val1 = 42
val2 = 255
masked = (val1 & 15) | 128
bounded = min(max(masked, 0), 100)
""",
    ),
]


def main():
    print("=== PYTHON-TO-MLOG COMPILATION WORKFLOW DEMOS ===\n")
    for title, code in DEMOS:
        print(f"--- {title} ---")
        print("Source Python DSL:")
        print(code.strip())
        print("\nCompiled MLog Output:")
        res = compile_py(code)
        print(res.mlog.strip())
        lines = [l for l in res.mlog.splitlines() if l.strip()]
        print(f"Instruction count: {len(lines)}\n")


if __name__ == "__main__":
    main()
