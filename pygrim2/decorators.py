# std
from functools import wraps
from logging import getLogger
from re import compile as re_compile

# non-std
try:
    from uwsgi import log as uwsgi_log
except ImportError:
    uwsgi_log = print

# local
from .components.routing import RouteNotFound
from .components.utils import ensure_tuple

log = getLogger("pygrim_start.decorators")


class BaseDecorator(object):

    def __init__(self, *args, **kwargs):
        super(BaseDecorator, self).__init__(*args, **kwargs)
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


class error_handler(BaseDecorator):
    """
    Marks method as an error handler, optionally for specific exception.
    Can only catch exceptions derived from BaseException.
    Such method is used when error occurs during request handling.
    """

    def __init__(
        self, errors=None, path=None, save_session=False, *args, **kwargs
    ):
        errors = ensure_tuple(errors or (BaseException,))
        self._error_status = kwargs.pop("status", 500)
        for one in errors:
            if not issubclass(one, BaseException):
                # TODO: more useful message
                raise RuntimeError(
                    "%s must be subclass of BaseException" % (one,)
                )

        super(error_handler, self).__init__(*args, **kwargs)
        self._error_classes = errors
        self._paths = ensure_tuple(path or ("",))
        self._save_session = save_session

    def pre_call(self, fun, args, kwargs):
        kwargs.get("context").set_response_status(self._error_status)
        return super(error_handler, self).pre_call(fun, args, kwargs)

    def prepare_func(self, func):
        func._errors = self._error_classes
        func._paths = self._paths
        func._save_session = self._save_session
        super(error_handler, self).prepare_func(func)


class force_content_length(BaseDecorator):
    """
    Forces method to send Content-Length response header even if server
    is configured not to do so (this enables optimization when sending
    view result)
    """

    def post_call(self, fun, args, kwargs, ret):
        context = kwargs["context"]
        context.disable_content_length = False
        return super().post_call(fun, args, kwargs, ret)


class json_method(BaseDecorator):
    """
    Sets view to json
    Puts result of decorated method to context.view_data.
    """

    def pre_call(self, fun, args, kwargs):
        context = kwargs.get("context")
        context.set_view("json")
        context.set_response_content_type("application/json")
        return super(json_method, self).pre_call(fun, args, kwargs)

    def post_call(self, fun, args, kwargs, res):
        context = kwargs.get("context")
        context.view_data.update(res or ())
        return super(json_method, self).post_call(fun, args, kwargs, res)


class not_found_handler(error_handler):
    """
    Marks method as not-found handler.
    Such method is called when no route matches requested url.
    """

    def __init__(self, path="", *args, **kwargs):
        kwargs["status"] = kwargs.get("status", 404)
        super(not_found_handler, self).__init__(
            errors=(RouteNotFound,), path=path, *args, **kwargs
        )


class route(BaseDecorator):
    """
    Marks method as request handler.
    Such method is called when request matching url and http method is called.
    """

    def __init__(self, methods, pattern=None, name=None, *args, **kwargs):
        self._route = {
            "methods": ensure_tuple(methods),
            "name": name,
            "pattern": pattern
        }
        super(route, self).__init__(*args, **kwargs)

    def prepare_func(self, func):
        if hasattr(func, "_route"):
            func._route.append(self._route)
        else:
            func._route = [self._route]


class regex_route(route):

    def __init__(self, methods, pattern=None, name=None, *args, **kwargs):
        if pattern is not None:
            pattern = re_compile(pattern)

        super(regex_route, self).__init__(
            methods, pattern, name, *args, **kwargs
        )


class template(BaseDecorator):
    """
    Sets specified template and optionally view.
    Puts result of decorated method to context.view_data.
    """

    def __init__(self, template_, view=None, *args, **kwargs):
        self._template = template_
        self._view = view
        super(template, self).__init__(*args, **kwargs)

    def pre_call(self, fun, args, kwargs):
        context = kwargs.get("context")
        context.template = self._template
        if self._view is not None:
            context.set_view(self._view)

        return super(template, self).pre_call(fun, args, kwargs)

    def post_call(self, fun, args, kwargs, res):
        context = kwargs.get("context")
        context.view_data.update(res or ())
        return super(template, self).post_call(fun, args, kwargs, res)


class uses_data(BaseDecorator):

    def __init__(self, method):
        self._method = method
        super(uses_data, self).__init__()

    def pre_call(self, fun, args, kwargs):
        controller = args[0]
        method = controller._methods[self._method]
        context = kwargs.get("context")
        method_returned = method(context) or {}
        context.view_data.update(method_returned.get("data", {}))
        return super(uses_data, self).pre_call(fun, args, kwargs)
