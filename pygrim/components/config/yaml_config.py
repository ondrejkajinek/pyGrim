# coding: utf8

from .abstract_config import AbstractConfig
from yaml import load as yaml_load, parser as yaml_parser


class YamlConfig(AbstractConfig):

    SEPARATOR = ":"

    def _load_config(self, path):
        try:
            with open(path, "rb") as conf_in:
                yaml_string = conf_in.read()
                config = yaml_load(yaml_string)
        except yaml_parser.ParserError as exc:
            print("Error when parsing file %r:\n%s" % (path, exc))
            config = {}
        except IOError as exc:
            print("Error when loading file %r:\n%s" % (path, exc))
            config = {}

        return config
