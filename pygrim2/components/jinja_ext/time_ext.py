# std
from datetime import date, datetime

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
        """
        This filter is deprecated and will be removed in the future
        Use date_format instead
        """
        if isinstance(date_, str):
            date_ = parse_dt(date_)

        return date_.strftime(format_str) if format_str else date_.isoformat()

    def date_format(self, source, format_str=None):
        obj = self._parse_date(source)
        return (
            obj.strftime(format_str) if format_str else obj.isoformat()
            if obj
            else None
        )

    def date_now(self):
        return date.today()

    def datetime_now(self):
        return datetime.now()

    def minutes_from_seconds(self, seconds):
        return "%02d:%02d" % divmod(seconds, 60)

    def time_from_seconds(self, seconds):
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return "%02d:%02d:%02d" % (hours, minutes, seconds)

    def to_date(self, source):
        return self._parse_date(source)

    def _get_filters(self):
        return {
            "as_date": self.as_date,
            "date_format": self.date_format,
            "mins_from_secs": self.minutes_from_seconds,
            "time_from_secs": self.time_from_seconds,
            "to_date": self.to_date
        }

    def _get_functions(self):
        return {
            "date_now": self.date_now,
            "datetime_now": self.datetime_now
        }

    def _parse_date(self, source):
        if isinstance(source, str):
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
            obj = None

        return obj
