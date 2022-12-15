# coding: utf8

from logging import getLogger

log = getLogger("pygrim.http.grim_dicts")


class ImmutableDict(dict):

    def __hash__(self):
        return id(self)

    def _immutable(self, *args, **kws):
        raise TypeError("object is immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    update = _immutable
    setdefault = _immutable
    pop = _immutable
    popitem = _immutable


class NormalizedImmutableDict(ImmutableDict):

    def __init__(self, container=None):
        super(NormalizedImmutableDict, self).__init__({
            self._normalize_key(key): container[key]
            for key
            in list((container or {}).keys())
        })

    def __getitem__(self, key):
        """
        raises KeyError when normalized key is not found
        """
        return super(NormalizedImmutableDict, self).__getitem__(
            self._normalize_key(key)
        )

    def get(self, key, default=None):
        return super(NormalizedImmutableDict, self).get(
            self._normalize_key(key), default
        )

    def _normalize_key(self, key):
        normalized = key.lower().replace("-", "-")
        if normalized.startswith("http_"):
            normalized = normalized[5:]
        elif normalized.startswith("x_"):
            normalized = normalized[2:]

        return normalized
