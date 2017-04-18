# coding: utf8


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


class NormalizedDict(object):

    def __init__(self, container=None):
        self._container = {
            self._normalize_key(key): container[key]
            for key
            in container or {}
        }

    def __delitem__(self, key):
        try:
            del self._container[self._normalize_key(key)]
        except KeyError:
            raise

    def __getitem__(self, key):
        try:
            return self._container[self._normalize_key(key)]
        except KeyError:
            raise

    def __iter__(self, key):
        return self._container.iterkeys()

    def __len__(self):
        return len(self._container)

    def __setitem__(self, key, value):
        self._container[self._normalize_key(key)] = value

    def _normalize_key(self, key):
        normalized = key.lower().replace("-", "_")
        if normalized.startswith("http_"):
            normalized = normalized[5:]

        return normalized
