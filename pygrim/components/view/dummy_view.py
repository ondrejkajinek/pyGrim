# coding: utf8

# local
from .abstract_view import AbstractView


class DummyView(AbstractView):

    def __init__(self, config, extra_functions):
        self._initialize_view(config)

    def _template_check(self, context):
        pass
