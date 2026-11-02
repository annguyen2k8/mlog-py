# Graphics Drawing Pipeline
# Demonstrates drawing primitives and flushing to a named display.
from mlog import draw, drawflush

draw.clear(0, 0, 0)
draw.color(255, 128, 0, 255)
draw.line(10, 10, 80, 80)
draw.rect(20, 20, 40, 40)
drawflush("display1")
