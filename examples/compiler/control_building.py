# Building Control Example
# Demonstrates the five Mindustry v160.7 building control modes:
# enabled, shoot, shootp, config, and color.
from mlog import control, packcolor

# 1. Turn a block on or off
control.enabled("reactor1", 1)

# 2. Aim a turret at map coordinates and fire
control.shoot("turret1", 100, 200, 1)

# 3. Aim a turret at the currently bound unit and fire
control.shootp("turret1", "@unit", 1)

# 4. Configure a sorter to accept copper
control.config("sorter1", "@copper")

# 5. Set a light block to a color produced by packcolor
light_color = packcolor(1, 1, 1, 1)
control.color("light1", light_color)

# The legacy generic form remains fully supported:
control("enabled", "conveyor1", 1)
