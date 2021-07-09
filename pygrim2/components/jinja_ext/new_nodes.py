# coding: utf8

from jinja2.nodes import Extends, NodeType


def orig_node_new(cls, name, bases, d):
    for attr in 'fields', 'attributes':
        storage = []
        storage.extend(getattr(bases[0], attr, ()))
        storage.extend(d.get(attr, ()))
        assert len(bases) == 1, 'multiple inheritance not allowed'
        assert len(storage) == len(set(storage)), 'layout conflict'
        d[attr] = tuple(storage)
    d.setdefault('abstract', False)
    return type.__new__(cls, name, bases, d)


jinja_node_new = NodeType.__new__
NodeType.__new__ = staticmethod(orig_node_new)


class PrefixExtends(Extends):
    pass


NodeType.__new__ = jinja_node_new
