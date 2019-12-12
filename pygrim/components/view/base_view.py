# -*- coding: utf8 -*-

from .abstract_view import AbstractView


class BaseView(AbstractView):

    def __init__(self, config, **kwargs):
        self._debug = False
        self.timestamp_cache = {}

    def display(self, context):
        context.set_response_body(self.render(context))

    def get_template_directory(self):
        return ""

    def render(self, context):
        return ""
