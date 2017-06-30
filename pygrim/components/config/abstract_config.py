# coding: utf8

from .default import DEFAULT_CONFIG
from ..utils.functions import deep_update, ensure_bool, split_to_iterable

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

    def getset(self, key, *args, **kwargs):
        return self._get_typed(
            lambda x: set(split_to_iterable(x)), key, *args, **kwargs
        )

    def gettuple(self, key, *args, **kwargs):
        return self._get_typed(
            lambda x: tuple(split_to_iterable(x)), key, *args, **kwargs
        )

    def _default_value(self, *args, **kwargs):
        if "default" in kwargs:
            value = kwargs["default"]
        elif args:
            value = args[0]
        else:
            raise NoDefaultValue()

        return value

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
