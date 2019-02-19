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
