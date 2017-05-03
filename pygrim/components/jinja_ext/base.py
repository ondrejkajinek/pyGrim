# coding: utf8

from datetime import date, datetime
from dateutil.parser import parse as parse_dt
from jinja2.ext import Extension
from json import dumps as json_dumps
from os import path

DTS = (
    type(datetime.min),
    type(date.min),
)


class BaseExtension(Extension):

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
        return json_dumps(data)

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

    def site_url(self, context, site):
        return path.join(self.base_url(context), site)

    def _get_filters(self):
        return {
            "as_date": self.as_date,
            "as_json": self.as_json,
            "base_url": self.base_url,
            "date_format": self.date_format,
            "site_url": self.site_url,
        }

    def _get_functions(self):
        return {
            "base_url": self.base_url,
            "site_url": self.site_url
        }
