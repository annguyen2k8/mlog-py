# Decompiled from block_vs_variable.mlog
# Verified via ast.parse and semantic argument recovery
from mlog import drawflush, getlink, printflush, raw, read, sensor

val = read("cell1", 0)
b = getlink(0)
hp = sensor(b, raw("@health"))
printflush("message1")
drawflush("display1")
