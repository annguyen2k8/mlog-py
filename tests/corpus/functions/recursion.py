def fib(n):
    if n <= 1:
        return n
    n1 = n - 1
    f1 = fib(n1)
    n2 = n - 2
    f2 = fib(n2)
    return f1 + f2

res = fib(6)
