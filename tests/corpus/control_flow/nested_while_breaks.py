a = 0
outer = 0
while outer < 5:
    inner = 0
    while inner < 4:
        if inner == 2:
            inner = inner + 1
            continue
        if outer == 3:
            break
        a = a + (outer * 10) + inner
        inner = inner + 1
    outer = outer + 1
