# coding: utf8

from functools import wraps
from uwsgi import log as uwsgi_log
from logging import getLogger
log = getLogger(__name__)


class BaseDecorator(object):

    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs

    def __call__(self, func):
        return func

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


class template_display(BaseDecorator):
    """
    Takes result of decorated method (expects {"data": view_data}),
    puts it to context, sets specified template and displays it.
    """

    def __init__(self, template, *args, **kwargs):
        self._template = template
        super(template_display, self).__init__(*args, **kwargs)

    def __call__(self, func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            res = func(*args, **kwargs)
            context = kwargs.get("context")
            context.view_data.update(res.get("data") or {})
            context.template = res.get("_template", self._template)
            args[0].display(context)

        return super(template_display, self).__call__(wrapper)


class template_method(template_display, method):
    """
    Combines the funcionality of template_display and method decorators
    """

    def __init__(self, *args, **kwargs):
        args = list(args)
        template = kwargs.pop("template", args.pop(0))
        super(template_method, self).__init__(template, *args, **kwargs)

    def __call__(self, func):
        return super(template_method, self).__call__(func)


class uses_data(BaseDecorator):

    def __init__(self, method):
        self._method = method

    def __call__(self, func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            server = args[0]
            method = server._methods[self._method]
            context = kwargs.get("context")
            context.view_data.update(method(context)["data"])
            res = func(*args, **kwargs)
            return res

        return wrapper
