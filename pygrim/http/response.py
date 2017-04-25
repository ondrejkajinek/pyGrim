# coding: utf8

# from compatibility import http_responses
from datetime import datetime, timedelta
from logging import getLogger
from urllib import quote_plus as url_quoteplus

log = getLogger("pygrim.http.response")

import sys
import os
if sys.version_info.major == 3:
    import http.server
    http_responses = {
        code: code_desc[0]
        for code, code_desc
        in http.server.BaseHTTPRequestHandler.responses.items()
    }
else:
    from httplib import responses as http_responses
# endif
# in order of http://en.wikipedia.org/wiki/List_of_HTTP_status_codes
http_responses.setdefault(418, "I'm a teapot")  # LOL
http_responses.setdefault(423, "Locked")
http_responses.setdefault(426, "Updgrade Required")
http_responses.setdefault(428, "Precondition Required")


class Response(object):

    COOKIE_PARTS = (
        lambda c: (
            "Domain=%s" % c["domain"]
            if c.get("domain")
            else None
        ),
        lambda c: (
            "Expires=%s" % (
                (datetime.utcnow() + timedelta(seconds=c["lifetime"]))
                .strftime("%a, %d-%b-%Y %H:%M:%S GMT")
            )
            if c.get("lifetime")
            else None
        ),
        lambda c: "HttpOnly" if c.get("http_only") else None,
        lambda c: "Path=%s" % c["path"] if c.get("path") else None,
        lambda c: "Secure" if c.get("secure") else None
    )

    NO_CONTENT_STATUSES = (204, 304)

    def __init__(self):
        self.body = ""
        self.headers = {
            "Content-Type": "text/html"
        }
        self.status = 200

        self._cookies = {}
        self._template = None
        self._view_data = {}

    def add_cookie(
        self, name, value, lifetime=None, domain=None, path=None,
        http_only=None, secure=None
    ):
        self._cookies[name] = {
            "domain": domain,
            "http_only": http_only,
            "lifetime": lifetime,
            "path": path,
            "secure": secure,
            "value": value
        }

    def add_view_data(self, data):
        self._view_data.update(data)

    def clear_view_data(self):
        self._view_data = {}

    def delete_cookie(
        self, name, domain=None, path=None, http_only=None, secure=None
    ):
        if name in self._cookies:
            self._cookies[name].update({
                "lifetime": -1,
                "value": None
            })
        else:
            self._cookies[name] = {
                "domain": domain,
                "http_only": http_only,
                "lifetime": -1,
                "path": path,
                "secure": secure,
                "value": None
            }

    def delete_view_data(self, key):
        try:
            del self._view_data[key]
        except KeyError:
            pass

    def finalize(self):
        log.debug(self.headers)
        if self.status in self.NO_CONTENT_STATUSES:
            del self.headers["Content-Type"]
            self.body = ""
        else:
            if isinstance(self.body, unicode):
                self.body = self.body.encode("utf-8")

            if isinstance(self.body, (basestring,)):
                self.headers["Content-Length"] = str(len(self.body))
            elif hasattr(self.body, "seek") and hasattr(self.body, "tell"):
                self.body.seek(0, os.SEEK_END)
                self.headers["Content-Length"] = str(self.body.tell())
                self.body.seek(0)
            else:
                log.warning(
                    "Unable to get Content-Length for content %r", self.body
                )
                self.headers["Content-Length"] = 0

        self.headers = [
            (key, str(value))
            for key, value
            in self.headers.iteritems()
        ]
        log.debug("RESPONSE HEADERS: %r", self.headers)

        if self._cookies:
            for cookie in self._serialized_cookies():
                self.headers.append(("Set-Cookie", cookie))

    def get_template(self):
        return self._template

    def get_view_data(self):
        return self._view_data

    def redirect(self, url, status=302):
        self.status = status
        self.headers["Location"] = url

    def set_template(self, template):
        self._template = template

    def status_code(self):
        return "%d %s" % (self.status, http_responses[self.status])

    def _serialize_cookie(self, name, cookie):
        params = (
            part_formatter(cookie)
            for part_formatter
            in self.COOKIE_PARTS
        )
        cookie_params = "; ".join(filter(None, params))
        return "%s=%s%s" % (
            url_quoteplus(name),
            url_quoteplus(str(cookie["value"])),
            (
                "; %s" % cookie_params
                if cookie_params
                else ""
            )
        )

    def _serialized_cookies(self):
        for name, cookie in self._cookies.iteritems():
            yield self._serialize_cookie(name, cookie)
