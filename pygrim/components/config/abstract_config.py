# coding: utf8

from collections import Mapping
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
        self.config = self._deep_update(
            deepcopy(DEFAULT_CONFIG), self._load_config(path)
        )

    def _deep_update(self, original, override):
        for key, value in override.iteritems():
            if isinstance(value, Mapping):
                new_value = self._deep_update(original.get(key, {}), value)
                original[key] = new_value
            else:
                original[key] = override[key]

        return original

    def _load_config(self, path):
        raise NotImplementedError()
