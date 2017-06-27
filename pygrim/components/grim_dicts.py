# coding: utf8

from logging import getLogger

log = getLogger("pygrim.http.grim_dicts")


class AttributeDict(dict):

    def __init__(self, *args, **kwargs):
        super(AttributeDict, self).__init__(*args, **kwargs)

    def __getattr__(self, key):
        try:
            return self.__getitem__(key)
        except KeyError as exc:
            raise AttributeError(exc)


class ImmutableDict(dict):

    def __init__(self, *args, **kwargs):
        super(ImmutableDict, self).__init__(*args, **kwargs)

    def __hash__(self):
        return id(self)

    def _immutable(self, *args, **kwargs):
        raise TypeError("object is immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    update = _immutable
    setdefault = _immutable
    pop = _immutable
    popitem = _immutable


class NormalizedDict(dict):

    def __init__(self, *args, **kwargs):
        super(NormalizedDict, self).__init__((
            (self._normalize_key(key), value)
            for key, value
            in dict(*args, **kwargs).iteritems()
        ))

    def __missing__(self, key):
        """
        raises KeyError when normalized key is not found
        """
        normalized = self._normalize_key(key)
        if normalized not in self:
            raise KeyError(key)

        return self[normalized]

    def __setitem__(self, key, value):
        super(NormalizedDict, self).__setitem__(
            self._normalize_key(key), value
        )

    def __delitem__(self, key):
        super(NormalizedDict, self).__delitem__(self._normalize_key(key))

    def pop(self, key, *args, **kwargs):
        try:
            value = super(NormalizedDict, self).pop(self._normalize_key(key))
        except:
            if "default" in kwargs:
                value = kwargs["default"]
            elif args:
                value = args[0]
            else:
                raise

        return value

    def setdefault(self, key, default=None):
        return super(NormalizedDict, self).setdefault(
            self._normalize_key(key), default
        )

    def update(self, other=None):
        iterator = (
            other.iteritems()
            if isinstance(other, dict)
            else other or ()
        )
        for key, value in iterator:
            self.__setitem__(key, value)

    def get(self, key, default=None):
        return super(NormalizedDict, self).get(
            self._normalize_key(key), default
        )

    def _normalize_key(self, key):
        normalized = key.lower().replace("_", "-")
        if normalized.startswith("http-"):
            normalized = normalized[5:]

        return normalized


class NormalizedImmutableDict(ImmutableDict, NormalizedDict):

    def __init__(self, *args, **kwargs):
        super(NormalizedImmutableDict, self).__init__(*args, **kwargs)
