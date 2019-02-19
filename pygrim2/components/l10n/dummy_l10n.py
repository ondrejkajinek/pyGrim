from .abstract_l10n import AbstractL10n


class DummyL10n(AbstractL10n):

    def __init__(self, *args, **kwargs):
        pass

    def get(self, translation):
        return None

    def has(self, translation):
        return True

    def select_language(self, context):
        return None, False

    def translations(self):
        return {}
