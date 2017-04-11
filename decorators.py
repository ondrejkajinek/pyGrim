# coding: utf8

from functools import wraps


def method(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    wrapper._exposed = True
    return wrapper
