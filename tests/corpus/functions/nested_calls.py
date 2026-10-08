def double_val(x):
    return x * 2

def quad_val(x):
    d = double_val(x)
    return double_val(d)

ans = quad_val(3)
