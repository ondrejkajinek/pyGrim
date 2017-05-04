#!/usr/bin/python
# -*- coding: utf-8 -*-


import datetime
# tenhle import mi do namespace da vsechno potrebne ja vlastne
#   jen predefinuji funkci dumps
from json import *
import uuid


# TODO SJEDNOTIT IPMLEMENTACI dpmps2 a dumps2fd pres StringIO

import types
import unicodedata
from decimal import Decimal
import collections

# JSON nepodporuje tyto hodnoty je treba to osetrit nejak u nas
Infinity = float("inf")
NegInfinity = float("-inf")
NaN = float("NaN")
"""
Jaký je rozdíl mezi reálným číslem a ženou?
Reálné číslo s periodou je racionální.
"""

InvalidJsonFloatTypes = (Infinity, NegInfinity, NaN)


def dumps2(obj, nice=None, depth=0):
    separator = ","
    indent = ""
    indent_step = "    "
    nl = ""
    if nice:
        indent = depth * indent_step
        nl = "\n"

    if isinstance(obj, str):
        obj = obj.decode("utf8")
    if isinstance(obj, unicode):
        norm = unicodedata.normalize("NFC", obj)
        norm = norm.replace('\\', '\\\\')
        norm = norm.replace('\x1F', "")  # ^_ - Unit separator
        norm = norm.replace('\x07', "")  # ^G - Bell, rings the bell...
        norm = "".join([
            ch if ord(ch) < 128 else "\u%04x" % ord(ch)
            for ch in norm
        ])
        norm = norm.replace('"', '\\"')
        norm = norm.replace('\n', '\\n')
        norm = norm.replace("\r", "")
        norm = norm.replace("\t", "")
        norm = norm.replace(chr(7), "")
        return '"%s"' % norm.encode("utf8")
    if isinstance(obj, bool):
        return "true" if obj is True else "false"
    if isinstance(obj, Decimal):
        obj = float(obj)  # no jo no, mas lepsi reseni?
    if isinstance(obj, float):
        if obj in InvalidJsonFloatTypes:
            raise TypeError(
                "JSON nemuze obsahovat float s hodnotou: %s" % obj)
        return str(obj)
    if isinstance(obj, (int, float, long)):
        return str(obj)
    if hasattr(obj, "_asdict"):
        # je to hnus velebnosti takle pres hasattr, ale je to blby
        obj = obj._asdict()
    #    # nic se nevraci, chceme jen split nasledujici podminku
    if isinstance(obj, dict):
        # pro prehlednost:
        sep = separator
        lead = "{"
        ind = ""
        trail = "}"
        if nice:
            sep += nl
            lead += nl
            ind += indent+indent_step
            trail = nl + indent + trail
        # endif nice
        ind += '"%s":%s'
        items = []
        for k, v in obj.iteritems():
            if isinstance(k, unicode):
                k = k.encode("utf8")
            else:
                k = str(k)
            # endif
            items.append(ind % (k, dumps2(v, nice=nice, depth=depth+1)))
        # endfor
        return lead + sep.join(items) + trail
    if isinstance(obj, (
            list, tuple, set, types.GeneratorType,
            collections.Iterable)):
        return "[" + separator.join(
            dumps2(i, nice=nice, depth=depth) for i in obj
            ) + "]"
    if isinstance(obj, uuid.UUID):
        return '"%s"' % (str(obj),)
    if obj is None:
        return "null"
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return '"%s"' % obj.isoformat()
    if hasattr(obj, "toJson"):
        return obj.toJson(func=dumps2, nice=nice, depth=depth)
    if isinstance(obj, datetime.timedelta):
        return '"%s"' % obj.total_seconds()
    raise TypeError(type(obj), dir(obj), repr(obj))
# enddef dumps2


def dumps2fd(obj, fd=None, nice=None, depth=0):
    separator = ","
    indent = ""
    indent_step = "    "
    nl = ""
    if nice:
        indent = depth * indent_step
        nl = "\n"

    if isinstance(obj, str):
        obj = obj.decode("utf8")
    if isinstance(obj, unicode):
        norm = unicodedata.normalize("NFC", obj)
        norm = norm.replace('\\', '\\\\')
        norm = norm.replace('\x1F', "")  # ^_ - Unit separator
        norm = norm.replace('\x07', "")  # ^G - Bell, rings the bell...
        norm = "".join([
            ch if ord(ch) < 128 else "\u%04x" % ord(ch)
            for ch in norm
        ])
        norm = norm.replace('"', '\\"')
        norm = norm.replace('\n', '\\n')
        norm = norm.replace("\r", "")
        norm = norm.replace("\t", "")
        norm = norm.replace(chr(7), "")
        fd.write('"%s"' % norm.encode("utf8"))
        return
    if isinstance(obj, bool):
        fd.write("true" if obj is True else "false")
        return
    if isinstance(obj, Decimal):
        obj = float(obj)  # no jo no, mas lepsi reseni?
    if isinstance(obj, float):
        if obj in InvalidJsonFloatTypes:
            raise TypeError(
                "JSON nemuze obsahovat float s hodnotou: %s" % obj)
        fd.write(str(obj))
        return
    if (
            isinstance(obj, int) or
            isinstance(obj, float) or
            isinstance(obj, long)):
        fd.write(str(obj))
        return
    if isinstance(obj, tuple) and hasattr(obj, "_asdict"):
        # je to hnus velebnosti takle pres hasattr, ale je to blby
        obj = obj._asdict()
    #    # nic se nevraci, chceme jen split nasledujici podminku
    if isinstance(obj, dict):
        # pro prehlednost:
        sep = separator
        lead = "{"
        ind = ""
        trail = "}"
        if nice:
            sep += nl
            lead += nl
            ind += indent+indent_step
            trail = nl + indent + trail
        # endif nice
        ind += '"%s":%s'

        fd.write(lead)

        first = True
        for k, v in obj.iteritems():
            if not first:
                fd.write(sep)
            if isinstance(k, unicode):
                k = k.encode("utf8")
            else:
                k = str(k)
            fd.write('"%s":' % k)
            for part in dumps2fd(v, fd, nice=nice, depth=depth+1):
                fd.write(part)
            first = False
        fd.write(trail)

    if (
            isinstance(obj, list) or
            isinstance(obj, tuple) or
            isinstance(obj, set) or
            isinstance(obj, types.GeneratorType)
            ):
        fd.write("[")
        first = True
        for part in obj:
            if not first:
                fd.write(", ")
            fd.write(dumps2fd(part, fd, nice=nice, depth=depth))
        fd.write("]")
        return
    if isinstance(obj, uuid.UUID):
        fd.write(str(obj))
        return
    if obj is None:
        fd.write("null")
        return
    if isinstance(obj, datetime.datetime) or isinstance(obj, datetime.date):
        fd.write('"%s"' % obj.isoformat())
        return
    if hasattr(obj, "toJson"):
        fd.write(obj.toJson(func=dumps2, nice=nice, depth=depth))
        return
    if isinstance(obj, datetime.timedelta):
        fd.write('"%s"' % obj.total_seconds())
        return
    raise TypeError(type(obj), dir(obj))
# enddef dumps2

dumps = dumps2

if __name__ == "__main__":
    test = {
        datetime.datetime.now(): set([5, 4, "ADSF"]),
        2345234: ("a", "b"),
        "asdf": [dict(x=1)],
        "d": datetime.datetime.now(),
        "B": [False, True],
        "NNNNNNNNNNNNNNN": None,
        "FL": (float(2)/3, 0.0),
        "Uvozovky": "'`\"",
    }
    print test
    print
    print dumps2(test)
    print dumps2(test, nice=True)
