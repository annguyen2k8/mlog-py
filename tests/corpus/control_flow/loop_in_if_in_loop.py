i = 0
res = 0
while i < 10:
    if i % 2 == 0:
        k = 0
        while k < 3:
            res = res + (i * k)
            k = k + 1
    else:
        res = res + i
    i = i + 1
