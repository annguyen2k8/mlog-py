# Nested Loops and Conditionals
# Demonstrates multi-level control flow structures.
from mlog import print, printflush

r = 0
while r < 3:
    c = 0
    while c < 3:
        if r == c:
            print("Diag: ")
            print(r)
        c = c + 1
    r = r + 1
printflush("message1")
