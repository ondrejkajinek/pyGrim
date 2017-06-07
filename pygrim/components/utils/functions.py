# coding: utf8

from collections import Mapping
from re import compile as re_compile

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


def ensure_string(text):
    return (
        text.encode("utf8")
        if isinstance(text, unicode)
        else str(text)
    )


def ensure_tuple(variable):
    if not isinstance(variable, tuple):
        variable = (variable, )

    return variable


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
