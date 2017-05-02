# coding: utf8

from functools import wraps
from uwsgi import log as uwsgi_log
from logging import getLogger
log = getLogger(__name__)


class BaseDecorator(object):

    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs

    def _expose(self, func):
        if func.__name__.startswith("_"):
            uwsgi_log(
                "pygrim WARNING: Internal method %r will not be exposed!" % (
                    func.__name__
                )
            )
        else:
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


class template_method(object):

    def __init__(self, template):
        self._template = template

    def __call__(self, func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            res = func(*args, **kwargs)
            context = kwargs.get("context")
            context.view_data.update(res.get("data") or {})
            context.template = res.get("_template", self._template)
            args[0].display(context)

        return wrapper


class uses_data(object):

    def __init__(self, method):
        self._method = method

    def __call__(self, func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            server = args[0]
            method = server._methods[self._method]
            context = kwargs.get("context")
            context.view_data.update(method(context)['data'])
            res = func(*args, **kwargs)
            return res

        return wrapper
