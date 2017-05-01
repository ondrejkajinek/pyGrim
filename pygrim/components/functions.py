# coding: utf-8
from dateutil.parser import parse as parse_dt
import datetime
DTS = (
    type(datetime.datetime.min),
    type(datetime.date.min),
)


def date_format(obj, format_str):
    if isinstance(obj, basestring):
        if obj.isdigit():
            obj = int(obj)
        else:
            obj = parse_dt(obj)
    if isinstance(obj, (int, long)):
        obj = datetime.datetime.strptime(str(obj), "%s")
    elif not isinstance(obj, DTS):
        return None
    return obj.strftime(format_str)
