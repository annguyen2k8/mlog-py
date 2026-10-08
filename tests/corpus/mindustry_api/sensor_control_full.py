from mlog import getlink, sensor, control

link_count = 4
idx = 0
while idx < link_count:
    block = getlink(idx)
    hp = sensor(block, "@health")
    max_hp = sensor(block, "@maxHealth")
    if hp < max_hp:
        control("enabled", block, 0)
    else:
        control("enabled", block, 1)
    idx = idx + 1
