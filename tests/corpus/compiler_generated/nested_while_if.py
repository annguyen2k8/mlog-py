i = 0
total = 0
while i < 10:
    j = 0
    while j < 5:
        if j == 3:
            break
        elif j == 1:
            j = j + 1
            continue
        total = total + (i * j)
        j = j + 1
    if total > 50:
        break
    i = i + 1
