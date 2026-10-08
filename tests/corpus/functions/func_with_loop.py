def sum_to_n(n):
    total = 0
    k = 1
    while k <= n:
        total = total + k
        k = k + 1
    return total

s = sum_to_n(10)
