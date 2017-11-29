# coding: utf8

from ..utils.functions import deep_update, ensure_bool
from copy import deepcopy


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

    def __init__(self, path, default=None):
        if default is None:
            default = DEFAULT_CONFIG

        self.config = deep_update(
            deepcopy(default), self._load_config(path)
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
        return self._get_typed(float, key, *args, **kwargs)

    def getint(self, key, *args, **kwargs):
        return self._get_typed(int, key, *args, **kwargs)

    def getbool(self, key, *args, **kwargs):
        return self._get_typed(ensure_bool, key, *args, **kwargs)

    getboolean = getbool

    def _asdict(self):
        raise NotImplementedError()

    def _default_value(self, *args, **kwargs):
        """
        there must be this construction because this raises IndexError
            everytime because args[0] is executed before kwargs.get
        try:
            return kwargs.get("default", args[0])
        except IndexError:
            raise RuntimeError("No default value given")
        """

        if "default" in kwargs:
            return kwargs["default"]
        if args:
            return args[0]
        raise NoDefaultValue()

    def _get_typed(self, construct, key, *args, **kwargs):
        value = self.get(key, *args, **kwargs)
        try:
            return construct(value)
        except ValueError:
            raise TypeError(
                "Wrong value %r for %r key: %r" % (value, construct, key)
            )

    def _load_config(self, path):
        raise NotImplementedError()
