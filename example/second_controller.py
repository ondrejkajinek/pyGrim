# coding: utf8

from logging import getLogger
from re import compile as re_compile
from time import sleep
from sys import exc_info

try:
    from checkerslib import StrChkr, IntChkr
except ImportError:
    from checkers import StrChkr, IntChkr

from pygrim2 import GET
from pygrim2 import route, template, Validator

log = getLogger(__file__)


class Second(object):

    @route(GET, "/second", "second_home")
    def home(self, context):
        # This would cause
        # self._controllers.Second.home(context)
        self._controllers.First.home(context)
        context.view_data.update({
            "text": (
                u"Hello, this controller calls other controller's method. "
                u"Original message: %r"
            ) % context.view_data["text"]
        })

    @route(GET, name="model")
    @template("layout.jinja")
    def model(self, context):
        return {
            "text": "Now: %s" % self._model.get_time().isoformat()
        }

    @route(GET, name="redirect")
    def redirect(self, context):
        context.redirect(self._router.url_for(
            "message",
            {
                "message": "This method redirects to another URL."
            }
        ))

    @route(GET, re_compile(r"/message/((?P<message>[^/]+))?"), "message")
    @template("layout.jinja")
    def message(self, context, message):
        return {
            "text": "Message: %s" % (message or "NO MESSAGE")
        }

    @route(GET, name="generator")
    def generator(self, context):
        context.set_view("raw")
        context.set_response_body((
            str(i) * 100 + "<br />"
            for i
            in xrange(4)
        ))

    @route(GET, name="generator_function")
    def generator_fction(self, context):

        def fction():
            for i in xrange(10):
                yield str(i) * 100 + "<br />"
                sleep(2)

        context.set_view("raw")
        context.set_response_body(fction)

    @route(GET, name="broken_generator_function")
    def broken_generator_fction(self, context):

        def fction():
            for i in xrange(10):
                yield str(i) * 100 + "<br />"
            raise RuntimeError()

        context.set_view("raw")
        context.set_response_body(fction)

    @route(GET, name="validated")
    @template("layout.jinja")
    def validated(self, context):
        validator = Validator(
            context.GET,
            (
                ("first", StrChkr()),
                ("second", IntChkr(optional=True))
            )
        )
        try:
            output = "VALID INPUT: %r" % validator.validate()
        except:
            log.exception("Validation error: %s", exc_info()[1])
            output = "INVALID INPUT: %r" % {
                "first": context.GET("first"),
                "second": context.GET("second")
            }

        return {
            "text": output
        }
