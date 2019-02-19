# local
from .base_view import BaseView


class RawView(BaseView):

    def __init__(self, config, **kwargs):
        self._initialize_view(config)

    def _render_template(self, context):
        return context.get_response_body()

    def _template_check(self, context):
        pass
