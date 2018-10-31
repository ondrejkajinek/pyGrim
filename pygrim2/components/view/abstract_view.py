# coding: utf8


class AbstractView(object):

    def __init__(self, config, **kwargs):
        raise NotImplementedError(
            "Can't instantiate View interface, use its implementation"
        )

    def display(self, context):
        context.set_response_body(self._render(context))

    def get_template_directory(self):
        return ()

    def _render(self, context):
        raise NotImplementedError()
