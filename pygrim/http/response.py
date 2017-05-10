# coding: utf8

# from compatibility import http_responses
from datetime import datetime, timedelta
from inspect import isgeneratorfunction
from logging import getLogger
from os import SEEK_END
from urllib import quote_plus as url_quoteplus

log = getLogger("pygrim.http.response")


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
        self.is_generator_function = False

    def finalize(self):
        if self.status in self.NO_CONTENT_STATUSES:
            del self.headers["Content-Type"]
            self.body = ""
        else:
            if isinstance(self.body, unicode):
                self.body = self.body.encode("utf-8")

            if isinstance(self.body, str):
                self.headers["Content-Length"] = len(self.body)
            elif isgeneratorfunction(self.body):
                self.is_generator_function = True
            else:
                if (
                    "Content-Length" not in self.headers and
                    hasattr(self.body, "seek") and
                    hasattr(self.body, "tell")
                ):
                    self.body.seek(0, SEEK_END)
                    self.headers["Content-Length"] = self.body.tell()
                    self.body.seek(0)
                else:
                    log.warning(
                        "Unable to get Content-Length for type %r",
                        type(self.body)
                    )

                try:
                    self.body = self.body.read()
                except AttributeError:
                    log.critical("Can't read read response body content!")
                    log.exception("Can't read read response body content!")

        self.headers = [
            (key, str(value))
            for key, value
            in self.headers.iteritems()
        ]

        if self.cookies:
            for cookie in self._serialized_cookies():
                self.headers.append(("Set-Cookie", cookie))

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
