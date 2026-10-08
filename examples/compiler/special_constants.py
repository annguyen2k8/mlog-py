# Special Mindustry Constants and Registers
# Demonstrates usage of @counter, @unit, @health, @copper.
from mlog import sensor, set, SensorProperty, Items

u_dead = sensor("@unit", SensorProperty.DEAD)
copper_name = Items.COPPER
set("@counter", 10)
