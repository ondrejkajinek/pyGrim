# coding: utf8

from functools import wraps
from locale import LC_ALL, getlocale, setlocale

from logging import getLogger
log = getLogger(__name__)


def c_locale(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        locale = getlocale()
        setlocale(LC_ALL, "C")
        try:
            res = func(*args, **kwargs)
        except:
            setlocale(LC_ALL, locale)
            raise
        else:
            setlocale(LC_ALL, locale)
            return res

    return wrapper
