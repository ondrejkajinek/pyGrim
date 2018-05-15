# coding: utf8

# std
from logging import getLogger
from re import compile as re_compile
from urllib import quote_plus

# local
from ..utils import (
    ensure_string, fix_trailing_slash, get_method_name, is_regex,
    remove_trailing_slash
)
from ...http.methods import GET, HEAD, METHODS

log = getLogger("pygrim.components.routing.route")


class RouteObject(object):

    def __init__(self, pattern, *args, **kwargs):
        super(RouteObject, self).__init__(*args, **kwargs)
        self.set_pattern(pattern)

    def get_pattern(self):
        return (
            self._pattern.pattern
            if self.is_regular()
            else self._pattern
        )

    def is_regular(self):
        return is_regex(self._pattern)

    def set_pattern(self, pattern):
        self._pattern = fix_trailing_slash(pattern)


class RouteGroup(RouteObject):

    def __add__(self, other):
        if not isinstance(other, RouteObject):
            raise NotImplemented()

        if isinstance(other, RouteGroup):
            result = RouteGroup(self._concat_pattern(other))
        else:
            result = Route(
                other._methods,
                self._concat_pattern(other),
                other._handle,
                other._name
            )

        return result

    def set_pattern(self, pattern):
        self._pattern = remove_trailing_slash(pattern)

    def _concat_pattern(self, other):
        full_pattern = "/".join((
            remove_trailing_slash(self.get_pattern()),
            other.get_pattern().lstrip("/")
        ))
        if any(i.is_regular() for i in (self, other)):
            full_pattern = re_compile(full_pattern)

        return full_pattern


class Route(RouteObject):

    URL_FORMAT_REGEXP = re_compile("%\(([^)]+)\)s")
    URL_OPTIONAL_REGEXP = re_compile("([^%])\((/?)(.*?)\)\?")
    URL_PARAM_REGEXP = re_compile("\(\?P<([^>]+)>[^)]+\)")

    def __init__(self, methods, pattern, handle, name=None):
        if pattern is None:
            pattern = "/%s" % handle.__name__

        if name is None:
            name = get_method_name(handle)

        # All routes supporting GET also support HEAD
        if GET in methods and HEAD not in methods:
            methods += (HEAD,)

        super(Route, self).__init__(pattern)
        self._handle = handle
        self._methods = tuple(
            method for method in methods if method in METHODS
        )
        self._name = name

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
            self.URL_PARAM_REGEXP.sub("", self.get_pattern()).count("/")
            if self.is_regular()
            else self.get_pattern().count("/")
        )

    def url_for(self, params):
        if self.is_regular():
            readable, param_names, optional_names = self._pattern_to_readable()
            for name in optional_names:
                params.setdefault(name, "")

            query_params = {
                key: params[key]
                for key
                in params.iterkeys()
                if key not in (param_names.union(optional_names))
            }
            url = readable % params
        else:
            url = self._pattern
            query_params = params

        if query_params:
            url += "?%s" % "&".join(
                "%s=%s" % tuple(
                    map(quote_plus, map(ensure_string, (key, value)))
                )
                for key, value
                in query_params.iteritems()
            )

        log.debug("Route constructed url: %r for params: %r" % (url, params))
        return "/%s" % url.strip("/")

    def _asdict(self):
        return {
            "handle_name": get_method_name(self._handle),
            "methods": self._methods,
            "name": self.get_name(),
            "pattern": self.get_pattern(),
            "regular": self.is_regular()
        }

    def _pattern_to_readable(self):
        param_names = self.URL_PARAM_REGEXP.findall(self._pattern.pattern)
        readable = self.URL_PARAM_REGEXP.sub(r"%(\1)s", self._pattern.pattern)
        optional_names = set()
        for optional in self.URL_OPTIONAL_REGEXP.findall(readable):
            optional_names.update(self.URL_FORMAT_REGEXP.findall(optional[2]))

        readable = self.URL_OPTIONAL_REGEXP.sub(r"\1\2\3", readable)
        readable = remove_trailing_slash(readable).lstrip("^")
        readable = readable.replace("\.", ".")
        mandatory_names = set(param_names) - set(optional_names)
        if len(mandatory_names) + len(optional_names) < len(param_names):
            raise RuntimeError(
                "Some keys are duplicate in route %r" % self._pattern.pattern
            )

        return readable, mandatory_names, optional_names

    def _supports_http_method(self, method):
        return method in self._methods

    def _uri_matches(self, context):
        uri = context.get_request_uri()
        log.debug("matching %r with %r", self.get_pattern(), uri)
        if self.is_regular():
            matches = self._pattern.match(uri)
            match = matches is not None
            context.set_route_params(matches.groupdict() if match else {})
        else:
            match = self._pattern == uri
            context.set_route_params()

        return match


class NoRoute(Route):

    def __init__(self):
        self._handle = None
        self._methods = ()
        self._name = "<no route>"

    def __nonzero__(self):
        return False

    def get_handle_name(self):
        return self._name
