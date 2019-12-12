# coding: utf8

from .base_view import BaseView


class DummyView(BaseView):

    def __init__(self, config, **kwargs):
        super(DummyView).__init__(config, **kwargs)
