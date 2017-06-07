# coding: utf8


from logging import getLogger
from pygrim import method, template_method

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

    @method()
    def redirect(self, context):
        context.redirect(self._router.url_for(
            "message",
            {
                "message": "This method redirects to another URL."
            }
        ))

    @template_method("layout.jinja")
    def message(self, context, message):
        return {
            "data": {
                "text": "Message: %s" % message
            }
        }
