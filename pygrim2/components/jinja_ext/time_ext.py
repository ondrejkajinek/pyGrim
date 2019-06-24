# non-std
from dateutil.parser import parse as parse_dt

# local
from .time_base import TimeBase


class TimeExtension(TimeBase):

    tags = set()

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

    def time_format(self, source, format_str):
        obj = self._parse_time(source)
        return obj.strftime(format_str) if obj else None

    def _get_filters(self):
        filters = super()._get_filters()
        filters.update({
            "as_date": self.as_date
        })
        return filters
