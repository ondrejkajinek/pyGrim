# coding: utf8

# from compatibility import http_responses
from datetime import datetime, timedelta
from logging import getLogger
from urllib import quote_plus as url_quoteplus

log = getLogger("pygrim.http.response")

import os


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
        self.cookies = {}
        self.headers = {
            "Content-Type": "text/html"
        }
        self.status = 200

    def finalize(self):
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

        if self.cookies:
            for cookie in self._serialized_cookies():
                self.headers.append(("Set-Cookie", cookie))

    def redirect(self, url, status=302):
        self.status = status
        self.headers["Location"] = url

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
        for name, cookie in self.cookies.iteritems():
            yield self._serialize_cookie(name, cookie)
