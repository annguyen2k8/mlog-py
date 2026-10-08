# Memory Cell Access
# Demonstrates reading and writing to named memory cell blocks.
from mlog import read, write

val = read("cell1", 0)
nxt = val + 10
write(nxt, "cell1", 1)
