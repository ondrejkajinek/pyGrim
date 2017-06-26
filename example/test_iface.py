# coding: utf8

from logging import getLogger
from pygrim import (
    custom_error_handler, error_handler, method, not_found_handler,
    template_display, template_method, RoutePassed
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
        context.set_view("jinja")

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
        context.set_view("jinja")

    @template_method("layout.jinja", "jinja")
    def cookie_show(self, context):
        return {
            "data": {
                "text": "COOKIES = %r" % context.get_cookies()
            }
        }

    @template_method("layout.jinja", "jinja")
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
    @template_display("layout.jinja", "jinja")
    def use_template_display(self, context):
        return {
            "data": {
                "text": (
                    "This method uses @template_display to render template. "
                    "The handle is exposed via @method decorator."
                )
            }
        }

    @template_method("nonexisting.jinja", "jinja", session=True)
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

    @template_method("layout.jinja", "jinja")
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

    @template_method("layout.jinja", "jinja")
    def group_test(self, context):
        return {
            "data": {
                "text": "This method is mapped to route in group."
            }
        }

    @template_method("layout.jinja", "jinja")
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

    @template_method("layout.jinja", "jinja")
    def inner_group_test(self, context, param=None):
        text = context.view_data.get("previous_text") or ""
        text += (
            "This method is mapped to route in inner group. "
            "Regexp route is used with optional parameter 'param'. "
            "Given value is: %r" % param
        )
        return {
            "data": {
                "text": text
            }
        }

    @method()
    def str_inner_group_test_pass(self, context, param=None):
        context.view_data.update({
            "previous_text": (
                "This method received route params %r. "
                "It does nothing but RoutePassed, so another matching route "
                "will be searched for." % context.get_route_params()
            )
        })
        raise RoutePassed()

    @not_found_handler("/detail/")
    def detail_not_found(self, context):
        context.view_data.update({
            "text": (
                u"404: This method is called when no route is registered "
                u"for given url and url starts with '/detail/'"
            )
        })
        context.template = "layout.jinja"
        context.set_view("jinja")

    @not_found_handler("/runtime-raising/")
    def runtime_raising_not_found(self, context):
        raise RuntimeError("This not-found handler raises RuntimeError!")

    @not_found_handler("/type-raising/")
    def type_raising_not_found(self, context):
        raise TypeError("This not-found handler raises TypeError!")

    @not_found_handler()
    def not_found(self, context):
        context.view_data.update({
            "text": (
                u"404: This method is called when "
                u"no route is registered for given url."
            )
        })
        context.template = "layout.jinja"
        context.set_view("jinja")

    @custom_error_handler(TypeError)
    def type_error_handle(self, context, exc):
        context.view_data.update({
            "text": (
                u"501: This method is used when TypeError is raised. "
                "This handle sets http status to 501"
            )
        })
        context.template = "layout.jinja"
        context.set_response_status(501)
        context.set_view("jinja")

    @error_handler()
    def ise_handle(self, context, exc):
        context.view_data.update({
            "text": (
                u"500: This method is used when exception is raised "
                u"and is not handled by any custom_error_handler"
            )
        })
        context.template = "layout.jinja"
        context.set_view("jinja")
