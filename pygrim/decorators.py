# coding: utf8

from functools import wraps
from uwsgi import log as uwsgi_log


class BaseDecorator(object):

    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs

    def _expose(self, func):
        if func.__name__.startswith("_"):
            uwsgi_log(
                "pygrim.decorators: Exposing internal method %s" % (
                    func.__name__
                )
            )

        func._exposed = True


class method(BaseDecorator):

    def __call__(self, func):
        self._expose(func)
        func._session = bool(self._kwargs.get("session"))

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper


class error_method(method):

    def __call__(self, func):
        func._error = True
        return super(error_method, self).__call__(func)


class not_found_method(method):

    def __call__(self, func):
        func._not_found = True
        return super(not_found_method, self).__call__(func)
