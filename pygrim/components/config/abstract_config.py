# coding: utf8

from ..utils.functions import deep_update
from copy import deepcopy
from logging import getLogger
log = getLogger(__name__)


class NoDefaultValue(Exception):
    pass

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
            except NoDefaultValue:
                raise exc

        return target

    def getfloat(self, key, *args, **kwargs):
        value = self.get(key, *args, **kwargs)
        if not isinstance(value, float):
            try:
                value = self._default_value(*args, **kwargs)
            except NoDefaultValue:
                raise TypeError("Wrong value for float key: %r" % (key,))

        return value

    def getint(self, key, *args, **kwargs):
        value = self.get(key, *args, **kwargs)
        try:
            value = int(value)
        except:
            raise TypeError("Wrong value for int key: %r" % (key,))

        # I do niot understand a purpose of this code
        # if not isinstance(value, (int, long)):
            # try:
                # value = self._default_value(*args, **kwargs)
            # except NoDefaultValue:
                # raise TypeError("Wrong value for int key: %r" % (key,))

        return value

    def _default_value(self, *args, **kwargs):
        """
        there must be this construction because this raises IndexError
            everytime because args[0] is executed before kwargs.get
        try:
            return kwargs.get("default", args[0])
        except IndexError:
            raise RuntimeError("No default value given")
        """

        if args:
            return args[0]
        if "default" in kwargs:
            return kwargs["default"]
        raise NoDefaultValue()

    def _load_config(self, path):
        raise NotImplementedError()
