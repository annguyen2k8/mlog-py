# Graphics Drawing Pipeline
# Demonstrates drawing primitives and flushing to a named display.
from mlog import draw, drawflush, DrawType

draw(DrawType.CLEAR, 0, 0, 0)
draw(DrawType.COLOR, 255, 128, 0, 255)
draw(DrawType.LINE, 10, 10, 80, 80)
draw(DrawType.RECT, 20, 20, 40, 40)
drawflush("display1")
