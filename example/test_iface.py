# coding: utf8

from logging import getLogger
from pyGrim import error_method, method, not_found_method, template_method

log = getLogger(__file__)


class Test(object):

    @method(
        session=True
    )
    def index(self, context):
        context.add_cookie(name="test", value="test", lifetime=3600)
        context.add_cookie(
            name="test2", value="test2", path="/test", lifetime=7200
        )
        context.view_data.update({
            "text": u"Hello, index here! :) Now we check unicode works fine.",
            "session_text": context.session.get("text")
        })
        context.session.setdefault("text", "")
        context.session["text"] += "a"
        if len(context.session["text"]) > 6:
            context.session["text"] = ""

        context.template = "layout.jinja"
        log.debug("Hello, index is logging :)")
        self.display(context)

    @method()
    @template_method("layout.jinja")
    def test_cookie(self, context):
        return {
            "data": {
                "text": "COOKIES = %r" % context.get_cookies()
            }
        }

    @method()
    def template_test(self, context, template):
        context.view_data.update({
            "text": u"Selected template: %r" % template
        })
        context.template = "layout.jinja"
        self.render(context)

    @method()
    def time_listing(self, context, world):
        context.view_data.update({
            "text": u"Time listing: %r" % world
        })
        context.template = "layout.jinja"
        self.render(context)

    @template_method("layout.jinja")
    def test_re_group(self, context, group):
        return {
            "data": {
                "text": "/regroup/%s/print" % group
            }
        }

    @method()
    def ise(self, context):
        # this will cause ValueError ;)
        int(10, 20)

    @not_found_method()
    def not_found(self, context):
        log.debug("Not found...")
        context.view_data.update({
            "text": u"404: Try something else ;)"
        })
        context.template = "layout.jinja"
        self.display(context)

    @error_method()
    def ise_handle(self, context, exc):
        log.exception("500: AARRGGHH")
        context.view_data.update({
            "text": u"500: Something terrible happened, but we know it :)"
        })
        context.template = "layout.jinja"
        self.display(context)
