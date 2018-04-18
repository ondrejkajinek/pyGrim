# coding: utf8

# std
from __future__ import print_function
from json import loads as json_loads

# non-std
try:
    from uwsgi import log as uwsgi_log
except ImportError:
    uwsgi_log = print

# local
from .abstract_config import AbstractConfig


class JsonConfig(AbstractConfig):

    SEPARATOR = ":"

    def _load_config(self, path):
        try:
            with open(path, "rb") as conf_in:
                json_string = conf_in.read()
                config = json_loads(json_string)
        except ValueError as exc:
            uwsgi_log("Error when parsing file %r:\n\t%s" % (path, exc))
            config = {}
        except IOError as exc:
            uwsgi_log("Error when loading file %r:\n\t%s" % (path, exc))
            config = {}

        return config
