# Decompiled from reactor_safety.mlog
# Verified via ast.parse and semantic argument recovery
from mlog import control, raw, sensor, wait

heat = sensor("reactor1", raw("@heat"))
if heat > 0.5:
    control.enabled("reactor1", 0)
else:
    control.enabled("reactor1", 1)
wait(0.5)
