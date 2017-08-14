# coding: utf8

# local
from .abstract_view import AbstractView


class DummyView(AbstractView):

    def __init__(self, config, **kwargs):
        pass

    def _render(self, context):
        return ""

    def _template_check(self, context):
        pass
