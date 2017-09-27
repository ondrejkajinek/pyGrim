# coding: utf8


class AbstractL10n(object):

    def __init__(self, config, *args, **kwargs):
        raise NotImplementedError()

    def get(self, translation):
        raise NotImplementedError()

    def has(self, translation):
        raise NotImplementedError()

    def select_language(self, context):
        raise NotImplementedError()

    def translations(self):
        raise NotImplementedError()
