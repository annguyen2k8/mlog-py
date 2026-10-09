# Decompiled from display_graphics.mlog
# Verified via ast.parse and semantic argument recovery
from mlog import draw, drawflush

draw("clear", 0, 0, 0, 0, 0, 0)
draw("color", 255, 128, 0, 255, 0, 0)
draw("line", 10, 10, 80, 80, 0, 0)
draw("rect", 20, 20, 40, 40, 0, 0)
drawflush("display1")
