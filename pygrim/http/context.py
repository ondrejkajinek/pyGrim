# coding: utf8

from .grim_dicts import ImmutableDict
from .request import Request
from .response import Response

import sys
if sys.version_info.major == 3:
    import http.server
    http_responses = {
        code: code_desc[0]
        for code, code_desc
        in http.server.BaseHTTPRequestHandler.responses.items()
    }
else:
    from httplib import responses as http_responses

# in order of http://en.wikipedia.org/wiki/List_of_HTTP_status_codes
http_responses.setdefault(418, "I'm a teapot")  # LOL
http_responses.setdefault(423, "Locked")
http_responses.setdefault(426, "Updgrade Required")
http_responses.setdefault(428, "Precondition Required")


class Context(object):

    def __init__(self, environment):

        self.current_route = None
        self.session = None
        self.template = None
        self.view_data = {}

        self._request = Request(environment)
        self._response = Response()
        self._route_params = None
        self._targets = {
            "request": self._request,
            "response": self._response
        }

        self.set_route_params()

    def GET(self, key=None, fallback=None):
        return self._request.request_param("GET", key, fallback)

    def POST(self, key=None, fallback=None):
        return self._request.request_param("POST", key, fallback)

    def add_cookie(
        self, name, value, lifetime=None, domain=None, path=None,
        http_only=None, secure=None
    ):
        self._response.cookies[name] = {
            "domain": domain,
            "http_only": http_only,
            "lifetime": lifetime,
            "path": path,
            "secure": secure,
            "value": value
        }

    def add_response_headers(self, headers):
        self._response.headers.update(headers)

    def delete_cookie(
        self, name, domain=None, path=None, http_only=None, secure=None
    ):
        if name in self._response.cookies:
            self._response.cookies[name].update({
                "lifetime": -1,
                "value": None
            })
        else:
            self._response.cookies[name] = {
                "domain": domain,
                "http_only": http_only,
                "lifetime": -1,
                "path": path,
                "secure": secure,
                "value": None
            }

    def finalize_response(self):
        self._response.finalize()

    def get_cookies(self):
        return self._request.cookies.copy()

    def get_request_host(self):
        return self._request.environment["host"]

    def get_request_host_with_port(self, scheme=None):
        scheme = scheme or self.get_request_scheme()
        port = self.get_request_port()
        return self.get_request_host() + (
            ""
            if self._request.special_port(scheme, port)
            else ":%d" % port
        )

    def get_request_ip(self):
        return self._request.environment["ip"]

    def get_request_method(self):
        return self._request.environment["request_method"]

    def get_request_port(self):
        return self._request.environment["server_port"]

    def get_request_uri(self):
        return self._request.environment["path_info"]

    def get_request_root_uri(self):
        return self._request.environment["script_name"]

    def get_request_url(self):
        scheme = self.get_request_scheme()
        return "%s://%s" % (scheme, self.get_request_host_with_port(scheme))

    def get_request_scheme(self):
        return self._request.environment["wsgi.url_scheme"]

    def get_response_body(self):
        return self._response.body

    def get_response_headers(self):
        return self._response.headers

    def get_response_status_code(self):
        return "%d %s" % (
            self._response.status, http_responses[self._response.status]
        )

    def load_session(self, session_handler):
        self.session = session_handler.load(self._request)

    def pop_route_params(self):
        params = self._route_params.copy()
        self.set_route_params()
        return params

    def redirect(self, url, status=302):
        self._response.status = status
        self._response.headers["Location"] = url

    def save_session(self, session_handler):
        session_handler.save(self.session)
        if self.session.need_cookie():
            self.add_cookie(
                **session_handler.cookie_for(self.session)
            )

    def set_response_body(self, body):
        self._response.body = body

    def set_response_status(self, status):
        self._response.status = status

    def set_route_params(self, params=None):
        self._route_params = ImmutableDict(params or {})
