"""Demonstration of Decompiler SourceMap and Debug Mode.

Usage:
    python3 examples/decompiler/sourcemap_debug.py
"""

from src.decompiler import decompile, decompile_with_source_map

MLOG_PROGRAM = """sensor heat reactor1 @heat
jump 4 lessThanEq heat 0.5
control enabled reactor1 0 0 0 0
jump 5 always 0 0
control enabled reactor1 1 0 0 0
wait 0.5
"""

def main():
    print("=== 1. RAW MLOG PROGRAM ===")
    print(MLOG_PROGRAM)

    print("=== 2. DEBUG DECOMPILATION (WITH INLINE ADDRESS COMMENTS) ===")
    debug_code = decompile(MLOG_PROGRAM, debug=True)
    print(debug_code)

    print("\n=== 3. SOURCEMAP BIDIRECTIONAL LOOKUP ===")
    clean_code, sm = decompile_with_source_map(MLOG_PROGRAM)
    print("Clean decompiled code:")
    print(clean_code)

    print("\nLine mapping inspection:")
    for py_line in range(1, len(clean_code.splitlines()) + 1):
        addrs = sm.python_to_mlog(py_line)
        print(f"  Python line {py_line} -> MLog addresses: {addrs}")

    print("\nAddress mapping inspection:")
    for addr in range(6):
        py_line = sm.mlog_to_python(addr)
        print(f"  MLog address {addr} -> Python line: {py_line}")

    print("\n=== 4. SOURCEMAP JSON SERIALIZATION ===")
    print(sm.to_json(indent=2))

if __name__ == "__main__":
    main()
