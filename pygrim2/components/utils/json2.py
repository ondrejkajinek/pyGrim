# coding: utf8

# std
from collections import Iterable
from cStringIO import StringIO
from datetime import date, datetime, timedelta
from decimal import Decimal
from types import GeneratorType
from unicodedata import normalize as unicodedata_normalize
from uuid import UUID

# import everything from json to current namespace,
# redefine functions as required
from json import *

# local
from .functions import ensure_string

# JSON does not support these values, so we mark them as invalid
InvalidJsonFloatValues = tuple(float(inv) for inv in ("inf", "-inf", "NaN"))

"""
TODO: translate
Jaký je rozdíl mezi reálným číslem a ženou?
Reálné číslo s periodou je racionální.
"""


def _dump_boolean(source):
    return "true" if source is True else "false"


def _dump_datetime(source):
    return '"%s"' % source.isoformat()


def _dump_dict(source, nice, depth):
    separator = ","
    indent_step = "    "
    if nice:
        indent = depth * indent_step
        nl = "\n"
    else:
        indent = ""
        nl = ""

    lead = "{"
    ind = ""
    trail = "}"
    if nice:
        separator += nl
        lead += nl
        ind += indent + indent_step
        trail = nl + indent + trail

    ind += '%s:%s'
    items = (
        ind % (
            _dumps(ensure_string(key), nice=nice, depth=depth),
            _dumps(value, nice=nice, depth=depth + 1)
        )
        for key, value
        in source.items()
    )

    return "%s%s%s" % (lead, separator.join(items), trail)


def _dump_iterable(source, nice, depth):
    glue = ", " if nice else ","
    return "[%s]" % glue.join(
        _dumps(i, nice=nice, depth=depth) for i in source
    )


def _dump_none():
    return "null"


def _dump_number(source):
    if source in InvalidJsonFloatValues:
        raise TypeError("JSON can't contain float with value: %s" % source)

    return str(source)


def _dump_string(source):
    return _dump_unicode(source.decode("utf8"))


def _dump_timedelta(source):
    return '"%s"' % source.total_seconds()


def _dump_unicode(source):
    norm = unicodedata_normalize("NFC", source)
    norm = norm.replace('\\', '\\\\')
    norm = norm.replace('\x1F', "")  # ^_ - Unit separator
    norm = norm.replace('\x07', "")  # ^G - Bell, rings the bell...
    norm = "".join(
        ch if ord(ch) < 128 else "\u%04x" % ord(ch)
        for ch
        in norm
    )
    norm = norm.replace('"', '\\"')
    norm = norm.replace('\n', '\\n')
    norm = norm.replace("\r", "")
    norm = norm.replace("\t", "")
    norm = norm.replace(chr(7), "")
    return '"%s"' % norm.encode("utf8")


def _dump_uuid(source):
    return '"%s"' % (str(source),)


def _dumps(obj, nice=None, depth=0):
    output = StringIO()
    if obj is None:
        output.write(_dump_none())
    elif isinstance(obj, str):
        output.write(_dump_string(obj))
    elif isinstance(obj, unicode):
        output.write(_dump_unicode(obj))
    elif isinstance(obj, bool):
        output.write(_dump_boolean(obj))
    elif isinstance(obj, (Decimal, float)):
        output.write(_dump_number(float(obj)))
    elif isinstance(obj, (int, long)):
        output.write(_dump_number(obj))
    elif isinstance(obj, dict):
        output.write(_dump_dict(obj, nice, depth))
    # must be after str and unicode, since these are also iterable
    elif isinstance(obj, (GeneratorType, Iterable)):
        output.write(_dump_iterable(obj, nice, depth))
    elif isinstance(obj, UUID):
        output.write(_dump_uuid(obj))
    elif isinstance(obj, (datetime, date)):
        output.write(_dump_datetime(obj))
    elif isinstance(obj, timedelta):
        output.write(_dump_timedelta(obj))
    elif hasattr(obj, "_asdict"):
        output.write(_dump_dict(obj._asdict(), nice, depth))
    elif hasattr(obj, "toJson"):
        output.write(obj.toJson(func=_dumps, nice=nice, depth=depth))
    else:
        raise TypeError(type(obj), dir(obj), repr(obj))

    res = output.getvalue()
    output.close()
    return res


def dumps2(obj, nice=None, depth=0):
    return _dumps(obj, nice, depth)


def dumps2fd(obj, fd=None, nice=None, depth=0):
    fd.write(_dumps(obj, nice, depth))


dumps = dumps2


if __name__ == "__main__":
    test = {
        datetime.now(): set((5, 4, "ADSF")),
        2345234: ("a", "b"),
        "asdf": [dict(x=1)],
        "d": datetime.now(),
        "B": [False, True],
        "NNNNNNNNNNNNNNN": None,
        "FL": (2.0 / 3, 0.0),
        "Uvozovky": "'`\"",
    }
    print test
    print
    print dumps2(test)
    print dumps2(test, nice=True)
    print loads(dumps2(test))
