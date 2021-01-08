# std
from collections import Mapping
import logging
import re
from unicodedata import normalize as unicodedata_normalize


log = logging.getLogger("pygrim2.components.utils.functions")


REGEXP_TYPE = type(re.compile(r""))
TRAILING_SLASH_REGEXP = re.compile(r"/\??\$?$|\$?$")

# OPTIONAL_PARAM_REGEXP = re.compile(r"\(([^)]*?)(%\(([^)]+)\)s)([^)]*?)\)\?")
# PARAM_REGEXP = re.compile(r"\(\?P<([^>]+)>[^)]+\)")
URL_OPTIONAL_REGEXP = re.compile(r"\(([^)]*?)(%\(([^)]+)\)s)([^)]*?)\)\?")
URL_PARAM_REGEXP = re.compile(r"\(\?P<([^>]+)>[^)]+\)")


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
    if pattern is None:
        return None
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
    if method is None:
        return None
    return "%s.%s" % (method.__self__.__class__.__name__, method.__name__)


def is_regex(pattern):
    return isinstance(pattern, REGEXP_TYPE)


def regex_to_readable(pattern):
    param_names = URL_PARAM_REGEXP.findall(pattern)
    readable = URL_PARAM_REGEXP.sub("%(\\1)s", pattern)
    optional_names = {
        optional[2]: "%s%%s%s" % (optional[0], optional[3])
        for optional
        in URL_OPTIONAL_REGEXP.findall(readable)
    }

    readable = URL_OPTIONAL_REGEXP.sub("\\2", readable)
    readable = remove_trailing_slash(readable).lstrip("^")
    readable = readable.replace("\\.", ".")
    mandatory_names = set(param_names) - set(optional_names)
    if len(mandatory_names) + len(optional_names) < len(param_names):
        raise RuntimeError(f"Some keys are duplicate in route {pattern}")
    return readable, mandatory_names, optional_names


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
