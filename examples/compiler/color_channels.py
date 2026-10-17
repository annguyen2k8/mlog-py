# Color Channel Unpacking
# Demonstrates packing RGBA channels into one number and unpacking them back with
# tuple unpacking: `r, g, b, a = unpackcolor(color)`.
# Both unpackcolor forms lower to the same single Mindustry `unpackcolor r g b a value`
# instruction, and the unpacked targets must be exactly 4 distinct variables.
from mlog import packcolor, print, printflush, unpackcolor

packed = packcolor(0.25, 0.5, 0.75, 1.0)
r, g, b, a = unpackcolor(packed)

print("RGBA sum: ")
print(r + g + b + a)
printflush("message1")