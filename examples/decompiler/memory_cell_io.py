# Decompiled from memory_cell_io.mlog
# Verified via ast.parse and semantic argument recovery
from mlog import read, write

val = read("cell1", 0)
nxt = val + 10
write(nxt, "cell1", 1)
