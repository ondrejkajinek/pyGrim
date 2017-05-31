# coding: utf8

from ..utils.functions import deep_update
from copy import deepcopy

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
        "enabled": True,
        "type": "jinja"
    }
}


class AbstractConfig(object):

    SEPARATOR = None

    def __init__(self, path):
        self.config = deep_update(
            deepcopy(DEFAULT_CONFIG), self._load_config(path)
        )

    def get(self, key, *args, **kwargs):
        try:
            target = self.config
            if self.SEPARATOR is not None:
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

    def _default_value(self, *args, **kwargs):
        try:
            return kwargs.get("default", args[0])
        except IndexError:
            raise RuntimeError("No default value given")

    def _load_config(self, path):
        raise NotImplementedError()
