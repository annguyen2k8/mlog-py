# Decompiled from block_vs_variable.mlog
# Verified via ast.parse and semantic argument recovery
from mlog import drawflush, getlink, printflush, read, sensor

val = read("cell1", 0)
b = getlink(0)
hp = sensor(b, '@health')
printflush("message1")
drawflush("display1")
