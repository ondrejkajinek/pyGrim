# std
from datetime import datetime, timedelta
from inspect import isgenerator, isgeneratorfunction
from logging import getLogger
from urllib.parse import quote_plus as url_quoteplus

# local
from ..components.containers import NormalizedDict

log = getLogger("pygrim.http.response")


NO_CONTENT_STATUSES = (204, 304)


def ensure_bytes(value):
    return (
        value.encode("utf-8")
        if isinstance(value, str)
        else bytes(value) if value else value
    )


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

    def __init__(self):
        self.cookies = {}
        self.headers = NormalizedDict((
            ("Content-Type", "text/html"),
        ))
        self.status = 200
        self.body = b""

    @property
    def body(self):
        return self._body

    @body.setter
    def body(self, body):
        is_generator = False
        if body is None:
            body = b""
            self.headers.pop("Content-Length", None)
        elif isinstance(body, bytes):
            pass
        elif isinstance(body, str):
            body = body.encode("utf-8")
        elif isgeneratorfunction(body):
            body = (ensure_bytes(part) for part in body())
            is_generator = True
        elif isgenerator(body):
            body = (ensure_bytes(part) for part in body)
            is_generator = True
        else:
            try:
                body.seek(0)
                body = ensure_bytes(body.read())
            except AttributeError:
                body = b""
                log.critical("Cannot read value from given body content")
                log.exception("Cannot read value from given body content")

        if body and not is_generator:
            self.headers["Content-Length"] = len(body)
        else:
            self.headers.pop("Content-Length", None)

        self.is_generator = is_generator
        self._body = body

    def finalize(self, is_head):
        if self.status in NO_CONTENT_STATUSES:
            self.body = None

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
