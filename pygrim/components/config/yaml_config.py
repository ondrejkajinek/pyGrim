# coding: utf8

from __future__ import print_function
from .abstract_config import AbstractConfig
try:
    from uwsgi import log as uwsgi_log
except ImportError:
    uwsgi_log = print

from yaml import load as yaml_load, parser as yaml_parser


class YamlConfig(AbstractConfig):

    SEPARATOR = ":"

    def _load_config(self, path):
        try:
            with open(path, "rb") as conf_in:
                yaml_string = conf_in.read()
                config = yaml_load(yaml_string)
        except yaml_parser.ParserError as exc:
            uwsgi_log("Error when parsing file %r:\n\t%s" % (path, exc))
            config = {}
        except IOError as exc:
            uwsgi_log("Error when loading file %r:\n\t%s" % (path, exc))
            config = {}

        return config
