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

    @template_method("layout.jinja", "jinja")
    def model(self, context):
        return {
            "data": {
                "text": "Now: %s" % self._model.get_time().isoformat()
            }
        }

    @method()
    def redirect(self, context):
        context.redirect(self._router.url_for(
            "message",
            {
                "message": "This method redirects to another URL."
            }
        ))

    @template_method("layout.jinja", "jinja")
    def message(self, context, message):
        return {
            "data": {
                "text": "Message: %s" % message
            }
        }

    @method()
    def generator(self, context):
        context.set_view("raw")
        context.set_response_body((
            str(i) * 100 + "<br />"
            for i
            in xrange(4)
        ))

    @method()
    def generator_fction(self, context):

        def fction():
            for i in xrange(10):
                yield str(i) * 100 + "<br />"

        context.set_view("raw")
        context.set_response_body(fction)

    @method()
    def broken_generator_fction(self, context):

        def fction():
            for i in xrange(10):
                yield str(i) * 100 + "<br />"
            raise RuntimeError()

        context.set_view("raw")
        context.set_response_body(fction)
