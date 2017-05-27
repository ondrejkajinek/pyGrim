# coding: utf8

from .grim_dicts import ImmutableDict
from .request import Request
from .response import Response
from logging import getLogger

try:
    from compatibility import http_responses
except ImportError:
    from .codes import http_responses

log = getLogger("pygrim.http.context")


class Context(object):

    def __init__(self, environment, config):
        self.config = config
        self._suppress_port = config.get("context:suppress_port", False)
        self._force_https = config.get("context:force_https", False)

        self.current_route = None
        self.session = None
        self.template = None
        self.view_data = {}

        self._request = Request(environment)
        self._response = Response()
        self._route_params = None
        self._session_loaded = False

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

    def add_css(self, *args):
        extra = self.view_data.setdefault("extra_css", set())
        extra.update(set(args))

    def add_js(self, *args, **kwargs):
        location_path = "header" if kwargs.get("header", True) else "footer"
        sync_path = "sync" if kwargs.get("sync", True) else "async"
        extra = self.view_data.setdefault(
            "extra_js_%s_%s" % (location_path, sync_path), set()
        )
        extra.update(set(args))

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

    def generates_response(self):
        return self._response.is_generator_function

    def get_cookies(self):
        return self._request.cookies.copy()

    def get_request_host(self):
        return self._request.environment["host"]

    def get_request_host_with_port(self, scheme=None):
        if self._suppress_port:
            return self.get_request_host()
        port = self.get_request_port()
        return self.get_request_host() + (
            ""
            if not self._request.special_port(scheme, port)
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
        if self._force_https:
            return "https"
        return self._request.environment["wsgi.url_scheme"]

    def get_response_body(self):
        return self._response.body

    def get_response_headers(self):
        return self._response.headers

    def get_response_status_code(self):
        return "%d %s" % (
            self._response.status, http_responses[self._response.status]
        )

    def is_request_get(self):
        return self._request.environment["request_method"] == "GET"

    def is_request_post(self):
        return self._request.environment["request_method"] == "POST"

    def load_session(self, session_handler):
        if self._session_loaded is False:
            self.session = session_handler.load(self._request)
            self._session_loaded = True
            log.debug(
                "Session handler: %r loaded session: %r",
                type(session_handler), self.session
            )

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

    def session_loaded(self):
        return self._session_loaded

    def set_response_body(self, body):
        self._response.body = body

    def set_response_content_type(self, content_type):
        self._response.headers["Content-Type"] = content_type

    def set_response_status(self, status):
        self._response.status = status

    def set_route_params(self, params=None):
        self._route_params = ImmutableDict(params or {})
