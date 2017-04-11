# coding: utf8

import re


class Route(object):

    REGEXP_TYPE = type(re.compile(r""))

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
        self._pattern = pattern

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
        return self._pattern

    def matches(self, request):
        return (
            self._supports_http_method(request.get_method()) and
            self._uri_matches(request)
        )

    def set_pattern(self, pattern):
        self._pattern = pattern

    def _supports_http_method(self, method):
        return method in self._methods

    def _uri_matches(self, request):
        if self._is_regex:
            matches = self._pattern.match(request.get_request_uri())
            match = matches is not None
            if match:
                request.set_route_params(matches.groupdict())
        else:
            match = self._pattern == request.get_request_uri()
            if match:
                request.set_route_params({})

        return match
