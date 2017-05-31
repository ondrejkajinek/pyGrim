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

    def _load_config(self, path):
        raise NotImplementedError()
