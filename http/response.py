# coding: utf8

# from compatibility import http_responses
from datetime import datetime, timedelta
from urllib import quote_plus as url_quote

import sys
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
        ("domain", lambda c: (
            "domain=%s" % c["domain"]
            if c.get("domain")
            else None
        )),
        ("expires", lambda c: (
            "expires=%s" % (
                (datetime.utcnow() + timedelta(seconds=c["lifetime"]))
                .strftime("%a, %d-%m-%Y %H:%M:%S UTC")
            )
            if c.get("lifetime")
            else None
        )),
        ("http_only", lambda c: "HttpOnly" if c.get("http_only") else None),
        ("path", lambda c: "path=%s" % c["path"] if c.get("path") else None),
        ("secure", lambda c: "secure" if c.get("secure") else None)
    )

    NO_CONTENT_STATUSES = (204, 304)

    def __init__(self, cookies=None):
        self.body = ""
        self.cookies = cookies or {}
        self.headers = {
            "Content-Type": "text/html"
        }
        self.status = 200

    def finalize(self):
        if self.status in self.NO_CONTENT_STATUSES:
            del self.headers["Content-Type"]
            self.body = ""
        else:
            self.headers["Content-Length"] = str(len(self.body))

        if self.cookies:
            self.headers["Set-Cookie"] = "\n".join(self._serialize_cookies())

        self.headers = [
            (key, value)
            for key, value
            in self.headers.iteritems()
        ]
        if isinstance(self.body, unicode):
            self.body = self.body.encode("utf-8")

    def redirect(self, url, status=302):
        self.status = status
        self.headers["Location"] = url

    def status_code(self):
        return "%d %s" % (self.status, http_responses[self.status])

    def _serialize_cookie(self, name, cookie):
        params = (
            part_formatter(part)
            for part, part_formatter
            in self.COOKIE_PARTS
        )
        cookie_params = "; ".join(filter(None, params))
        return "%s=%s%s" % (
            url_quote(name), url_quote(str(cookie["value"])), cookie_params
        )

    def _serialize_cookies(self):
        for name, cookie in self.cookies.iteritems():
            yield self._serialize_cookie(name, cookie)
