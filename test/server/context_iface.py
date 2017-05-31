# coding: utf8

from logging import getLogger
from pygrim.decorators import template_method

log = getLogger(__file__)


class ContextIface(object):
    """ testy contextu dostupneho z templaty"""

    def postfork(self):
        pass

    @template_method('context.jinja', session=True)
    def context(self, context):
        return {
            "data": {},
        }
