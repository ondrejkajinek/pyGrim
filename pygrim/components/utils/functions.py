# coding: utf8

from collections import Mapping
from re import compile as re_compile
from unicodedata import normalize as unicodedata_normalize

REGEXP_TYPE = type(re_compile(r""))
TRAILING_SLASH_REGEXP = re_compile("/\??\$?$|\$?$")


def deep_update(original, override):
    for key, value in override.iteritems():
        if isinstance(value, Mapping):
            new_value = deep_update(original.get(key, {}), value)
            original[key] = new_value
        else:
            original[key] = override[key]

    return original


def ensure_bool(a):
    # Václav Pokluda: is ~25% quicker than isinstance(a, bool)
    if a is True or a is False:
        res = a
    elif a is None:
        res = False
    elif isinstance(a, basestring):
        res = (
            int(a)
            if a.isdigit()
            else a.lower().strip() == "true"
        )
    else:
        res = bool(a)

    return res


def ensure_string(text):
    return (
        text.encode("utf8")
        if isinstance(text, unicode)
        else str(text)
    )


def fix_trailing_slash(pattern):
    return (
        re_compile(TRAILING_SLASH_REGEXP.sub("/?$", pattern.pattern))
        if is_regex(pattern)
        else "%s/" % pattern.rstrip("/")
    )


def is_regex(pattern):
    return type(pattern) == REGEXP_TYPE


def remove_trailing_slah(pattern):
    return (
        re_compile(TRAILING_SLASH_REGEXP.sub("", pattern.pattern))
        if is_regex(pattern)
        else TRAILING_SLASH_REGEXP.sub("", pattern)
    )


def strip_accent(text):
    if isinstance(text, str):
        text = unicode(text, "utf8")

    return "".join(
        c for c in unicodedata_normalize("NFKD", text) if ord(c) < 127
    )
