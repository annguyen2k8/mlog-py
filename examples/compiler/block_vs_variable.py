# Named Hardware Links vs Program Variables
# Demonstrates the distinction between static device names and dynamic variables.
from mlog import read, write, getlink, sensor

# 1. Named hardware link (quoted string literal)
val = read("cell1", 0)
nxt = val + 1
write(nxt, "cell1", 0)

# 2. Dynamic block reference obtained via getlink (unquoted variable identifier)
b = getlink(0)
hp = sensor(b, "@health")
