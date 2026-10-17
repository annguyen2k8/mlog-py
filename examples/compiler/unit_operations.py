# Unit Operations Example
# Demonstrates canonical Mindustry Logic unit control APIs:
# - ubind: binding a specific unit type (e.g., @flare)
# - ulocate: locating cores, ore deposits, spawn points, or damaged structures
# - uradar: scanning for enemy units within sensor range
# - ucontrol: commanding unit movement, weapon targeting, and flags

from mlog import (
    ubind,
    ucontrol,
    uradar,
    ulocate,
    sensor,
)

# 1. Bind an available flying unit (@flare)
ubind("@flare")

# 2. Locate friendly core coordinates
# core_x, core_y, found_core, core_build = ulocate.building(group, enemy)
core_x, core_y, found_core, core_build = ulocate.building("core", False)

# 3. Locate nearest copper ore deposit
# ore_x, ore_y, found_ore = ulocate.ore(ore)
ore_x, ore_y, found_ore = ulocate.ore("@copper")

# 4. Search for closest enemy unit using radar
# target = uradar(target1, target2, target3, sort, sort_order)
enemy = uradar("enemy", "any", "any", "distance", 1)

# 5. Read bound unit health using sensor (target, property)
u_health = sensor("@unit", "@health")
u_dead = sensor("@unit", "@dead")

# 6. Combat and retreat decision logic
if enemy != 0:
    # Target enemy and approach attack distance
    e_x = sensor(enemy, "@x")
    e_y = sensor(enemy, "@y")
    ucontrol.approach(e_x, e_y, 8)
    ucontrol.target(e_x, e_y, 1)
    ucontrol.flag(1)
elif found_core:
    # Retreat to core when no enemy is detected
    ucontrol.approach(core_x, core_y, 12)
    ucontrol.target(0, 0, 0)
    ucontrol.flag(0)
else:
    # Idle fallback
    ucontrol.idle()
