from mlog import ubind, ucontrol, uradar

ubind("@flare")
ucontrol("move", 100, 200, 0, 0, 0)
ucontrol("approach", 100, 200, 5, 0, 0)
ucontrol("boost", 1, 0, 0, 0, 0)
target = uradar("enemy", "any", "any", "distance", 0, 1)
ucontrol("target", 150, 250, 1, 0, 0)
ucontrol("itemDrop", "core1", 10, 0, 0, 0)
