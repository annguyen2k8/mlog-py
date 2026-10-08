# Decompiled from branch_ladder.mlog
# Verified via ast.parse and semantic argument recovery
a = 15
if a > 20:
    res = 1
# [UNSTRUCTURED REGION]: Unstructured unconditional jump to address 6
jump('6', 'always', '0', '0')  # addr 3
if a > 10:
    res = 2
# [UNSTRUCTURED REGION]: Unstructured unconditional jump to address 7
jump('7', 'always', '0', '0')  # addr 6
res = 0
