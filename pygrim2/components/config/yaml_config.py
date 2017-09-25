# coding: utf8

# std
from __future__ import print_function

# non-std
try:
    from uwsgi import log as uwsgi_log
except ImportError:
    uwsgi_log = print

from yaml import load as yaml_load, parser as yaml_parser
from yaml import BaseLoader, MappingNode
from yaml.constructor import ConstructorError

# local
from .abstract_config import AbstractConfig


class PygrimYamlLoader(BaseLoader):

    """
    This reimplements PyYAML loader

    PyYAML loader rewrites values when multiple keys are present in dict.
    PygrimYamlLoader will turn the value into list
    """

    def construct_mapping(self, node, deep=False):
        if not isinstance(node, MappingNode):
            raise ConstructorError(
                None,
                None,
                "expected a mapping node, but found %s" % (
                    node.id, node.start_mark
                )
            )
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError, exc:
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found unacceptable key (%s)" % exc,
                    key_node.start_mark
                )
            value = self.construct_object(value_node, deep=deep)
            if key in mapping:
                if isinstance(mapping[key], list):
                    mapping[key].append(value)
                else:
                    mapping[key] = [mapping[key], value]
            else:
                mapping[key] = value
        return mapping


class YamlConfig(AbstractConfig):

    SEPARATOR = ":"

    def _asdict(self):
        return self.config

    def _load_config(self, path):
        try:
            with open(path, "rb") as conf_in:
                yaml_string = conf_in.read()
                config = yaml_load(yaml_string, Loader=PygrimYamlLoader)
        except yaml_parser.ParserError as exc:
            uwsgi_log("Error when parsing file %r:\n\t%s" % (path, exc))
            config = {}
        except IOError as exc:
            uwsgi_log("Error when loading file %r:\n\t%s" % (path, exc))
            config = {}

        return config
