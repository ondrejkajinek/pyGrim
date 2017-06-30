# coding: utf8

from ..components.routing import StopDispatch
from ..components.grim_dicts import ImmutableDict
from .exceptions import HeadersAlreadySent
from .request import Request
from .response import Response
from logging import getLogger

try:
    from compatibility import http_responses
except ImportError:
    from .codes import http_responses

log = getLogger("pygrim.http.context")


class Context(object):

    def __init__(self, environment, config, model, session_handler):
        self.config = config
        self.current_route = None
        self.model = model
        self.template = None
        self.view_data = {}

        super(Context, self).__setattr__("_can_create_session", True)
        self._force_https = config.getbool("context:force_https", False)
        self._request = Request(environment)
        self._response = Response()
        self._route_params = None
        self._session_handler = session_handler
        super(Context, self).__setattr__("_session_loaded", False)
        self._suppress_port = config.getbool("context:suppress_port", False)
        self._view = None

        self.add_response_headers(config.get("context:default_headers", {}))
        self.set_route_params()

    def __getattr__(self, key):
        if key == "session":
            if (
                self._can_create_session is False and
                self._request.cookies.get("SESS_ID") is None
            ):
                raise HeadersAlreadySent("can't create new session!")

            super(Context, self).__setattr__("_session_loaded", False)
            self.load_session()
            return self.session

        raise AttributeError(key)

    def __setattr__(self, key, value):
        if key == ("_can_create_session", "_session_loaded"):
            raise RuntimeError("%r is readonly!" % key)

        super(Context, self).__setattr__(key, value)

    def DELETE(self, key=None, fallback=None):
        return self._request_param("DELETE", key, fallback)

    def GET(self, key=None, fallback=None):
        return self._request_param("GET", key, fallback)

    def JSON(self, key=None, fallback=None):
        return self._request_param("JSON", key, fallback)

    def PARAM(self, key=None, fallback=None):
        return self._request_param(self.get_request_method(), key, fallback)

    def POST(self, key=None, fallback=None):
        return self._request_param("POST", key, fallback)

    def PUT(self, key=None, fallback=None):
        return self._request_param("PUT", key, fallback)

    def RAW_POST(self):
        return self._request.RAW_POST

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
        extra.update(args)

    def add_js(self, *args, **kwargs):
        location_path = "header" if kwargs.get("header", True) else "footer"
        sync = "sync" if kwargs.get("sync", True) else "async"
        self.view_data.setdefault(
            "extra_js_%s_%s" % (location_path, sync), set()
        ).update(args)

    def add_response_headers(self, headers):
        self._response.headers.update(
            (str(k), str(v))
            for k, v
            in headers.iteritems()
        )

    def delete_cookie(
        self, name, domain=None, path=None, http_only=None, secure=None
    ):
        if name in self._response.cookies:
            self._response.cookies[name].update((
                ("lifetime", -1),
                ("value", None)
            ))
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
        self._response.finalize(is_head=self.is_request_head())
        super(Context, self).__setattr__("_can_create_session", False)

    def generates_response(self):
        return self._response.is_generator

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
        return (
            "https"
            if self._force_https
            else self._request.environment["wsgi.url_scheme"]
        )

    def get_response_body(self):
        return self._response.body

    def get_response_headers(self):
        return self._response.headers

    def get_response_status_code(self):
        return "%d %s" % (
            self._response.status, http_responses[self._response.status]
        )

    def get_route_params(self):
        return self._route_params.copy()

    def get_view(self):
        return self._view

    def is_request_get(self):
        return self._request.environment["request_method"] == "GET"

    def is_request_head(self):
        return (
            self._request.environment.get("original_request_method") == "HEAD"
        )

    def is_request_post(self):
        return self._request.environment["request_method"] == "POST"

    def load_session(self):
        if self._session_loaded is False:
            self.session = self._session_handler.load(self._request)
            super(Context, self).__setattr__("_session_loaded", True)
            self.add_cookie(**self._session_handler.cookie_for(self.session))
            log.debug(
                "Session handler: %r loaded session: %r",
                type(self._session_handler), self.session
            )

    def redirect(self, url, status=302):
        self._response.status = status
        self._response.headers["Location"] = url
        raise StopDispatch()

    def save_session(self):
        self._session_handler.save(self.session)

    def session_loaded(self):
        return self._session_loaded

    def set_response_body(self, body):
        self._response.set_body(body)

    def set_response_content_type(self, content_type):
        self._response.headers["Content-Type"] = content_type

    def set_response_status(self, status):
        self._response.status = status

    def set_route_params(self, params=None):
        self._route_params = ImmutableDict(params or {})

    def set_view(self, view):
        self._view = view

    def _request_param(self, method, key=None, fallback=None):
        try:
            value = (
                getattr(self._request, method)
                if key is None
                else getattr(self._request, method).get(key, fallback)
            )
        except AttributeError:
            log.warning(
                "Trying to get param sent by unknown method %r", method
            )
            value = None

        return value
