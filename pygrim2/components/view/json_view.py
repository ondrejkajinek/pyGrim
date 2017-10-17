# coding: utf8

# local
from .abstract_view import BaseView
from ..utils.json2 import dumps as json_dumps


class JsonView(BaseView):

    def __init__(self, config, **kwargs):
        self._initialize_view(config)

    def _render_template(self, context):
        return json_dumps(context.view_data)

    def _template_check(self, context):
        return
