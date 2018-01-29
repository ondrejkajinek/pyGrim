# coding: utf8

from ..utils import (
    ensure_string, fix_trailing_slash, is_regex, remove_trailing_slash
)
from logging import getLogger
from re import compile as re_compile
from string import upper as string_upper
from urllib import quote_plus

log = getLogger("pygrim.components.route")


class RouteObject(object):

    def __init__(self, pattern, *args, **kwargs):
        super(RouteObject, self).__init__(*args, **kwargs)
        self._pattern = fix_trailing_slash(pattern)

    def get_pattern(self):
        return (
            self._pattern.pattern
            if self.is_regex()
            else self._pattern
        )

    def is_regex(self):
        return is_regex(self._pattern)


class RouteGroup(RouteObject, list):
    def __init__(self, pattern, *args, **kwargs):
        super(RouteGroup, self).__init__(pattern, *args, **kwargs)


class Route(RouteObject):

    URL_FORMAT_REGEXP = re_compile("%\(([^)]+)\)s")
    URL_OPTIONAL_REGEXP = re_compile("([^%])\((/?)(.*?)\)\?")
    URL_PARAM_REGEXP = re_compile("\(\?P<([^>]+)>[^)]+\)")

    def __init__(self, methods, pattern, handle_name, name=None):
        super(Route, self).__init__(pattern)
        # temporary
        # pyGrim will assign requested method on its postfork event
        self._handle = None
        self._handle_name = handle_name
        self._methods = tuple(map(
            string_upper,
            (
                (methods,)
                if isinstance(methods, basestring)
                else tuple(methods)
            )
        ))
        self._name = name

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

    def set_pattern(self, pattern):
        self._pattern = fix_trailing_slash(pattern)

    def url_for(self, params):
        if self.is_regex():
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

    def _pattern_to_readable(self):
        param_names = self.URL_PARAM_REGEXP.findall(self._pattern.pattern)
        readable = self.URL_PARAM_REGEXP.sub(r"%(\1)s", self._pattern.pattern)
        optional_names = set()
        for optional in self.URL_OPTIONAL_REGEXP.findall(readable):
            optional_names.update(
                set(self.URL_FORMAT_REGEXP.findall(optional[2]))
            )

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
        if self.is_regex():
            matches = self._pattern.match(uri)
            match = matches is not None
            route_params = matches.groupdict() if matches else {}
        else:
            match = self._pattern == uri
            route_params = {}

        if match:
            context.set_route_params(route_params)

        return match
