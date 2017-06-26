# coding: utf8

from ..components.grim_dicts import ImmutableDict, NormalizedImmutableDict
from logging import getLogger
from re import compile as re_compile, IGNORECASE as re_IGNORECASE
from string import strip as string_strip
from urllib import unquote_plus

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
        self._params = {
            "GET": None,
            "POST": None
        }
        self._parse_headers(environment)
        self._save_environment(environment)
        self.cookies = self._parse_string(self._headers.get("cookie", ""), ";")

    def special_port(self, scheme, port):
        try:
            return self.DEFAULT_SCHEME_PORTS[scheme] != port
        except KeyError:
            return True

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

    def _get_method_param_string(self, method):
        """
        no extra check is done since the method is called
        after it is checked that `method` is ok
        """
        if method == "GET":
            return self.environment["query_string"]
        elif method == "POST":
            return "".join(part for part in self.environment["wsgi.input"])

    def _get_port(self, env):
        try:
            port = int(env.pop("SERVER_PORT"))
        except:
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

    def _parse_query_params(self, method):
        return self._parse_string(
            self._get_method_param_string(method)
        )

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
                map(string_strip, map(unquote_plus, part.split("=", 1)))
                if "=" in part
                else (unquote_plus(part.strip()), None)
            )
            parsed.setdefault(key, []).append(value)

        for key in parsed.iterkeys():
            if len(parsed[key]) == 1:
                parsed[key] = parsed[key][0]

        return ImmutableDict(parsed)

    def _save_environment(self, env):
        method = env.pop("REQUEST_METHOD").upper()
        if method == "HEAD":
            env["original_request_method"] = method
            method = "GET"

        env["host"] = self._get_host(env)
        env["ip"] = self._get_ip(env)
        env["path_info"] = env.pop("PATH_INFO").rstrip("/") + "/"
        env["request_method"] = method
        env["server_port"] = self._get_port(env)
        self.environment = NormalizedImmutableDict(**env)
