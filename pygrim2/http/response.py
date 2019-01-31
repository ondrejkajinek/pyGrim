# coding: utf8

# std
from datetime import datetime, timedelta
from inspect import isgenerator, isgeneratorfunction
from logging import getLogger
from os import SEEK_END
from urllib import quote_plus as url_quoteplus

# local
from ..components.containers import NormalizedDict

log = getLogger("pygrim.http.response")


class Response(object):

    COOKIE_PARTS = (
        lambda c: "Domain=%s" % c["domain"] if c.get("domain") else None,
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
        self.headers = NormalizedDict((
            ("Content-Type", "text/html"),
        ))
        self.status = 200

    def finalize(self, is_head):
        if self.status in self.NO_CONTENT_STATUSES:
            del self.headers["Content-Type"]
            self.body = ""
        else:
            if isinstance(self.body, bytes):
                self.headers["Content-Length"] = len(self.body)
                if is_head:
                    self.body = ""
            elif isgenerator(self.body):
                pass
                # do not set body to None when is_head
                # we want to iterate over body to see if no error occur
            else:
                if "Content-Length" not in self.headers:
                    if (
                        hasattr(self.body, "seek") and
                        hasattr(self.body, "tell")
                    ):
                        self.body.seek(0, SEEK_END)
                        self.headers["Content-Length"] = self.body.tell()
                    else:
                        log.warning(
                            "Unable to get Content-Length for type %r",
                            type(self.body)
                        )

                if is_head:
                    self.body = ""
                else:
                    try:
                        self.body.seek(0)
                        self.body = self.body.read()
                    except AttributeError:
                        log.critical("Can't read read response body content!")
                        log.exception("Can't read read response body content!")

    def serialized_headers(self):
        serialized = [
            (key, str(value))
            for key, value
            in self.headers.items()
        ]
        serialized.extend((
            ("Set-Cookie", cookie)
            for cookie
            in self._serialized_cookies()
        ))
        return serialized

    def set_body(self, body):
        if isgeneratorfunction(body):
            self.body = body()
        elif isinstance(body, str):
            self.body = body.encode("utf-8")
        else:
            self.body = body

    def _serialize_cookie(self, name, cookie):
        params = (
            part_formatter(cookie)
            for part_formatter
            in self.COOKIE_PARTS
        )
        cookie_params = "; ".join(filter(None, params))
        return str("%s=%s%s" % (
            url_quoteplus(name),
            url_quoteplus(str(cookie["value"])),
            (
                "; %s" % cookie_params
                if cookie_params
                else ""
            )
        ))

    def _serialized_cookies(self):
        for name, cookie in self.cookies.items():
            yield self._serialize_cookie(name, cookie)
