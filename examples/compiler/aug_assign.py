"""Example: Augmented assignment operators on scalars and memory arrays."""

from mlog import Array

# 1. Scalar augmented assignment
total = 0
step = 5
total += step
total *= 2
total -= 3
total //= 2

# 2. Accumulating values in a loop
sum_sq = 0
for i in range(1, 5):
    sum_sq += i * i

# 3. Memory array element augmented assignment (single-offset evaluation)
int_buffer = Array("cell1", size=10, dtype=int)
float_buffer = Array("cell1", size=10, dtype=float)
flags = Array("cell1", size=10, dtype=bool)

# Direct element updates
int_buffer[0] = 100
int_buffer[0] += 25
int_buffer[0] //= 5

float_buffer[0] = 1.0
float_buffer[0] += 2.5
float_buffer[0] *= 1.5

# Dynamic indexing in loop
for i in range(len(int_buffer)):
    int_buffer[i] += 10
    flags[i] ^= True
