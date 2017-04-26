# coding: utf8

from logging import getLogger
from pyGrim import error_method, method, not_found_method

log = getLogger(__file__)


class Test(object):

    @method()
    def index(self, request, response):
        response.add_cookie(name="test", value="test", lifetime=3600)
        response.add_cookie(
            name="test2", value="test2", path="/test", lifetime=7200
        )
        response.add_view_data({
            "text": u"Hello, index here! :) Now we check unicode works fine.",
            "session_text": request.session.get("text")
        })
        request.session.setdefault("text", "")
        request.session["text"] += "a"
        if len(request.session["text"]) > 6:
            request.session["text"] = ""

        response.set_template("layout.jinja")
        log.debug("Hello, index is logging :)")
        self.display(request, response)

    @method()
    def test_cookie(self, request, response):
        response.add_view_data({
            "text": "COOKIES = %r" % request.cookies
        })
        response.set_template("layout.jinja")
        self.display(request, response)

    @method()
    def template_test(self, request, response, template):
        response.add_view_data({
            "text": u"Selected template: %r" % template
        })
        response.set_template("layout.jinja")
        self.render(request, response)

    @method()
    def time_listing(self, request, response, world):
        response.add_view_data({
            "text": u"Time listing: %r" % world
        })
        response.set_template("layout.jinja")
        self.render(request, response)

    @method()
    def ise(self, **kwargs):
        # this will cause ValueError ;)
        int(10, 20)

    @not_found_method
    def not_found(self, request, response):
        log.debug("Not found...")
        response.add_view_data({
            "text": u"404: Try something else ;)"
        })
        response.set_template("layout.jinja")
        self.display(request, response)

    @error_method()
    def ise_handle(self, request, response, exc):
        log.exception("500: AARRGGHH")
        response.add_view_data({
            "text": u"500: Something terrible happened, but we know it :)"
        })
        response.set_template("layout.jinja")
        self.display(request, response)
