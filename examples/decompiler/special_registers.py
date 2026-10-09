# Decompiled from special_registers.mlog
# Verified via ast.parse and semantic argument recovery
from mlog import sensor, set

u = sensor('@unit', '@dead')
hp = sensor("core1", '@health')
set("@counter", 10)
