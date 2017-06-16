# coding: utf8

from .default import DEFAULT_CONFIG
from ..utils.functions import deep_update, ensure_bool, ensure_tuple
from copy import deepcopy
from logging import getLogger
log = getLogger(__name__)


class NoDefaultValue(Exception):
    pass


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

    def getbool(self, key, *args, **kwargs):
        return self._get_typed(ensure_bool, key, *args, **kwargs)

    getboolean = getbool

    def getfloat(self, key, *args, **kwargs):
        return self._get_typed(float, key, *args, **kwargs)

    def getint(self, key, *args, **kwargs):
        return self._get_typed(int, key, *args, **kwargs)

    def gettuple(self, key, *args, **kwargs):
        return self._get_typed(ensure_tuple, key, *args, **kwargs)

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
