# std
from datetime import date, datetime, time
from logging import getLogger

# non-std
from dateutil.parser import parse as parse_dt
from jinja2.ext import Extension


DDT = type(datetime.min)
DD = type(date.min)
DT = type(time.min)
DTS = (DDT, DD, DT)

log = getLogger("pygrim.jinja_ext.time_base")


class TimeBase(Extension):

    tags = set()

    def __init__(self, environment):
        super().__init__(environment)
        environment.filters.update(self._get_filters())
        environment.globals.update(self._get_functions())

    def date_format(self, source, format_str=None):
        raise NotImplementedError()

    def date_now(self):
        return date.today()

    def datetime_now(self):
        return datetime.now()

    def minutes_from_seconds(self, seconds):
        return "%02d:%02d" % divmod(seconds, 60)

    def time_format(self, source, format_str):
        raise NotImplementedError()

    def time_from_seconds(self, seconds):
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return "%02d:%02d:%02d" % (hours, minutes, seconds)

    def to_date(self, source):
        return self._parse_date(source)

    def _get_filters(self):
        return {
            "date_format": self.date_format,
            "to_date": self.to_date,
            "mins_from_secs": self.minutes_from_seconds,
            "time_format": self.time_format,
            "time_from_secs": self.time_from_seconds
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

    def _parse_time(self, source):
        if isinstance(source, str):
            obj = parse_dt(source).time()
        elif isinstance(source, DDT):
            obj = source.time()
        elif isinstance(source, DT):
            obj = source
        else:
            obj = None

        return obj
