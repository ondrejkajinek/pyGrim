# coding: utf8

from jinja2.nodes import Tuple


def ensure_jinja_tuple(value):
    if isinstance(value, Tuple):
        result = value.items
    else:
        result = (value,)

    return result
