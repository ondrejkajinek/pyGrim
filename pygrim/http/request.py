# coding: utf8

from .grim_dicts import ImmutableDict, NormalizedImmutableDict
from logging import getLogger
from re import compile as re_compile, IGNORECASE as re_IGNORECASE
from string import strip as string_strip
from urllib import unquote_plus
from ..components.utils import json2 as json
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

    def __getattr__(self, attr):
        if (
            attr == "JSON" and
            self._headers.get("content_type") == "application/json"
        ):
            try:
                self.JSON = json.loads(self.RAW_POST)
                return self.JSON
            except:
                log.exception("Error loding json data from request")
                return {}
        elif attr == "RAW_POST":
            self.RAW_POST = "".join(
                part for part in self.environment["wsgi.input"])
            return self.RAW_POST
        elif attr in ("GET", "DELETE"):
            data = self._parse_string(self.environment["query_string"])
            setattr(self, attr, data)
            return data

        elif attr in ("POST", "DELETE"):
            c_t = self._headers.get("content_type")
            if c_t is None or c_t == "application/x-www-form-urlencoded":
                data = self._parse_string(self.RAW_POST)
            else:
                data = {}
            setattr(self, attr, data)
            return data
        # endif
        raise AttributeError(
            "%r object has no attribute %r" % (self.__class__.__name__, attr))

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
                headers[key] = environment.get(key)

        self._headers = NormalizedImmutableDict(headers)

    def _parse_string(self, source, pairs_separator="&"):
        if not source:
            return ImmutableDict()
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
        self.environment = NormalizedImmutableDict(env)
