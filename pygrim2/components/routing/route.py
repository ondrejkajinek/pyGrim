# std
from logging import getLogger
import re
from urllib.parse import quote_plus

# local
from ..utils import (
    fix_trailing_slash, get_method_name, is_regex, remove_trailing_slash,
    regex_to_readable
)
from ...http.methods import GET, HEAD, METHODS

log = getLogger("pygrim.components.routing.route")


class RouteObject(object):

    def __init__(self, pattern, *args, **kwargs):
        super(RouteObject, self).__init__(*args, **kwargs)
        self.__pattern = None
        self.pattern = pattern

    @property
    def pattern(self):
        return (
            self.__pattern.pattern
            if self.is_regular()
            else self.__pattern
        )

    @pattern.setter
    def pattern(self, pattern):
        self._set_pattern(pattern)

    @property
    def _raw_pattern(self):
        return self.__pattern

    def is_regular(self):
        return is_regex(self.__pattern)

    def _set_pattern(self, pattern):
        self.__pattern = fix_trailing_slash(pattern)


class RouteGroup(RouteObject):

    def __add__(self, other):
        if isinstance(other, RouteGroup):
            result = RouteGroup(self._concat_pattern(other))
        elif isinstance(other, Route):
            result = Route(
                other._methods,
                self._concat_pattern(other),
                other._handle,
                other._name
            )
        else:
            raise TypeError(
                "unsupported operand type(s) for +: 'RouteGroup' and '%s'" % (
                    type(other),
                )
            )

        return result

    def _concat_pattern(self, other):
        full_pattern = "/".join((
            remove_trailing_slash(self.pattern),
            other.pattern.lstrip("/")
        ))
        if any(i.is_regular() for i in (self, other)):
            full_pattern = re.compile(full_pattern)

        return full_pattern

    def _set_pattern(self, pattern):
        super()._set_pattern(remove_trailing_slash(pattern))


class Route(RouteObject):

    URL_PARAM_REGEXP = re.compile(r"\(\?P<([^>]+)>[^)]+\)")

    def __init__(self, methods, pattern, handle, name=None):
        if pattern is None:
            pattern = "/%s" % handle.__name__

        if name is None:
            name = get_method_name(handle)

        # All routes supporting GET also support HEAD
        if GET in methods and HEAD not in methods:
            methods += (HEAD,)

        self._readable_pattern = ""
        self._required_params = set()
        self._optional_params = {}

        super(Route, self).__init__(pattern)
        self._handle = handle
        self._methods = tuple(
            method for method in methods if method in METHODS
        )
        self._name = name

    def __eq__(self, other):
        return (
            self.pattern == other.pattern and
            set(self._methods).intersection(other._methods)
        )

    def __str__(self):
        return repr(self._asdict())

    def dispatch(self, context):
        self._handle(context=context, **context.get_route_params())

    def get_handle_name(self):
        return get_method_name(self._handle)

    def get_name(self):
        return self._name

    def matches(self, context):
        return (
            self._supports_http_method(context.get_request_method()) and
            self._uri_matches(context)
        )

    def specificity(self):
        return (
            self.URL_PARAM_REGEXP.sub("", self.pattern).count("/")
            if self.is_regular()
            else self.pattern.count("/")
        )

    def url_for(self, params):
        if self.is_regular():
            for name in self._optional_params:
                if params.get(name):
                    params[name] = self._optional_params[name] % params[name]
                else:
                    params[name] = ""

            query_params = {
                key: params[key]
                for key
                in params.keys()
                if key not in (
                    self._required_params.union(self._optional_params.keys())
                )
            }
            url = self._readable_pattern % params
        else:
            url = self.pattern
            query_params = params

        if query_params:
            url += "?%s" % "&".join(
                "{}={}".format(quote_plus(str(key)), quote_plus(str(value)))
                for key, value
                in query_params.items()
            )

        log.debug("Route constructed url: %r for params: %r", url, params)
        return "/%s" % url.strip("/")

    def _asdict(self):
        return {
            "handle_name": get_method_name(self._handle),
            "methods": self._methods,
            "name": self.get_name(),
            "pattern": self.pattern,
            "regular": self.is_regular()
        }

    def _pattern_to_readable(self):
        if self.is_regular():
            readable, required_names, optional_names = regex_to_readable(
                self.pattern
            )
        else:
            readable = self.pattern
            required_names = set()
            optional_names = set()

        return readable, required_names, optional_names

    def _set_pattern(self, pattern):
        super(Route, self)._set_pattern(fix_trailing_slash(pattern))
        readable, req_params, optional_params = self._pattern_to_readable()
        self._readable_pattern = readable
        self._required_params = req_params
        self._optional_params = optional_params

    def _supports_http_method(self, method):
        return method in self._methods

    def _uri_matches(self, context):
        uri = context.get_request_uri()
        log.debug("matching %r with %r", self.pattern, uri)
        if self.is_regular():
            matches = self._raw_pattern.match(uri)
            match = matches is not None
            context.set_route_params(matches.groupdict() if match else {})
        else:
            match = self.pattern == uri
            context.set_route_params()

        return match


class NoRoute(Route):

    def __init__(self):
        self._handle = None
        self._methods = ()
        self._name = "<no route>"

    def __bool__(self):
        return False

    def get_handle_name(self):
        return self._name
