# coding: utf8


class AbstractView(object):
    """Defines interface for View classes"""

    def __init__(self, config, **kwargs):
        raise NotImplementedError(
            "Can't instantiate View interface, use its implementation"
        )

    def display(self, context):
        """Displays data given to context"""
        raise NotImplementedError()

    def get_template_directory(self):
        """Returns directory in which templates are searched"""
        raise NotImplementedError()

    def render(self, context):
        """
        Renders a template. Template's path and data are taken from context
        """
        raise NotImplementedError()
