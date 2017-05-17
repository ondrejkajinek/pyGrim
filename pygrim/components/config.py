# coding: utf8

from collections import Mapping
from copy import deepcopy
from yaml import load as yaml_load, parser as yaml_parser


DEFAULT_CONFIG = {
    "pygrim": {
        "debug": True
    },
    "jinja": {
        "debug": True,
        "dump_switch": "jkxd",
        "environment": {
            "autoescape": ("jinja",)
        },
        "extensions": [],
        "suppress_none": True,
        "template_path": "templates"
    },
    "logging": {
        "file": "/tmp/pygrim.log",
        "level": "DEBUG"
    },
    "session": {
        "enabled": True,
        "type": "file",
        "args": {
            "session_dir": "/tmp/pygrim_session/"
        }
    },
    "view": {
        "enabled": True
    }
}


class ConfigObject(object):

    SEPARATOR = ":"

    def __init__(self, path):
        self.config = self._deep_update(
            deepcopy(DEFAULT_CONFIG), self._load_config(path)
        )

    def get(self, key, *args, **kwargs):
        try:
            target = self.config
            for part in key.split(self.SEPARATOR):
                target = target[part]
        except KeyError as exc:
            try:
                target = self._default_value(*args, **kwargs)
            except:
                raise exc

        return target

    def getfloat(self, key, *args, **kwargs):
        value = self.get(key, *args, **kwargs)
        if not isinstance(value, float):
            try:
                value = self._default_value(*args, **kwargs)
            except:
                raise TypeError("Wrong value for float key: %r" % (key,))

        return value

    def getint(self, key, *args, **kwargs):
        value = self.get(key, *args, **kwargs)
        if not isinstance(value, (int, long)):
            try:
                value = self._default_value(*args, **kwargs)
            except:
                raise TypeError("Wrong value for int key: %r" % (key,))

        return value

    def _deep_update(self, original, override):
        for key, value in override.iteritems():
            if isinstance(value, Mapping):
                new_value = self._deep_update(original.get(key, {}), value)
                original[key] = new_value
            else:
                original[key] = override[key]

        return original

    def _default_value(self, *args, **kwargs):
        try:
            return kwargs.get("default", args[0])
        except IndexError:
            raise RuntimeError("No default value given")

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
