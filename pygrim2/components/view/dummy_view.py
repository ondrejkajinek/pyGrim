# local
from .abstract_view import AbstractView


class DummyView(AbstractView):

    def __init__(self, config, **kwargs):
        pass

    def _render(self, context):
        return ""
