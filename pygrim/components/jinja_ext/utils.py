# coding: utf8

from jinja2.nodes import List, Tuple


def ensure_jinja_iterable(value):
    if isinstance(value, (List, Tuple)):
        result = value
    elif isinstance(value, (tuple, list, range, set)):
        result = List(value)
    else:
        result = List((value,))

    return result
