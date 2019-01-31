# coding: utf8

# std
from datetime import date, datetime
from time import gmtime, strftime

# non-std
from dateutil.parser import parse as parse_dt
from jinja2.ext import Extension


DTS = (
    type(datetime.min),
    type(date.min),
)


class TimeExtension(Extension):

    tags = set()

    def __init__(self, environment):
        super(TimeExtension, self).__init__(environment)
        environment.filters.update(self._get_filters())
        environment.globals.update(self._get_functions())

    def as_date(self, date_, format_str=None):
        if isinstance(date_, basestring):
            date_ = parse_dt(date_)

        text = date_.strftime(format_str) if format_str else date_.isoformat()
        if isinstance(text, str):
            text = unicode(text, "utf8")

        return text

    def date_format(self, source, format_str):
        if isinstance(source, basestring):
            obj = (
                datetime.fromtimestamp(float(source))
                if source.isdigit()
                else parse_dt(source)
            )
        elif isinstance(source, (int, float)):
            obj = datetime.fromtimestamp(source)
        elif isinstance(source, DTS):
            obj = source
        else:
            return None

        text = obj.strftime(format_str)
        if isinstance(text, str):
            text = unicode(text, "utf8")

        return text

    def date_now(self):
        return date.today()

    def datetime_now(self):
        return datetime.now()

    def minutes_from_seconds(self, seconds):
        return "%d:%d" % (seconds // 60, seconds % 60)

    def time_from_seconds(self, seconds):
        return strftime("%H:%M:%S", gmtime(seconds))

    def _get_filters(self):
        return {
            "as_date": self.as_date,
            "date_format": self.date_format,
            "mins_from_secs": self.minutes_from_seconds,
            "time_from_secs": self.time_from_seconds
        }

    def _get_functions(self):
        return {
            "date_now": self.date_now,
            "datetime_now": self.datetime_now
        }
