# Loops with Break and Continue
# Demonstrates while loop execution with early exit and skips.
i = 0
total = 0
while i < 10:
    if i == 3:
        i = i + 1
        continue
    if i == 8:
        break
    total = total + i
    i = i + 1
