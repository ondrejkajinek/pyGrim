# coding: utf8

from json import dumps as json_dumps

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

    def __init__(
        self, environment, config, request_class, response_class, debug=False
    ):
        self._debug = debug
        self.canonical_args = None
        self.formater = None
        self.config = config
        self._suppress_port = config.getbool("context:suppress_port", False)
        self._force_https = config.getbool("context:force_https", False)
        self._default_headers = config.get("context:default_headers", None)
        self._lang_switch = config.get("pygrim:i18n:locale_switch", "lang")

        self.disable_content_length = config.get(
            "view:disable_content_length", False)
        self.current_route = None
        self.session = None
        self.template = None
        self.view_data = {}

        self._request = request_class(environment)

        self._enabled_acceptances = {"function"}
        cookie_acceptance = self.get_cookie("cookie_accept")
        self._acceptance_is_set = bool(cookie_acceptance)
        if cookie_acceptance:
            self._enabled_acceptances |= set(
                {
                    "P": "preference",
                    "A": "analytics",
                    "M": "marketing",
                    "F": "function"
                }.get(k, "function") for k in cookie_acceptance
            )

        self._response = response_class()
        if self._default_headers:
            self.add_response_headers(self._default_headers)

        self._session_loaded = False
        self.set_route_params()

        self._default_language = 'cs_CZ.UTF8'
        self._language = self._default_language
        self._lang_key = None
        self._languages = (self._default_language,)
        self._debug_languages = ()
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
        http_only=None, secure=None, same_site=None
    ):
        """
        Sets cookie with specified name, value, domain, path, etc.,
        for a lifetime relative to utcnow()
        """
        self._response.cookies[name] = {
            "domain": domain,
            "http_only": http_only,
            "lifetime": lifetime,
            "path": path,
            "secure": secure,
            "value": value,
            "same_site": same_site
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
        self, name, domain=None, path=None, http_only=None, secure=None,
        same_site=None
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
                "value": None,
                "same_site": same_site
            }

    def dump_request(self):
        environment = {
            key: value
            for key, value
            in self._request.environment.iteritems()
            if not key.startswith(("wsgi.", "uwsgi."))
        }
        environment.update((
            ("RAW_POST", self._request.RAW_POST),
            ("POST", self._request.POST)
        ))
        if self.get_request_content_type() == "application/json":
            environment["JSON"] = self._request.JSON

        return json_dumps({
            "environment": environment,
            "cookies": self._request.cookies
        })

    def finalize_response(self):
        self._response.finalize()

    def generates_response(self):
        return (
            self._response.is_generator or
            self._response.is_generator_function
        )

    def get_cookie(self, key):
        return self._request.cookies.get(key)

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

    def get_available_languages(self, debug=False):
        debug = debug or self._debug
        if debug:
            return tuple(self._languages)
        else:
            return tuple(
                language
                for language in self._languages
                if language not in self._debug_languages
            )

    def get_request_content_type(self):
        return self._request.content_type

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
        return self._request.environment.get("script_name") or "/"

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

    def is_generator_function(self):
        return self._response.is_generator_function

    def is_request_get(self):
        return self._request.environment["request_method"] == "GET"

    def is_request_head(self):
        return self._request.environment.get(
            "original_request_method") == "HEAD"

    def is_request_post(self):
        return self._request.environment["request_method"] == "POST"

    def is_cookie_acceptance_set(self):
        return self._acceptance_is_set

    def set_cookie_acceptance(self, enabled_preferences):
        enabled_preferences = list(enabled_preferences)
        if "function" not in enabled_preferences:
            enabled_preferences.append("function")
        enabled_preferences.sort()

        value = "".join({
            "preference": "P",
            "analytics": "A",
            "marketing": "M",
            "function": "F"
        }[k] for k in enabled_preferences)

        self.add_cookie(
            name="cookie_accept",
            value=value,
            # lifetime=2 * 365.25 * 24 * 60 * 60 - 2 roky dle tasku #93872
            lifetime=63115200,
            path="/",
        )

        if "preference" not in enabled_preferences:
            self.unset_language_cookie()

    def is_cookie_acceptance_enabled(self, acceptance):
        return (
            acceptance == "function" or
            acceptance in self._enabled_acceptances
        )

    def load_session(self, session_handler):
        if self._session_loaded is False:
            self.session = session_handler.load(self._request)
            self._session_loaded = True
            log.debug(
                "Session handler: %r loaded session: %r",
                type(session_handler), self.session
            )
        # endif

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

    def set_language(self, language, debug=False, with_cookie=True):
        debug = debug or self._debug
        language = self._language_map.get(language)
        if language in self._languages:
            if self.formater:
                self.formater._set_locale(language)
            else:
                self.formater = Formater(language)
            self._language = language
            if with_cookie:
                # lang cookie is not nesessary to be secured => same_site=None
                self.add_cookie(
                    self._lang_key, self._language, 3600 * 24 * 365,
                    path="/", same_site="None"
                )
        else:
            log.warning("Language %r is not supported", language)
            self._language = self._default_language

    def unset_language_cookie(self):
        if self._lang_key is not None:
            # pozor params stejné jako při vytváření
            self.delete_cookie(
                name=self._lang_key,
                domain=None,
                path="/",
                http_only=None,
                secure=None,
                same_site="None"
            )

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
        self._debug_languages = (
            self.config.get("pygrim:i18n:debug_locales", None) or ()
        )
        self._language_map = {
            lang: lang
            for lang
            in self._languages
        }
        self._language_map.update(
            self.config.get("pygrim:i18n:locale_map", {})
        )
        self._language = self._select_language(
            with_cookie=self.is_cookie_acceptance_enabled("preference")
        )

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

    def _select_language(self, debug=False, with_cookie=False):
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
        self.set_language(language, debug=debug, with_cookie=with_cookie)
        return self._language

    def get_canonical_url(self, _raise_on_error=False, **args):
        def get_in(where, keys):
            if not isinstance(keys, (tuple, list)):
                return keys
            for one in keys:
                if hasattr(where, one):
                    where = getattr(where, one)
                else:
                    where = where[one]
            return where
        if self.current_route is None:
            return None
        try:
            data = {}
            if self.canonical_args:
                data = {
                    k: get_in(self.view_data, keys)
                    for k, keys in self.canonical_args.iteritems()
                }
            data.update(args)
            return self.get_request_url() + self.current_route.url_for(data)
        except:
            if (
                _raise_on_error is True or
                self._debug
            ):
                raise
            return None
# eof
