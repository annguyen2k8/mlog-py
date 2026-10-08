def add(a, b):
    return a + b

def multiply(a, b):
    res = 0
    k = 0
    while k < b:
        res = res + a
        k = k + 1
    return res

def compute_stat(x, y, z):
    s1 = add(x, y)
    s2 = multiply(s1, z)
    if s2 > 1000:
        return s2 // 2
    return s2

i = 0
acc = 0
while i < 8:
    tmp = compute_stat(i, i + 1, 3)
    acc = acc + tmp
    i = i + 1
