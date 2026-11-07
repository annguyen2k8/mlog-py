# Decompiled from special_constants.mlog
# Verified via ast.parse and semantic argument recovery
from mlog import raw, sensor, set

u = sensor(raw("@unit"), raw("@dead"))
hp = sensor("core1", raw("@health"))
set(raw("@counter"), 10)
