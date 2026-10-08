# Decompiled from reactor_safety.mlog
# Verified via ast.parse and semantic argument recovery
sensor(heat, "reactor1", "@heat")
if heat > 0.5:
    control(enabled, "reactor1", 0, 0, 0, 0)
else:
    control(enabled, "reactor1", 1, 0, 0, 0)
wait(0.5)
