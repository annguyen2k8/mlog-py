"""Example demonstrating compile-time constant folding in mlog-py.

Pure constant expressions are evaluated directly by the compiler:
- Arithmetic: (10 + 15) * (2 * 3) -> set total 150
- Bitwise: (1 << 4) | (1 << 1) -> set flags 18
- Comparisons & Booleans: (10 > 5) and (not False) -> set is_valid true
- String concatenation: "Reactor " + "Monitor" -> set title "Reactor Monitor"
- Array memory sizing: Array("cell1", size=2 * 8) -> allocates 16 slots
- Array static indexing: buffer[1 + 2] = total -> write 150 cell1 3
"""

from mlog import Array, print, printflush

# 1. Compile-time arithmetic expressions
total = (10 + 15) * (2 * 3)

# 2. Compile-time bitwise operations
flags = (1 << 4) | (1 << 1)

# 3. Compile-time comparisons and booleans
is_valid = (10 > 5) and (not False)

# 4. String concatenation
title = "Reactor " + "Monitor"

# 5. Array declaration with folded constant size (16 slots)
buffer = Array("cell1", size=2 * 8)

# 6. Static array indexing with folded constant offset (slot 3)
buffer[1 + 2] = total

# 7. Output results
print(title)
print("\nTotal: ")
print(total)
print("\nFlags: ")
print(flags)
printflush("message1")
