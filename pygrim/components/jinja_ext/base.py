# coding: utf8

from ..json2 import dumps as json_dumps
from datetime import date, datetime
from dateutil.parser import parse as parse_dt
from jinja2.ext import Extension
from logging import getLogger
from re import compile as re_compile, IGNORECASE as re_IGNORECASE
from os import path

log = getLogger("pygrim.components.jinja_ext.base")

DTS = (
    type(datetime.min),
    type(date.min),
)


class BaseExtension(Extension):

    DASH_SQUEEZER = re_compile("r/-{2,}")
    ENVELOPE_REGEXP = re_compile(r"/envelope/\d+\.jpeg", re_IGNORECASE)
    ENVELOPE_FORMATTER = re_compile(r"\d+")
    SEO_DASHED = (" ", "/", "\\", ":")
    SEO_REMOVED = ("*", "?", "\"", "<", ">", "|", ",")
    SIZE_PREFIXES = ("", "ki", "Mi", "Gi", "Ti")

    tags = set()

    def __init__(self, environment):
        super(BaseExtension, self).__init__(environment)
        environment.filters.update(self._get_filters())
        environment.globals.update(self._get_functions())

    def as_date(self, datum, strf=None):
        if isinstance(datum, basestring):
            datum = parse_dt(datum)

        return datum.strftime(strf)

    def as_json(self, data):
        log.warning("Filter `as_json` is deprecated and will be removed soon.")
        return self.to_json(data)

    def base_url(self, context):
        return "%s%s" % (
            context.get_request_url(), context.get_request_root_uri()
        )

    def date_format(self, source, format_str):
        if isinstance(source, basestring):
            obj = (
                datetime.fromtimestamp(float(source))
                if source.isdigit()
                else parse_dt(source)
            )
        elif isinstance(source, (int, long)):
            obj = datetime.fromtimestamp(source)
        elif isinstance(source, DTS):
            obj = source
        else:
            return None

        return obj.strftime(format_str).decode('utf-8')

    def fit_image(self, path, size=160):
        if not path.startswith("/"):
            path = "//img.mopa.cz/fit,img,%s,;%s" % size, path
        elif self.ENVELOPE_REGEXP.match(path):
            path = self.ENVELOPE_FORMATTER.sub("%s/\g<0>" % size, path)

        return path

    def minutes_from_seconds(self, seconds):
        return "%d:%d" % (seconds // 60, seconds % 60)

    def readable_size(self, size, precision=0):
        index = 0
        while size >= 1024:
            size /= 1024.0
            index += 1

        return ("%%0.%df %%sB" % precision) % (size, self.SIZE_PREFIXES[index])

    def seo(self, text):
        return self.DASH_SQUEEZER.sub(
            "-",
            self._seo_dashize(self._seo_remove(text))
        )

    def site_url(self, context, site):
        return path.join(self.base_url(context), site)

    def to_json(self, value, indent=None):
        return json_dumps(value)

    def _get_filters(self):
        return {
            "as_date": self.as_date,
            "as_json": self.as_json,
            "base_url": self.base_url,
            "date_format": self.date_format,
            "fit_image": self.fit_image,
            "mins_from_secs": self.minutes_from_seconds,
            "readable_size": self.readable_size,
            "seo": self.seo,
            "site_url": self.site_url,
            "tojson": self.to_json
        }

    def _get_functions(self):
        return {
            "base_url": self.base_url,
            "site_url": self.site_url
        }

    def _seo_dashize(self, text):
        return "".join("-" if c in self.SEO_DASHED else c for c in text)

    def _seo_remove(self, text):
        return "".join("" if c in self.SEO_REMOVED else c for c in text)
