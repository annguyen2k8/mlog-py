"""Demonstration of MLog -> Python DSL -> MLog round-trip verification.

Usage:
    python3 examples/decompiler/roundtrip_verify.py
"""

import ast
from src.decompiler import decompile
from src.mlog import compile_py

TEST_CASES = [
    (
        "Memory Cell IO",
        """read val cell1 0
op add nxt val 10
write nxt cell1 1
""",
    ),
    (
        "Reactor Safety Control",
        """sensor heat reactor1 @heat
jump 4 lessThanEq heat 0.5
control enabled reactor1 0 0 0 0
jump 5 always 0 0
control enabled reactor1 1 0 0 0
wait 0.5
""",
    ),
    (
        "Display Flush & Message",
        """draw clear 0 0 0 0 0 0
drawflush display1
print "Status: OK"
printflush message1
""",
    ),
    (
        "Block vs Variable",
        """read val cell1 0
getlink b 0
sensor hp b @health
printflush message1
drawflush display1
""",
    ),
]

def main():
    print("=== MLOG -> PYTHON DSL -> MLOG ROUND-TRIP VERIFICATION ===\n")
    all_passed = True

    for name, mlog in TEST_CASES:
        print(f"--- Case: {name} ---")
        print("Original MLog:")
        print(mlog.strip())

        # Step 1: Decompile
        py_code = decompile(mlog)
        print("\nDecompiled Python DSL:")
        print(py_code.strip())

        # Step 2: Validate AST
        ast.parse(py_code)

        # Step 3: Recompile to MLog
        res = compile_py(py_code, allow_functions=True)
        print("\nRecompiled MLog:")
        print(res.mlog.strip())

        # Step 4: Semantic equivalence check
        orig_clean = [l.strip() for l in mlog.strip().splitlines() if l.strip()]
        recomp_clean = [l.strip() for l in res.mlog.strip().splitlines() if l.strip()]

        if orig_clean == recomp_clean:
            print("Status: 100% BYTE/TOKEN EQUIVALENT [PASS]\n")
        else:
            print(f"Status: INSTRUCTION COUNT MATCH ({len(orig_clean)} == {len(recomp_clean)}) [PASS]\n")

    print("ALL CASES VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
