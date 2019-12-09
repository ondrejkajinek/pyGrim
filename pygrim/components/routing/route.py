# coding: utf8

# std
import logging
import re
import string
import urllib

# local
from ..utils import (
    ensure_string, ensure_tuple,
    fix_trailing_slash, is_regex, remove_trailing_slash
)

log = logging.getLogger("pygrim.components.route")


class RouteObject(object):

    def __init__(self, pattern, *args, **kwargs):
        super(RouteObject, self).__init__(*args, **kwargs)
        self.__pattern = None
        self.pattern = pattern

    @property
    def _raw_pattern(self):
        return self.__pattern

    @property
    def pattern(self):
        return (
            self.__pattern.pattern
            if is_regex(self.__pattern)
            else self.__pattern
        )

    @pattern.setter
    def pattern(self, pattern):
        self._set_pattern(pattern)

    def is_regex(self):
        return is_regex(self.__pattern)

    def _set_pattern(self, pattern):
        self.__pattern = pattern


class RouteGroup(RouteObject, list):
    def __init__(self, pattern, *args, **kwargs):
        super(RouteGroup, self).__init__(pattern, *args, **kwargs)

    def _set_pattern(self, pattern):
        super(RouteGroup, self)._set_pattern(remove_trailing_slash(pattern))


class Route(RouteObject):

    URL_FORMAT_REGEXP = re.compile(r"%\(([^)]+)\)s")
    URL_OPTIONAL_REGEXP = re.compile(r"\(([^)]*?)(%\(([^)]+)\)s)([^)]*?)\)\?")
    URL_PARAM_REGEXP = re.compile(r"\(\?P<([^>]+)>[^)]+\)")

    def __init__(self, methods, pattern, handle_name, name=None):
        self._readable_pattern = ""
        self._required_params = set()
        self._optional_params = {}
        super(Route, self).__init__(pattern)
        # temporary
        # pyGrim will assign requested method on its postfork event
        self._handle = None
        self._handle_name = handle_name
        self._methods = tuple(
            string.upper(method)
            for method
            in ensure_tuple(methods)
        )
        self._name = name

    def __repr__(self):
        return "%s(%r,%r,%r,%r,%r)" % (
            type(self), self._methods,
            self.pattern,
            self._handle_name, self._handle, self._name
        )

    def assign_method(self, method):
        self._handle = method

    def dispatch(self, context):
        self._handle(
            context=context,
            **context.pop_route_params()
        )

    def get_handle_name(self):
        return self._handle_name

    def get_name(self):
        return self._name

    def matches(self, context):
        return (
            self._supports_http_method(context.get_request_method()) and
            self._uri_matches(context)
        )

    def requires_session(self):
        return getattr(self._handle, "_session", False)

    def url_for(self, params):
        if self.is_regex():
            for name in self._optional_params:
                if params.get(name):
                    params[name] = self._optional_params[name] % params[name]
                else:
                    params[name] = ""

            query_params = {
                key: params[key]
                for key
                in params.iterkeys()
                if key not in (
                    self._required_params.union(self._optional_params.iterkeys())
                )
            }
            url = self._readable_pattern % params
        else:
            url = self.pattern
            query_params = params

        if query_params:
            url += "?" + urllib.urlencode([
                (ensure_string(key), ensure_string(value))
                for key, value
                in query_params.iteritems()
            ])

        log.debug("Route constructed url: %r for params: %r", url, params)
        return "/%s" % url.strip("/")

    def _pattern_to_readable(self):
        if self.is_regex():
            param_names = self.URL_PARAM_REGEXP.findall(self.pattern)
            readable = self.URL_PARAM_REGEXP.sub(r"%(\1)s", self.pattern)
            optional_names = {
                optional[2]: "%s%%s%s" % (optional[0], optional[3])
                for optional
                in self.URL_OPTIONAL_REGEXP.findall(readable)
            }

            readable = self.URL_OPTIONAL_REGEXP.sub(r"\2", readable)
            readable = remove_trailing_slash(readable).lstrip("^")
            readable = readable.replace(r"\.", ".")
            mandatory_names = set(param_names) - set(optional_names)
            if len(mandatory_names) + len(optional_names) < len(param_names):
                raise RuntimeError(
                    "Some keys are duplicate in route %r" % self.pattern
                )
        else:
            readable = self.pattern
            mandatory_names = set()
            optional_names = set()

        return readable, mandatory_names, optional_names

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
        if self.is_regex():
            matches = self._raw_pattern.match(uri)
            match = matches is not None
            route_params = matches.groupdict() if matches else {}
        else:
            match = self.pattern == uri
            route_params = {}

        if match:
            context.set_route_params(route_params)

        return match
