# For Loop with Range Iterator
# Demonstrates for-loop compilation with range(start, stop, step),
# loop latch increment, and break / continue statements.
total = 0
for i in range(1, 10, 2):
    if i == 5:
        continue
    if i > 7:
        break
    total = total + i
