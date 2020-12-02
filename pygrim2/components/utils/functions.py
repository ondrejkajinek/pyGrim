# std
from collections import Mapping
import logging
import re
from unicodedata import normalize as unicodedata_normalize


log = logging.getLogger("pygrim2.components.utils.functions")


REGEXP_TYPE = type(re.compile(r""))
TRAILING_SLASH_REGEXP = re.compile(r"/\??\$?$|\$?$")

OPTIONAL_PARAM_REGEXP = re.compile(r"\(([^)]*?)(%\(([^)]+)\)s)([^)]*?)\)\?")
PARAM_REGEXP = re.compile(r"\(\?P<([^>]+)>[^)]+\)")


def deep_update(original, override):
    for key, value in override.items():
        if isinstance(value, Mapping):
            new_value = deep_update(original.get(key, {}), value)
            original[key] = new_value
        else:
            original[key] = override[key]

    return original


def ensure_bool(val):
    # Václav Pokluda: is ~25% quicker than isinstance(val, bool)
    if val is True or val is False:
        res = val
    elif val is None:
        res = False
    elif isinstance(val, str):
        res = (
            bool(int(val))
            if val.isdigit()
            else val.lower().strip() == "true"
        )
    else:
        res = bool(val)

    return res


def ensure_tuple(variable):
    if isinstance(variable, tuple):
        res = variable
    elif isinstance(variable, (list, set, memoryview)):
        res = tuple(variable)
    else:
        res = (variable,)

    return res


def fix_trailing_slash(pattern):
    return (
        re.compile(TRAILING_SLASH_REGEXP.sub("/?$", pattern.pattern))
        if is_regex(pattern)
        else pattern.rstrip("/") or "/"
    )


def get_instance_name(instance):
    return get_class_name(instance.__class__)


def get_class_name(cls):
    return "%s.%s" % (cls.__module__, cls.__name__)


def get_method_name(method):
    return "%s.%s" % (method.__self__.__class__.__name__, method.__name__)


def is_regex(pattern):
    return isinstance(pattern, REGEXP_TYPE)


def regex_to_readable(pattern):
    start = 0
    pos = 0
    end = len(pattern)
    group_depth = 0
    readable = ""
    param_names = []
    optional_names = {}
    while pos < end:
        if pattern[pos] == "(":
            if group_depth == 0:
                readable += pattern[start:pos]
                start = pos

            group_depth += 1
        elif pattern[pos] == ")":
            group_depth -= 1
            if group_depth == 0:
                param_name = PARAM_REGEXP.findall(pattern, start, pos + 1)[0]
                param_names.append(param_name)
                if pos + 1 < end and pattern[pos + 1] == "?":
                    optional_readable = PARAM_REGEXP.sub(
                        r"%(\1)s", pattern[start + 1:pos]
                    )
                    optional_names.update((
                        (param_name, "%s%%s%s" % (opt[0], opt[3]))
                        for opt
                        in OPTIONAL_PARAM_REGEXP.findall(optional_readable)
                    ))
                    pos += 1

                readable += "%({})s".format(param_name)
                start = pos + 1

        pos += 1

    # add trailing part
    readable += pattern[start:end]
    required_names = set(
        name
        for name
        in param_names
        if name not in optional_names
    )
    if len(required_names) + len(optional_names) < len(param_names):
        raise RuntimeError(
            "Some keys are duplicate in route %r" % pattern
        )

    return readable, required_names, optional_names



def remove_trailing_slash(pattern):
    return (
        re.compile(TRAILING_SLASH_REGEXP.sub("", pattern.pattern))
        if is_regex(pattern)
        else TRAILING_SLASH_REGEXP.sub("", pattern)
    )


def split_to_iterable(value, separator=","):
    return (
        [part.strip() for part in value.split(separator)]
        if isinstance(value, str)
        else value
    )


def strip_accent(text):
    return "".join(
        c for c in unicodedata_normalize("NFKD", text) if ord(c) < 127
    )
