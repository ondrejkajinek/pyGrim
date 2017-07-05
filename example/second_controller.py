# coding: utf8


from logging import getLogger
from pygrim import route, template
from re import compile as re_compile
from time import sleep

log = getLogger(__file__)


class Second(object):

    @route("GET", "/second", "second_home")
    def home(self, context):
        # This would cause
        # self._controllers.Second.home(context)
        self._controllers.First.home(context)
        context.view_data.update({
            "text": u"Hello, this controller calls other controller's method."
        })

    @route("GET", "/model", "model")
    @template("layout.jinja")
    def model(self, context):
        return {
            "data": {
                "text": "Now: %s" % self._model.get_time().isoformat()
            }
        }

    @route("GET", "/redirect", "redirect")
    def redirect(self, context):
        context.redirect(self._router.url_for(
            "message",
            {
                "message": "This method redirects to another URL."
            }
        ))

    @route("GET", re_compile(r"/message/((?P<message>[^/]+))?"), "message")
    @template("layout.jinja")
    def message(self, context, message):
        return {
            "data": {
                "text": "Message: %s" % (message or "NO MESSAGE")
            }
        }

    @route("GET", "/generator", "generator")
    def generator(self, context):
        context.set_view("raw")
        context.set_response_body((
            str(i) * 100 + "<br />"
            for i
            in xrange(4)
        ))

    @route("GET", "/generator_fction", "generator_function")
    def generator_fction(self, context):

        def fction():
            for i in xrange(10):
                yield str(i) * 100 + "<br />"
                sleep(2)

        context.set_view("raw")
        context.set_response_body(fction)

    @route("GET", "/broken_generator_fction", "broken_generator_function")
    def broken_generator_fction(self, context):

        def fction():
            for i in xrange(10):
                yield str(i) * 100 + "<br />"
            raise RuntimeError()

        context.set_view("raw")
        context.set_response_body(fction)
