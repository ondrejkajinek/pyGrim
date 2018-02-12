# coding: utf8

from ..formater import Formater
from ..utils.functions import strip_accent
from ..utils.json2 import dumps as json_dumps
from jinja2.ext import Extension, Markup
from logging import getLogger
from re import compile as re_compile

log = getLogger("pygrim.components.jinja_ext.base")


class BaseExtension(Extension):

    DASH_SQUEEZER = re_compile("r/-{2,}")
    SEO_DASHED = (" ", "/", "\\", ":")
    SEO_REMOVED = ("*", "?", "\"", "<", ">", "|", ",")
    SIZE_PREFIXES = ("", "ki", "Mi", "Gi", "Ti")

    tags = set()

    def __init__(self, environment):
        super(BaseExtension, self).__init__(environment)
        environment.filters.update(self._get_filters())
        environment.globals.update(self._get_functions())
        self.formater = Formater("en_US.UTF8")

    def as_json(self, data):
        log.warning("Filter `as_json` is deprecated and will be removed soon.")
        return self.to_json(data)

    def currency_format(self, amount, currency, locale=None, **kwargs):
        amount, currency, curr_last, sep = self.formater.format_currency(
            amount, currency, locale
        )
        return self._format_currency(
            amount, currency, curr_last, sep, **kwargs
        )

    def currency_int_format(self, amount, currency, locale=None, **kwargs):
        amount, currency, curr_last, sep = self.formater.format_currency_int(
            amount, currency, locale
        )
        return self._format_currency(
            amount, currency, curr_last, sep, **kwargs
        )

    def decimal_format(self, number, precision, locale=None):
        return self.formater.format_decimal(number, precision, locale)

    def fit_image(
        self, path, size=None, proxy=False, width=None, height=None,
        method=None
    ):
        if not size:
            size = 160
        if not width and not height:
            width = size

        width = width or ""
        height = height or ""
        if not path.startswith("/"):
            start = "/" if proxy else "//"
            path = "%simg.grandit.cz/%s,img,%s,%s;%s" % (
                start, method or "fit", width, height, path)

        return path

    def number_format(self, number, locale=None):
        return self.formater.format_number(number, locale)

    def readable_size(self, size, precision=0):
        index = 0
        while size >= 1024:
            size /= 1024.0
            index += 1

        return ("%%0.%df %%sB" % precision) % (size, self.SIZE_PREFIXES[index])

    def safe_title(self, text):
        res = "".join(
            c
            for c
            in strip_accent(text).replace(" ", "_")
            if c.isalnum() or c in "_-.:"
        )
        return res or "_"

    def seo(self, text):
        return self.DASH_SQUEEZER.sub(
            "-",
            self._seo_dashize(self._seo_remove(text))
        )

    def to_json(self, value, indent=None):
        return json_dumps(value)

    def _format_currency(
        self, amount, currency, currency_last, separator, **kwargs
    ):
        if kwargs:
            amount = """<span %s data-sep="%s">%s</span>""" % (
                " ".join(
                    '%s="%s"' % (key, value)
                    for key, value
                    in kwargs.iteritems()
                ),
                separator,
                amount
            )

        params = (
            (amount, currency)
            if currency_last
            else (currency, amount)
        )

        return Markup("%s%s" % params)

    def _get_filters(self):
        return {
            "as_json": self.as_json,
            "fit_image": self.fit_image,
            "readable_size": self.readable_size,
            "safe_title": self.safe_title,
            "seo": self.seo,
            "tojson": self.to_json
        }

    def _get_functions(self):
        return {
            "currency_format": self.currency_format,
            "currency_int_format": self.currency_int_format,
            "decimal_format": self.decimal_format,
            "number_format": self.number_format
        }

    def _seo_dashize(self, text):
        return "".join("-" if c in self.SEO_DASHED else c for c in text or "")

    def _seo_remove(self, text):
        return "".join("" if c in self.SEO_REMOVED else c for c in text or "")
