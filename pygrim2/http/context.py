# std
from json import dumps as json_dumps
from logging import getLogger

# local
from .codes import http_responses
from .exceptions import HeadersAlreadySent
from .methods import DELETE, GET, HEAD, POST, PUT
from ..components.routing import StopDispatch
from ..components.containers import ImmutableDict, NormalizedDict
from ..components.utils.decorators import lazy_property

log = getLogger("pygrim.http.context")

LANGUAGE_CASCADE = ("cs", "sk", "cs", "en", "de", "ru")


class Context(object):

    language_priority = None

    def __init__(
        self, config, model, session_handler, l10n, request, response
    ):
        self.config = config
        self.current_route = None
        self.disable_content_length = config.get(
            "view:disable_content_length", False
        )
        self.l10n = l10n
        self.model = model
        self.template = None
        self.view_data = {}

        self._can_create_session = True
        self._force_https = config.getbool("context:force_https", False)
        self._request = request
        self._response = response
        self._session_handler = session_handler
        self._save_session = False
        self._session_loaded = False
        self._suppress_port = config.getbool("context:suppress_port", False)
        self._uses_flash = config.getbool("session:flash", True)
        self._view = None

        self.add_response_headers(config.get("context:default_headers", {}))
        self._initialize_localization()
        self.set_route_params()

    @property
    def can_crate_session(self):
        return self._can_create_session

    @property
    def session_changed(self):
        return self._save_session

    @session_changed.setter
    def session_changed(self, value):
        # a bit faster than isinstance(value, boolean)
        if value is True or value is False:
            self._save_session = value
        else:
            raise ValueError("save_session must be boolean")

    @lazy_property
    def session(self):
        if self._can_create_session is False:
            raise HeadersAlreadySent("Can't create new session!")

        session = self._load_session()
        self._save_session = True
        self._session_loaded = True
        return session

    @property
    def session_loaded(self):
        return self._session_loaded

    def DELETE(self, key=None, fallback=None):
        return self._request_param(DELETE, key, fallback)

    def GET(self, key=None, fallback=None):
        return self._request_param(GET, key, fallback)

    def JSON(self, key=None, fallback=None):
        return self._request_param("JSON", key, fallback)

    def PARAM(self, key=None, fallback=None):
        return self._request_param(self.get_request_method(), key, fallback)

    def POST(self, key=None, fallback=None):
        return self._request_param(POST, key, fallback)

    def PUT(self, key=None, fallback=None):
        return self._request_param(PUT, key, fallback)

    def RAW_POST(self):
        return self._request.RAW_POST

    def add_cookie(
        self, name, value, lifetime=None, domain=None, path=None,
        http_only=None, secure=None
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
            "value": value
        }

    def add_css(self, *args):
        extra = self.view_data.setdefault("extra_css", [])
        extra += args

    def add_js(self, *args, **kwargs):
        location_path = "header" if kwargs.get("header", True) else "footer"
        sync = "sync" if kwargs.get("sync", True) else "async"
        extra = self.view_data.setdefault(
            "extra_js_%s_%s" % (location_path, sync), []
        )
        extra += args

    def add_response_headers(self, headers):
        self._response.headers.update(
            (k, v)
            for k, v
            in headers.items()
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

    def delete_response_headers(self):
        self._response.headers = NormalizedDict()

    def dump_request(self):
        return json_dumps({
            "environment": {
                key: value
                for key, value
                in self._request.environment.items()
                if not (key.startswith("wsgi.") or key.startswith("uwsgi."))
            },
            "cookies": self._request.cookies
        })

    def finalize_response(self):
        self._response.finalize(is_head=self.is_request_head())
        self._can_create_session = False

    def flash(self, type_, message):
        if "_flash" in self.session:
            self.session["_flash"].append((type_, message))
        else:
            log.warning("Trying to use disabled flash messages!")

    def generates_response(self):
        return self._response.is_generator

    def get_cookie(self, key):
        return self._request.cookies.get(key)

    def get_cookies(self):
        return self._request.cookies.copy()

    def get_flashes(self, types=None):
        messages = self.session.get("_flash")
        index = 0
        while index < len(messages):
            if types is None or messages[index][0] in types:
                message = messages.pop(index)
                yield message[0], message[1]
            else:
                index += 1

    def get_language(self):
        return self._language

    def get_language_priority(self):
        if self.language_priority:
            return self.language_priority

        language = self._language.split("_", 1)[0]
        if language in LANGUAGE_CASCADE:
            idx = LANGUAGE_CASCADE.index(language)
            lp = LANGUAGE_CASCADE[idx:] + LANGUAGE_CASCADE[:idx]
        else:
            lp = [language] + LANGUAGE_CASCADE
        self.language_priority = lp
        return lp

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
        return self._response.serialized_headers()

    def get_response_status_code(self):
        return "%d %s" % (
            self._response.status, http_responses[self._response.status]
        )

    def get_route_params(self):
        return self._route_params.copy()

    def get_view(self):
        return self._view

    def is_request_get(self):
        return self._request.environment["request_method"] == GET

    def is_request_head(self):
        return self._request.environment["request_method"] == HEAD

    def is_request_post(self):
        return self._request.environment["request_method"] == POST

    def redirect(self, url, status=302):
        self._response.status = status
        self._response.headers["Location"] = url
        raise StopDispatch()

    def save_session(self):
        if self.session_loaded and self.session_changed:
            self._session_handler.save(self.session)

    def set_language(self, language, with_cookie=False):
        if self._check_language(language):
            self._session_load_should_save_lang_cookie = False
            self._language = language
            if with_cookie:
                self._save_language_cookie()

    def set_temp_language(self, language):
        if self._check_language(language):
            self._language = language

    def set_response_body(self, body):
        self._response.body = body

    def set_response_content_type(self, content_type):
        self._response.headers["Content-Type"] = content_type

    def set_response_status(self, status):
        self._response.status = status

    def set_route_params(self, *args, **kwargs):
        self._route_params = ImmutableDict(*args, **kwargs)

    def set_view(self, view):
        self._view = view

    def get_available_languages(self):
        return self.l10n.translations().keys()

    def _check_language(self, language):
        res = self.l10n.has(language)
        if res is False:
            log.warning(
                "Language %r is not supported, supported languages: %r",
                language, self.l10n.translations().keys()
            )

        return res

    def _initialize_localization(self):
        (
            self._language,
            self._session_load_should_save_lang_cookie
        ) = self.l10n.select_language(self)
        # lang cookies se odkládá až to budu dle souhlasu moct udělat
        #   (po load session)

    def _session_preference_cookies_enabled(self, session):
        try:
            if not session:
                return False
            accept = session.get("cookie_accept")
            if not accept:
                return False
            return bool(accept.get("preference"))
        except BaseException:
            log.exception("err setting lang after session loading")
            return False

    def _preference_cookies_enabled(self):
        try:
            if not self._session_loaded:
                return False
            return self._session_preference_cookies_enabled(self.session)
        except BaseException:
            log.exception("err setting lang after session loading")
            return False

    def _load_session(self):
        session = self._session_handler.load(self._request)
        self.add_cookie(**self._session_handler.cookie_for(session))
        log.debug(
            "Session handler: %r loaded session: %r",
            type(self._session_handler), session
        )
        if self._uses_flash and "_flash" not in session:
            session["_flash"] = []

        if (
            self._session_load_should_save_lang_cookie and
            self._language and
            self._session_preference_cookies_enabled(session)
        ):
            self._session_load_should_save_lang_cookie = False
            self._save_language_cookie()

        return session

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

    def _save_language_cookie(self):
        self.add_cookie(
            self.l10n.lang_key(), self._language, 3600 * 24 * 365, path="/"
        )
