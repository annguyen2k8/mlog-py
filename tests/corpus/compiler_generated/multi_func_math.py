def square(x):
    return x * x

def clamp(val, low, high):
    if val < low:
        return low
    elif val > high:
        return high
    return val

v1 = square(7)
v2 = clamp(v1, 10, 40)
