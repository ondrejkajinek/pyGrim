# coding: utf8

from logging import getLogger
from pygrim import (
    error_handler, error_method, method, not_found_method,
    template_display, template_method
)
from time import time

log = getLogger(__file__)


class Test(object):

    @method()
    def home(self, context):
        context.view_data.update({
            "text": u"Hello, this is the most simple case."
        })
        context.template = "layout.jinja"
        self.view.display(context)

    @method(
        session=True
    )
    def session_text(self, context):
        context.session.setdefault("text", "")
        context.session["text"] += "a"
        if len(context.session["text"]) > 6:
            context.session["text"] = ""

        context.view_data.update({
            "text": "This page shows content of session, zero to six a's",
            "session_text": context.session.get("text")
        })
        context.template = "layout.jinja"
        self.view.display(context)

    @template_method("layout.jinja")
    def cookie_show(self, context):
        return {
            "data": {
                "text": "COOKIES = %r" % context.get_cookies()
            }
        }

    @template_method("layout.jinja")
    def cookie_set(self, context):
        cur_time = int(time())
        context.add_cookie(name="test", value=cur_time, lifetime=3600)
        context.add_cookie(
            name="test2", value=cur_time, path="/cookie_set", lifetime=7200
        )
        return {
            "data": {
                "text": u"Current time is %d, COOKIES = %r" % (
                    cur_time, context.get_cookies()
                )
            }
        }

    @method()
    @template_display("layout.jinja")
    def use_template_display(self, context):
        return {
            "data": {
                "text": (
                    "This method uses @template_display to render template. "
                    "The handle is exposed via @method decorator."
                )
            }
        }

    @template_method("nonexisting.jinja", session=True)
    def use_template_method(self, context):
        return {
            "data": {
                "text": (
                    u"This method uses @template_method to expose method "
                    u"and set a template to 'nonexisting.jinja'. "
                    u"However, template is overriden to 'layout.jinja'. "
                    u"This method also loads session via its decorator."
                ),
                "session_text": context.session.get("text")
            },
            "_template": "layout.jinja"
        }

    @template_method("layout.jinja")
    def template_show(self, context, template):
        return {
            "data": {
                "text": "Template %r is given" % template
            }
        }

    @method()
    def type_error(self, context):
        raise TypeError("This method raises 'TypeError'")

    @method()
    def runtime_error(self, context):
        raise RuntimeError("This method raises 'RuntimeError'")

    @template_method("layout.jinja")
    def group_test(self, context):
        return {
            "data": {
                "text": "This method is mapped to route in group."
            }
        }

    @template_method("layout.jinja")
    def int_inner_group_test(self, context, param):
        return {
            "data": {
                "text": (
                    "This method is mapped to route in inner group. "
                    "Regexp route is used with integer parameter 'param'. "
                    "Given value is: %r" % param
                )
            }
        }

    @template_method("layout.jinja")
    def inner_group_test(self, context, param=None):
        return {
            "data": {
                "text": (
                    "This method is mapped to route in inner group. "
                    "Regexp route is used with optional parameter 'param'. "
                    "Given value is: %r" % param
                )
            }
        }

    @not_found_method("/detail/")
    def detail_not_found(self, context):
        context.view_data.update({
            "text": (
                u"404: This method is called when no route is registered "
                u"for given url and url starts with '/detail/'"
            )
        })
        context.template = "layout.jinja"
        context.set_response_status(404)
        self.view.display(context)

    @not_found_method()
    def not_found(self, context):
        context.view_data.update({
            "text": (
                u"404: This method is called when "
                u"no route is registered for given url."
            )
        })
        context.template = "layout.jinja"
        context.set_response_status(404)
        self.view.display(context)

    @error_handler(TypeError)
    def type_error_handle(self, context, exc):
        context.view_data.update({
            "text": u"500: This method is used when TypeError is raised."
        })
        context.template = "layout.jinja"
        context.set_response_status(500)
        self.view.display(context)

    @error_method()
    def ise_handle(self, context, exc):
        context.view_data.update({
            "text": (
                u"500: This method is used when exception is raised "
                u"and is not handled by any custom_error_handler"
            )
        })
        context.template = "layout.jinja"
        context.set_response_status(500)
        self.view.display(context)
