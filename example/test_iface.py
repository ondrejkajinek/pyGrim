# coding: utf8

from logging import getLogger
from pyGrim import method, not_found_method

log = getLogger(__file__)


class Test(object):

    @method()
    def index(self, request, response):
        data = {
            "text": u"Hello, index here! :)"
        }
        response.add_cookie(name="test", value="test", lifetime=3600)
        response.add_cookie(name="test2", value="test2", lifetime=7200)
        log.debug("Hello, index is logging :)")
        self.render(
            "layout.jinja", data, request, response
        )

    @method()
    def template_test(self, request, response, template):
        data = {
            "text": u"Selected template: %r" % template
        }
        self.render(
            "layout.jinja", data, request, response
        )

    @method()
    def time_listing(self, request, response, world):
        data = {
            "text": u"Time listing: %r" % world
        }
        self.render(
            "layout.jinja", data, request, response
        )

    @not_found_method
    def not_found(self, request, response):
        data = {
            "text": u"404: Try something else ;)"
        }
        log.debug("Not found...")
        self.render(
            "layout.jinja", data, request, response
        )
