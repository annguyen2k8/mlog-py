"""Demonstration of Python-to-MLog compilation workflow.

Usage:
    python3 examples/compiler/roundtrip_demo.py
"""

from src.mlog import compile_py

PYTHON_CODE = """# Reactor Safety System
from mlog import sensor, control, wait, SensorProperty, ControlProperty

heat = sensor("reactor1", SensorProperty.HEAT)
if heat > 0.5:
    control(ControlProperty.ENABLED, "reactor1", 0)
else:
    control(ControlProperty.ENABLED, "reactor1", 1)
wait(0.5)
"""

def main():
    print("=== SOURCE PYTHON DSL ===")
    print(PYTHON_CODE)

    print("=== COMPILING TO MLOG ===")
    result = compile_py(PYTHON_CODE, filename="reactor_safety.py")
    print(result.mlog)

    print("=== COMPILED INSTRUCTION COUNT ===")
    lines = [l for l in result.mlog.splitlines() if l.strip()]
    print(f"Total instructions: {len(lines)}")

if __name__ == "__main__":
    main()
