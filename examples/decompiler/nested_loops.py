# Decompiled from nested_loops.mlog
# Verified via ast.parse and semantic argument recovery
r = 0
while True:
    if r < 3:
        c = 0
        while True:
            if c < 3:
                if r == c:
                    print("Diag: ")
                print(r)
                c = c + 1
        r = r + 1
printflush("message1")
