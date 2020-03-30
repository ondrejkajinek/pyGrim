# coding: utf8

from datetime import datetime, timedelta
from inspect import isgeneratorfunction
from logging import getLogger
# from os import SEEK_END
from urllib import quote_plus as url_quoteplus
from locale import getlocale, LC_ALL
import types

log = getLogger("pygrim.http.response")


NO_CONTENT_STATUSES = (204, 304)


def ensure_string(value):
    return (
        value.encode("utf-8")
        if isinstance(value, unicode)
        else str(value) if value else value
    )


class Response(object):

    COOKIE_PARTS = (
        lambda c: (
            "Domain=%s" % c["domain"]
            if c.get("domain")
            else None
        ),
        lambda c: "Lang=%s" % (getlocale(LC_ALL)[0] or "",),
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
        lambda c: (
            "Secure"
            if (
                c.get("secure") or
                (c.get("same_site") or "").lower() == "none"
            )
            else None
        ),
        lambda c: "SameSite=%s" % (c.get("same_site") or "Lax"),
    )

    COOKIE_PARTS_LEGACY = (
        lambda c: (
            "Domain=%s" % c["domain"]
            if c.get("domain")
            else None
        ),
        lambda c: "Lang=%s" % (getlocale(LC_ALL)[0] or "",),
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
        lambda c: "Secure" if c.get("secure") else None,
    )

    def __init__(self):
        self._body = ""
        self.cookies = {}
        self.headers = {
            "Content-Type": "text/html"
        }
        self.status = 200
        self.is_generator = False
        self.is_generator_function = False

    @property
    def body(self):
        return self._body

    @body.setter
    def body(self, body):
        is_generator = False
        if body is None:
            body = ""
        elif isinstance(body, str):
            pass
        elif isinstance(body, unicode):
            body = body.encode("utf-8")
        elif isinstance(body, types.GeneratorType):
            body = (ensure_string(part) for part in body)
            is_generator = True
        elif isgeneratorfunction(body):
            body = (ensure_string(part) for part in body())
            is_generator = True
        else:
            try:
                body.seek(0)
                body = body.read()
            except AttributeError:
                body = ""
                log.critical("Cannot read value from given body content!")
                log.exception("Cannot read value from given body content!")

        if body and not is_generator:
            self.headers["Content-Length"] = len(body)
        else:
            self.headers.pop("Content-Length", None)

        self.is_generator = is_generator
        self._body = body

    def finalize(self):
        if self.status in NO_CONTENT_STATUSES:
            self.body = None

        self.headers = [
            (key, str(value))
            for key, value
            in self.headers.iteritems()
        ]

        if self.cookies:
            for cookie in self._serialized_cookies():
                self.headers.append(("Set-Cookie", cookie))

    def _serialize_cookie(self, name, cookie):
        # ensure cookie values:
        params = (
            ensure_string(part_formatter(cookie))
            for part_formatter
            in self.COOKIE_PARTS
        )
        cookie_params = "; ".join(param for param in params if param)

        name_part = url_quoteplus(name)
        value_part = url_quoteplus(str(cookie["value"]))
        params_part = "; {}".format(cookie_params)
        return "{}={}{}".format(name_part, value_part, params_part)

    def _serialize_cookie_legacy(self, name, cookie):
        if cookie.get("same_site") not in (None, "None"):
            return None

        # ensure cookie values:
        params = (
            ensure_string(part_formatter(cookie))
            for part_formatter
            in self.COOKIE_PARTS_LEGACY
        )
        cookie_params = "; ".join(param for param in params if param)

        name_part = url_quoteplus(name + "-legacy")
        value_part = url_quoteplus(str(cookie["value"]))
        params_part = "; {}".format(cookie_params)
        return "{}={}{}".format(name_part, value_part, params_part)

    def _serialized_cookies(self):
        for name, cookie in self.cookies.iteritems():
            yield self._serialize_cookie(name, cookie)
            leg_cookie = self._serialize_cookie_legacy(name, cookie)
            if leg_cookie:
                yield leg_cookie
