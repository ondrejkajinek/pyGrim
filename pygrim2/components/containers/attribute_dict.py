# coding: utf8


class AttributeDict(dict):

    def __init__(self, *args, **kwargs):
        super(AttributeDict, self).__init__(*args, **kwargs)

    def __getattr__(self, key):
        try:
            return self.__getitem__(key)
        except KeyError as exc:
            raise AttributeError(exc)
