# coding: utf8

from __future__ import print_function
from functools import wraps
try:
    from uwsgi import log as uwsgi_log
except ImportError:
    uwsgi_log = print

from logging import getLogger
log = getLogger("pygrim.decorators")


class BaseDecorator(object):

    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs

    def __call__(self, func):
        return func


class method(BaseDecorator):
    """
    Exposes method to server so that it can be used for route handling.
    Every decorator that is supposed to expose methods has to be
    properly derived from this class.
    """

    def __call__(self, func):
        func._session = bool(self._kwargs.get("session"))
        func._dispatch_name = self._kwargs.pop("dispatch_name", func.__name__)
        self._expose(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return super(method, self).__call__(wrapper)

    def _expose(self, func):
        if func._dispatch_name.startswith("_"):
            uwsgi_log(
                "pygrim WARNING: Internal method %r will not be exposed!" % (
                    func.__name__
                )
            )
        else:
            func._exposed = True


class error_handler(method):
    """
    Marks method as an error handler.
    Such method is used when error occurs during request handling.
    Also exposes method, see method decorator.
    """

    def __init__(self, *args, **kwargs):
        super(error_handler, self).__init__(**kwargs)
        for one in args:
            if not issubclass(one, BaseException):
                raise RuntimeError(
                    "%s must be subclass of Basexception" % (one,)
                )
        self.err_classes = args
    # enddef

    def __call__(self, func):
        func._custom_error = self.err_classes
        return super(error_handler, self).__call__(func)


class error_method(method):
    """
    Marks method as an error handler.
    Such method is used when error occurs during request handling.
    Also exposes method, see method decorator.
    """

    def __call__(self, func):
        func._error = True
        return super(error_method, self).__call__(func)


class not_found_method(method):
    """
    Marks method as not-found handler.
    Such method is called when no route matches requested url.
    Also exposes method, see method decorator.
    """

    def __init__(self, *args, **kwargs):
        super(not_found_method, self).__init__(**kwargs)
        self._not_found_prefixes = args or ("",)

    def __call__(self, func):
        func._not_found = self._not_found_prefixes
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
        super(uses_data, self).__init__()

    def __call__(self, func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            server = args[0]
            method = server._methods[self._method]
            context = kwargs.get("context")
            method_returned = method(context) or {}
            context.view_data.update(method_returned.get("data", {}))
            res = func(*args, **kwargs)
            return res

        return super(uses_data, self).__call__(wrapper)
