# coding: utf8

import re

from logging import getLogger
from urllib import quote_plus

log = getLogger("pygrim.components.route")


class RouteGroup(list):
    def __init__(self, pattern, *args, **kwargs):
        self.pattern = pattern
        super(RouteGroup, self).__init__(*args, **kwargs)


class Route(object):

    REGEXP_TYPE = type(re.compile(r""))

    TRAILING_SLASH_REGEXP = re.compile("/\??$")
    URL_PARAM_REGEXP = re.compile("\(\?P<([^>]+)>[^)]+\)")

    def __init__(self, methods, pattern, handle_name, name=None):
        # temporary
        # pyGrim will assign requested method on its postfork event
        self._handle = None
        self._handle_name = handle_name
        self._is_regex = type(pattern) == self.REGEXP_TYPE
        self._methods = tuple(map(
            lambda x: x.upper(),
            (
                (methods,)
                if isinstance(methods, basestring)
                else tuple(methods)
            )
        ))
        self._name = name
        self._pattern = self._strip_trailing_slash(pattern)

    def assign_method(self, method):
        self._handle = method

    def dispatch(self, request, response):
        self._handle(
            request=request,
            response=response,
            **request.pop_route_params()
        )

    def get_handle_name(self):
        return self._handle_name

    def get_name(self):
        return self._name

    def get_pattern(self):
        patt = (
            self._pattern.pattern
            if self._is_regex
            else self._pattern
        )
        patt = patt.strip("/")
        return patt

    def matches(self, request):
        return (
            self._supports_http_method(request.get_method()) and
            self._uri_matches(request)
        )

    def requires_session(self):
        return self._handle._session

    def set_pattern(self, pattern):
        self._pattern = pattern

    def url_for(self, params):
        if self._is_regex:
            readable, param_names = self._pattern_to_readable()
            query_params = {
                key: params[key]
                for key
                in params.iterkeys()
                if key not in param_names
            }
            url = readable % params
        else:
            url = self._pattern
            query_params = params

        if query_params:
            url += "?%s" % "&".join(
                "%s=%s" % tuple(map(quote_plus, map(str, (key, value))))
                for key, value
                in query_params.iteritems()
            )

        log.debug("Route constructed url: %r for params: %r" % (url, params))
        return "/%s" % url.lstrip("/")

    def _pattern_to_readable(self):
        param_names = self.URL_PARAM_REGEXP.findall(self._pattern.pattern)
        readable = self.URL_PARAM_REGEXP.sub(r"%(\1)s", self._pattern.pattern)
        readable = readable.rstrip("$")
        return readable, param_names

    def _strip_trailing_slash(self, pattern):
        if self._is_regex:
            return re.compile(
                self.TRAILING_SLASH_REGEXP.sub("", pattern.pattern)
            )
        else:
            return pattern.rstrip("/")

    def _supports_http_method(self, method):
        return method in self._methods

    def _uri_matches(self, request):
        uri = request.get_request_uri() or "/"
        log.debug(
            "matching %r with  %r",
            self._pattern.pattern if self._is_regex else self._pattern, uri
        )
        if self._is_regex:
            matches = self._pattern.match(uri)
            match = matches is not None
            if match:
                request.set_route_params(matches.groupdict())
        else:
            match = self._pattern == uri
            if match:
                request.set_route_params({})

        return match
