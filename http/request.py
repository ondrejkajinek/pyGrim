# coding: utf8

from grim_dicts import ImmutableDict, NormalizedDict
from urllib import unquote_plus

import re


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
        # env
        "http://localhost:7846/test/testovič?param=a"
        {
            'SCRIPT_NAME': '',
            'REQUEST_METHOD': 'GET',
            'PATH_INFO': '/test/testovi\xc4\x8d',
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'QUERY_STRING': 'param=a',
            'HTTP_USER_AGENT': (
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/57.0.2987.111 Safari/537.36 '
                'Vivaldi/1.8.770.38'
            ),
            'HTTP_CONNECTION': 'keep-alive',
            'SERVER_NAME': 'DellInspiron',
            'REMOTE_ADDR': '127.0.0.1',
            'wsgi.url_scheme': 'http',
            'SERVER_PORT': '7846',
            'uwsgi.node': 'DellInspiron',
            'wsgi.input': "<uwsgi._Input object at 0x7f2b860392b8>",
            'HTTP_DNT': '1',
            'HTTP_HOST': 'localhost:7846',
            'wsgi.multithread': False,
            'HTTP_UPGRADE_INSECURE_REQUESTS': '1',
            'REQUEST_URI': '/test/testovi%C4%8D?param=a',
            'HTTP_ACCEPT': (
                'text/html,application/xhtml+xml,application/xml;q=0.9,'
                'image/webp,*/*;q=0.8'
            ),
            'wsgi.version': (1, 0),
            'wsgi.run_once': False,
            'wsgi.errors': (
                "<open file 'wsgi_errors', mode 'w' at 0x7f2b7da3ded0>"
            ),
            'wsgi.multiprocess': True,
            'HTTP_ACCEPT_LANGUAGE': 'cs-CZ,cs;q=0.8',
            'uwsgi.version': '2.0.13',
            'wsgi.file_wrapper': "<built-in function uwsgi_sendfile>",
            'HTTP_ACCEPT_ENCODING': 'gzip, deflate, sdch, br'
        }

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
            matches = self.HOST_REGEXP.match(env["HTTP_HOST"])
        except KeyError:
            host = env["SERVER_NAME"]
        else:
            if matches:
                host = matches.groups()[1]
            else:
                host = env["HTTP_HOST"].split(":")[0]

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
        self._headers = NormalizedDict()
        for key in environment.keys():
            upper_key = key.upper()
            if (
                upper_key.startswith("X_") or
                upper_key.startswith("HTTP_")
            ):
                self._headers[key] = environment.pop(key)

    def _parse_query_params(self):
        self._get_params = self._parse_string(
            self._environment["query_string"]
        )
        self._post_params = self._parse_string(
            "".join(part for part in self._environment["wsgi.input"])
        )
        self.cookies = self._parse_string(self._headers.get("cookie", ""))

    def _parse_string(self, source):
        parts = (
            item
            for item
            in source.split("&")
            if item
        )

        parsed = {}
        for part in parts:
            key, value = (
                map(unquote_plus, part.split("=", 1))
                if "=" in part
                else (unquote_plus(part), None)
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
        self._environment = NormalizedDict(env)
