from functools import update_wrapper, wraps
from locale import LC_ALL, getlocale, setlocale


def c_locale(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        locale = getlocale()
        setlocale(LC_ALL, "C")
        try:
            res = func(*args, **kwargs)
        except BaseException:
            setlocale(LC_ALL, locale)
            raise
        else:
            setlocale(LC_ALL, locale)
            return res

    return wrapper


class lazy_property:

    def __init__(self, fun):
        self.fun = fun
        update_wrapper(self, fun)

    def __get__(self, obj, cls=None):
        if obj is None:
            return self

        value = self.fun(obj)
        setattr(obj, self.fun.__name__, value)
        return value
