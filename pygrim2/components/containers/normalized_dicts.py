# coding: utf8

# local
from .immutable_dict import ImmutableDict
from ..utils import ensure_string


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
        normalized = ensure_string(key).lower().replace("_", "-")
        if normalized.startswith("http-"):
            normalized = normalized[5:]
        elif normalized.startswith("x-"):
            normalized = normalized[2:]

        return normalized


class NormalizedImmutableDict(ImmutableDict, NormalizedDict):

    def __init__(self, *args, **kwargs):
        super(NormalizedImmutableDict, self).__init__(*args, **kwargs)
