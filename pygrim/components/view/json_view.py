# coding: utf8

from .abstract_view import AbstractView
from ..utils.json2 import dumps as json_dumps


class JsonView(AbstractView):

    def __init__(self, config, _unused):
        pass

    def render(self, context):
        return json_dumps(context.view_data)
