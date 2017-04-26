# coding: utf8

from .grim_dicts import ImmutableDict, NormalizedImmutableDict
from logging import getLogger
from urllib import unquote_plus

import re

log = getLogger("pygrim.http.request")


class Request(object):

    DEFAULT_SCHEME_PORTS = {
        "http": 80,
        "https": 443
    }

    HOST_REGEXP = re.compile(r"^(\[[a-f0-9:.]+\])(:\d+)?\Z", re.IGNORECASE)

    IP_KEYS = (
        "X_FORWARDED_FOR", "HTTP_X_FORWARDED_FOR", "CLIENT_IP"
    )

    def __init__(self, environment):
        self.session = None
        self.set_route_params()
        self._parse_headers(environment)
        self._save_environment(environment)
        self._parse_query_params()

    def get(self, key=None, fallback=None):
        return self._safe_param(self._get_params, key, fallback)

    def get_host(self):
        return self._environment["host"]

    def get_ip(self):
        return self._environment["ip"]

    def get_method(self):
        return self._environment["request_method"]

    def get_port(self):
        return self._environment["server_port"]

    def get_request_uri(self):
        return self._environment["path_info"]

    def get_root_uri(self):
        return self._environment["script_name"]

    def get_scheme(self):
        return self._environment["wsgi.url_scheme"]

    def get_url(self):
        return "%s://%s%s" % (
            self.get_scheme(), self.get_host(),
            (
                ""
                if self.DEFAULT_SCHEME_PORTS.get(self.get_port())
                else ":%d" % self.get_port()
            )
        )

    def pop_route_params(self):
        params = self.route_params.copy()
        self.set_route_params()
        return params

    def post(self, key=None, fallback=None):
        return self._safe_param(self._post_params, key, fallback)

    def set_route_params(self, params=None):
        self.route_params = ImmutableDict(params or {})

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
                ip = env[key]
                break
            except KeyError:
                pass
        else:
            ip = env["REMOTE_ADDR"]

        return ip

    def _get_port(self, env):
        try:
            return int(env["SERVER_PORT"])
        except:
            return self.DEFAULT_SCHEME_PORTS[env["wsgi.url_scheme"]]

    def _parse_headers(self, environment):
        headers = {}
        for key in environment.keys():
            upper_key = key.upper()
            if (
                upper_key.startswith("X_") or
                upper_key.startswith("HTTP_")
            ):
                headers[key] = environment.pop(key)

        self._headers = NormalizedImmutableDict(headers)

    def _parse_query_params(self):
        self._get_params = self._parse_string(
            self._environment["query_string"]
        )
        self._post_params = self._parse_string(
            "".join(part for part in self._environment["wsgi.input"])
        )
        self.cookies = self._parse_string(self._headers.get("cookie", ""), ";")

    def _parse_string(self, source, pairs_separator="&"):
        parts = (
            item
            for item
            in source.split(pairs_separator)
            if item
        )

        parsed = {}
        for part in parts:
            key, value = (
                map(lambda x: x.strip(), map(unquote_plus, part.split("=", 1)))
                if "=" in part
                else (unquote_plus(part.strip()), None)
            )
            parsed.setdefault(key, []).append(value)

        for key in parsed.iterkeys():
            if len(parsed[key]) == 1:
                parsed[key] = parsed[key][0]

        return ImmutableDict(parsed)

    def _safe_param(self, source, key=None, fallback=None):
        if key is not None:
            return source.get(key, fallback)
        else:
            return source

    def _save_environment(self, env):
        env["host"] = self._get_host(env)
        env["ip"] = self._get_ip(env)
        env["path_info"] = env.pop("PATH_INFO").rstrip("/")
        env["request_method"] = env.pop("REQUEST_METHOD").upper()
        env["server_port"] = self._get_port(env)
        self._environment = NormalizedImmutableDict(env)
