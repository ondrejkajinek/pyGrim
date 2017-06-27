# coding: utf8

from .abstract_view import AbstractView


class RawView(AbstractView):

    def __init__(self, config, extra_functions):
        self._initialize_view(config)

    def _render(self, context):
        return context.get_response_body()

    def _template_check(self, context):
        pass
