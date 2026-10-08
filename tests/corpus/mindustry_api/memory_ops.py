from mlog import read, write

i = 0
while i < 16:
    val = read("cell1", i)
    val = val * 2
    write(val, "cell2", i)
    i = i + 1
