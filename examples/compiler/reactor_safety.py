# Sensor & Reactor Control
# Demonstrates reading sensor properties and issuing control commands.
from mlog import sensor, control, wait, SensorProperty, ControlProperty

heat = sensor("reactor1", SensorProperty.HEAT)
if heat > 0.5:
    control(ControlProperty.ENABLED, "reactor1", 0)
else:
    control(ControlProperty.ENABLED, "reactor1", 1)
wait(0.5)
