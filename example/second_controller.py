# coding: utf8


from logging import getLogger
from pygrim import method

log = getLogger(__file__)


class Second(object):

    @method()
    def home(self, context):
        # This would cause
        # self._controllers.Second.home(context)
        self._controllers.Test.home(context)
        context.view_data.update({
            "text": u"Hello, this controller calls other controller's method."
        })
