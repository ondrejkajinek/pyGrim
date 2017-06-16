# coding: utf8

from .abstract_view import AbstractView


class RawView(AbstractView):

    def render(self, context):
        return context.get_response_body()
