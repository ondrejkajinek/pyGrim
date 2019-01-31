# coding: utf8

from __future__ import print_function
from functools import wraps
from components.utils import json2 as json
from copy import deepcopy

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

    def pre_call(self, fun, args, kwargs):
        pass

    def post_call(self, fun, args, kwargs, ret):
        return ret

    def prepare_func(self, fun):
        pass

    def __call__(self, func):
        self.prepare_func(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            args = list(args)
            self.pre_call(func, args, kwargs)
            ret = func(*args, **kwargs)
            return self.post_call(func, args, kwargs, ret)

        return wrapper

    def _expose(self, func):
        if func._dispatch_name.startswith("_"):
            uwsgi_log(
                "pygrim WARNING: Internal method %r will not be exposed!" % (
                    func.__name__
                )
            )
        else:
            log.debug("Exposing %r", func)
            func._exposed = True


class method(BaseDecorator):
    """
    Exposes method to server so that it can be used for route handling.
    Every decorator that is supposed to expose methods has to be
    properly derived from this class.
    """
    def __init__(self, *args, **kwargs):
        self._session = bool(kwargs.pop("session", False))
        self._dispatch_name = kwargs.pop("dispatch_name", None)
        super(method, self).__init__(*args, **kwargs)

    def prepare_func(self, func):
        func._session = self._session
        func._dispatch_name = self._dispatch_name or func.__name__
        self._expose(func)

        super(method, self).prepare_func(func)


class error_handler(method):
    """
    Marks method as an error handler for specific exception.
    Can only catch exceptions derived from BaseException.
    Such method is used when error occurs during request handling.
    Also exposes method, see method decorator.
    """

    def __init__(self, *args, **kwargs):
        self._error_status = kwargs.pop("status", 500)
        self._save_session = kwargs.pop("save_session", False)
        super(error_handler, self).__init__(**kwargs)
        for one in args:
            if not issubclass(one, BaseException):
                raise RuntimeError(
                    "%s must be subclass of BaseException" % (one,)
                )
        self.err_classes = args

    def pre_call(self, fun, args, kwargs):
        kwargs.get("context").set_response_status(self._error_status)
        super(error_handler, self).pre_call(fun, args, kwargs)

    def prepare_func(self, func):
        func._custom_error = self.err_classes
        func._save_session = self._save_session
        super(error_handler, self).prepare_func(func)


class error_method(method):
    """
    Marks method as an error handler.
    Such method is used when error occurs during request handling.
    Also exposes method, see method decorator.
    """

    def pre_call(self, fun, args, kwargs):
        kwargs.get("context").set_response_status(500)
        return super(error_method, self).pre_call(fun, args, kwargs)

    def prepare_func(self, func):
        func._error = True
        super(error_method, self).prepare_func(func)


class not_found_method(method):
    """
    Marks method as not-found handler.
    Such method is called when no route matches requested url.
    Also exposes method, see method decorator.
    """

    def __init__(self, *args, **kwargs):
        super(not_found_method, self).__init__(**kwargs)
        self._not_found_prefixes = []
        for one in (args or (("", 0),)):
            if isinstance(one, basestring):
                one = (one, 0)
            self._not_found_prefixes.append(tuple(one))

    def pre_call(self, fun, args, kwargs):
        kwargs.get("context").set_response_status(404)
        return super(not_found_method, self).pre_call(fun, args, kwargs)

    def prepare_func(self, func):
        func._not_found = self._not_found_prefixes
        super(not_found_method, self).prepare_func(func)


class json_method(method):
    """
    Takes result of decorated method, puts it to context, sets response type to
    json and displays it.
    """

    def post_call(self, fun, args, kwargs, res):
        context = kwargs.get("context")
        if context:
            json_res = json.dumps(res)
            context.set_response_body(json_res)
            context.set_response_content_type('application/json')

        return super(json_method, self).post_call(fun, args, kwargs, res)


class template_display(BaseDecorator):
    """
    Takes result of decorated method (expects {"data": view_data}),
    puts it to context, sets specified template and displays it.
    """

    def __init__(self, template, *args, **kwargs):
        self._template = template
        super(template_display, self).__init__(*args, **kwargs)

    def post_call(self, fun, args, kwargs, res):
        context = kwargs.get("context")
        context.view_data.update(res.get("data") or {})
        context.template = res.get("_template", self._template)
        args[0].display(context)
        return super(template_display, self).post_call(fun, args, kwargs, res)


class template_method(template_display, method):
    """
    Combines the funcionality of template_display and method decorators
    """

    def __init__(self, *args, **kwargs):
        if "template" in kwargs:
            template = kwargs.pop("template")
        elif args:
            template = args[0]
            args = args[1:]
        else:
            raise RuntimeError(
                "Error registering template_method withot template given"
            )
        # endif
        super(template_method, self).__init__(template, *args, **kwargs)


class uses_data(BaseDecorator):

    def __init__(self, method):
        self._method = method
        super(uses_data, self).__init__()

    def pre_call(self, fun, args, kwargs):
        server = args[0]
        method = server._methods[self._method]
        context = kwargs.get("context")
        method_returned = method(context) or {}
        context.view_data.update(method_returned.get("data", {}))
        return super(uses_data, self).pre_call(fun, args, kwargs)


class canonical_url(BaseDecorator):
    """
    příklad
    @canonical_url(canonical={
        "id": ["detail","id"],
        "seo": "x",
        ...
    })
    def detail(..):
        ...
    """
    def __init__(self, *args, **kwargs):
        self.canonical_args = kwargs.get("canonical")

        super(canonical_url, self).__init__(*args, **kwargs)

    def pre_call(self, fun, args, kwargs):
        context = kwargs.get("context")
        if context and self.canonical_args is not None:
            context.canonical_args = deepcopy(self.canonical_args)
        return super(canonical_url, self).pre_call(fun, args, kwargs)

# eof
