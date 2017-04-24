# coding: utf8

from functools import wraps
from uwsgi import log as uwsgi_log


def error_method(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    wrapper._error = True
    return _expose(wrapper)


def method(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return _expose(wrapper)


def not_found_method(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    wrapper._not_found = True
    return _expose(wrapper)


def _expose(func):
    if func.__name__.startswith("_"):
        uwsgi_log(
            "pygrim.decorators: Exposing internal method %s" % func.__name__
        )

    func._exposed = True
    return func
