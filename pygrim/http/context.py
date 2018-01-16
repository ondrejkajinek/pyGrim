# coding: utf8

from .grim_dicts import ImmutableDict
from ..components.formater import Formater
from ..components.jinja_ext.i18n import I18NExtension, Undefined
from logging import getLogger

try:
    from compatibility import http_responses
except ImportError:
    from .codes import http_responses

log = getLogger("pygrim.http.context")


class Context(object):

    def __init__(self, environment, config, request_class, response_class):
        self.formater = None
        self.config = config
        self._suppress_port = config.getbool("context:suppress_port", False)
        self._force_https = config.getbool("context:force_https", False)
        self._default_headers = config.get("context:default_headers", None)
        self._lang_switch = config.get("pygrim:i18n:locale_switch", "lang")

        self.current_route = None
        self.session = None
        self.template = None
        self.view_data = {}

        self._request = request_class(environment)
        self._response = response_class()
        if self._default_headers:
            self.add_response_headers(self._default_headers)

        self._session_loaded = False
        self.set_route_params()

        self._default_language = 'cs_CZ.UTF8'
        self._language = self._default_language
        self._lang_key = None
        self._languages = (self._default_language,)
        self._language_map = {}
        if self.config.get("pygrim:i18n", False):
            self._initialize_localization()
        if not self.formater:
            self.formater = Formater(self.get_language())

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
        extra = self.view_data.setdefault("extra_css", [])
        extra.extend(args)

    def add_js(self, *args, **kwargs):
        location_path = "header" if kwargs.get("header", True) else "footer"
        sync_path = "sync" if kwargs.get("sync", True) else "async"
        extra = self.view_data.setdefault(
            "extra_js_%s_%s" % (location_path, sync_path), []
        )
        extra.extend(args)

    def add_response_headers(self, headers):
        self._response.headers.update(
            (str(k), str(v))
            for k, v
            in headers.items()
        )

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

    def get_language(self):
        return (
            self._language
            if self._language in self._languages
            else self._default_language
        )

    def lang_text(self, source, order=None):
        if order is None:
            order = (i.split("_", 1)[0] for i in self._languages)
        ret = I18NExtension.lang_text(
            source, self._language.split("_", 1)[0], order=order
        )
        if isinstance(ret, Undefined):
            ret = None
        return ret

    def get_available_languages(self):
        return tuple(self._languages)

    def get_request_content_type(self):
        return self._request.environment["content_type"]

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
        """
        if self._force_https:
            return "https"
        return self._request.environment["wsgi.url_scheme"]
        """

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

    def is_request_head(self):
        return self._request.environment.get(
            "original_request_method") == "HEAD"

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

    def set_language(self, language):
        language = self._language_map.get(language)
        if language in self._languages:
            if self.formater:
                self.formater._set_locale(language)
            else:
                self.formater = Formater(language)
            self._language = language
            self.add_cookie(
                self._lang_key, self._language, 3600 * 24 * 365, path="/"
            )
        else:
            log.warning("Language %r is not supported", language)

    def set_response_body(self, body):
        self._response.body = body

    def set_response_content_type(self, content_type):
        self._response.headers["Content-Type"] = content_type

    def set_response_status(self, status):
        self._response.status = status

    def set_route_params(self, params=None):
        self._route_params = ImmutableDict(params or {})

    def _initialize_localization(self):
        self._default_language = self.config.get("pygrim:i18n:default_locale")
        self._lang_key = self.config.get(
            "pygrim:i18n:cookie_key", "site_language"
        )
        self._languages = self.config.get("pygrim:i18n:locales")
        self._language_map = {
            lang: lang
            for lang
            in self._languages
        }
        self._language_map.update(
            self.config.get("pygrim:i18n:locale_map", {})
        )
        self._language = self._select_language()

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

    def _select_language(self):
        language = self._language_map.get(self.GET(self._lang_switch))
        if language is None:
            cookieval = self._request.cookies.get(self._lang_key)
            if cookieval and isinstance(cookieval, list):
                cookieval = cookieval[-1]
            if cookieval:
                language = self._language_map.get(cookieval)
            else:
                language = None

        if language is None:
            try:
                accept_languages = (
                    self._language_map.get(lang.split(";")[0])
                    for lang
                    in self._request.environment["accept_language"].split(",")
                )
            except KeyError:
                language = self._default_language
            else:
                language = (
                    next((lang for lang in accept_languages if lang), None) or
                    self._default_language
                )
        else:
            # lang was in url or in get => create or prolong lang cookie
            self.set_language(language)

        return language
