# coding: utf8


class AbstractView(object):

    def __init__(self, config, extra_functions):
        raise NotImplementedError(
            "Can't instantiate View interface, use its implementation"
        )

    def display(self, context):
        context.set_response_body(self.render(context))

    def get_template_directory(self):
        return ""

    def render(self, context):
        return ""
