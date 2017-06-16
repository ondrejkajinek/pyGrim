# coding: utf8

from .abstract_view import AbstractView


class RawView(AbstractView):

    def __init__(self, config, extra_functions):
        pass

    def render(self, context):
        return context.get_response_body()
