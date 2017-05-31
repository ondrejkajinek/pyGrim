# coding: utf8

from logging import getLogger
from pygrim.decorators import method, uses_data, template_method
from pygrim.decorators import not_found_method
from icon import customized_icon

log = getLogger(__file__)


class FirstIface(object):
    """ testy zakladniho pouziti"""

    def postfork(self):
        pass

    @template_method('index.jinja', session=True)
    @uses_data('header')
    @uses_data('css_inject')
    def index(self, context):
        return {
            "data": {
                "value": u"předaná hodnota",
            },
        }

    @template_method('index.jinja')
    @uses_data('header')
    def uses_data_decorator(self, context):
        return {"data": {}}

    @template_method('index.jinja')
    @uses_data('css_inject')
    def uses_data_css(self, context):
        return {"data": {}}

    @method(session=True)
    def flash(self, context, *args, **kwargs):
        """ test zda flash prezije redirect """
        flash1 = ("flash_ident", u"Flash 1")
        flash2 = ("flash_ident", u"Flash 2")
        context.session.flash(*flash1)
        context.session.flash(*flash2)
        self.redirect(context, url="/")

    @method()
    def favicon(self, context):
        "testuje ze se v poradky vraci binary response obrazku"
        context.set_response_body(customized_icon())
        context.set_response_content_type("image/png")

    @method()
    def header(self, context):
        "test dekoratoru uses_data: injectne do contexdu data"
        return {
            "data": {
                "uses_data": u"hodnota z dekorátoru"
            }
        }

    @method()
    def css_inject(self, context):
        "test dekoratoru uses_data: injectne do contextu css"
        context.add_css(
            "test_css", "test_css.css",
        )

    @method()
    def method_decorator(self, context):
        "test ze decorator @method vyexponuje metodu (vrati 200)"
        return {
            "data": {},
        }

    @template_method('static_page.jinja')
    def template_method_decorator(self, context):
        "test ze decorator @template_method vyexponuje metodu (vrati 200)"
        return {
            "data": {},
        }

    @not_found_method()
    def not_found(self, context, *args, **kwargs):
        log.debug("Not found...")
        context.status = 404
        context.template = "404.jinja"
        self.display(context)

