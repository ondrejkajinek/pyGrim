# coding: utf8

# std
from logging import getLogger
from re import compile as re_compile, IGNORECASE as re_IGNORECASE
from string import strip as string_strip
from urllib import unquote_plus

# local
from .methods import DELETE, GET, POST, PUT
from ..components.containers import ImmutableDict, NormalizedImmutableDict
from ..components.utils import get_instance_name
from ..components.utils.json2 import loads as json_loads

log = getLogger("pygrim.http.request")


class Request(object):

    DEFAULT_SCHEME_PORTS = {
        "http": 80,
        "https": 443
    }

    HOST_REGEXP = re_compile(r"^(\[[a-f0-9:.]+\])(:\d+)?\Z", re_IGNORECASE)

    IP_KEYS = (
        "X_REAL_IP", "X_FORWARDED_FOR", "HTTP_X_FORWARDED_FOR", "CLIENT_IP",
        "REMOTE_ADDR"
    )

    def __init__(self, environment):
        self._parse_headers(environment)
        self._save_environment(environment)
        self.cookies = self._parse_string(self._headers.get("cookie"), ";")

    def __getattr__(self, attr):
        save = True
        if (
            attr == "JSON" and
            self.content_type == "application/json"
        ):
            try:
                data = json_loads(self.RAW_POST)
            except BaseException:
                log.exception("Error loding json data from request")
                data = {}
                save = False
        elif attr == "RAW_POST":
            data = "".join(part for part in self.environment["wsgi.input"])
        elif attr in (GET, DELETE):
            data = self._parse_string(self.environment.get("query_string"))
        elif attr in (POST, PUT):
            if self.content_type in (
                None, "application/x-www-form-urlencoded"
            ):
                data = self._parse_string(self.RAW_POST)
            else:
                data = {}
        elif attr == "content_type":
            data = self._get_content_type()
        else:
            raise AttributeError("%r object has no attribute %r" % (
                get_instance_name(self), attr
            ))

        if save:
            setattr(self, attr, data)

        return data

    def special_port(self, scheme, port):
        try:
            return self.DEFAULT_SCHEME_PORTS[scheme] != port
        except KeyError:
            return True

    def _accept_language(self, env):
        return env.pop("ACCEPT_LANGUAGE", "").split(",")

    def _get_content_type(self):

        def _normalize_content_type(c_type):
            if c_type:
                c_type = c_type.split(";", 1)[0].strip().lower()

            return c_type or None

        c_type = _normalize_content_type(
            self._headers.get("content_type")
        )
        # fallback for some special cases when content type is not present
        #   in headers but can be found in environment without HTTP_ prefix
        if not c_type:
            c_type = _normalize_content_type(
                self.environment.get("content_type")
            )

        return c_type or None

    def _get_host(self, env):
        try:
            matches = self.HOST_REGEXP.match(self._headers["host"])
        except KeyError:
            host = env["SERVER_NAME"]
        else:
            if matches:
                host = matches.groups()[1]
            else:
                host = self._headers["host"].split(":")[0]

        return host

    def _get_ip(self, env):
        for key in self.IP_KEYS:
            try:
                ip = env[key].split(",")[0].strip()
                break
            except KeyError:
                pass
        else:
            ip = None

        return ip

    def _get_port(self, env):
        try:
            port = int(env.pop("SERVER_PORT"))
        except BaseException:
            port = self.DEFAULT_SCHEME_PORTS[env["wsgi.url_scheme"]]

        return port

    def _parse_headers(self, environment):
        headers = {}
        for key in environment.iterkeys():
            upper_key = key.upper()
            if (
                upper_key.startswith("X_") or
                upper_key.startswith("HTTP_")
            ):
                headers[key] = environment.get(key)

        self._headers = NormalizedImmutableDict(**headers)

    def _parse_string(self, source, pairs_separator="&"):
        source = source or ""
        parts = (item for item in source.split(pairs_separator) if item)
        parsed = {}
        for part in parts:
            key, value = (
                [unquote_plus(i).strip() for i in part.split("=", 1)]
                if "=" in part
                else (unquote_plus(part.strip()), None)
            )
            parsed.setdefault(key, []).append(value)

        for key in parsed.iterkeys():
            if len(parsed[key]) == 1:
                parsed[key] = parsed[key][0]

        return ImmutableDict(parsed)

    def _save_environment(self, env):
        env["host"] = self._get_host(env)
        env["ip"] = self._get_ip(env)
        env["path_info"] = env.pop("PATH_INFO").rstrip("/") or "/"
        env["request_method"] = env.pop("REQUEST_METHOD").upper()
        env["server_port"] = self._get_port(env)
        env["accept_language"] = self._accept_language(env)
        self.environment = NormalizedImmutableDict(**env)
