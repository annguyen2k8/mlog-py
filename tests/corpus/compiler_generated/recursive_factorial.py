def fact(n):
    if n <= 1:
        return 1
    sub = n - 1
    prev = fact(sub)
    return n * prev

result = fact(5)
