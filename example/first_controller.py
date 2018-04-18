# coding: utf8

from logging import getLogger
from pygrim2 import error_handler, not_found_handler, route, template
from pygrim2 import GET
from re import compile as re_compile
from time import time
from traceback import format_exc

log = getLogger(__file__)


class First(object):

    @route(GET, "/", "home")
    def home(self, context):
        context.view_data.update({
            "text": u"Hello, this is the most simple case."
        })
        context.add_js("/tmp/added_header_async.js", sync=False)
        context.template = "layout.jinja"

    @route(GET, "/double_routed", "double_routed")
    @route(GET, "/dual_routed", "dual_routed")
    # this route will take pattern from method name, resulting in /twice_routed
    @route(GET, name="twice_routed")
    def twice_routed(self, context):
        context.view_data.update({
            "text": u"This handle can be accessed via two different routes."
        })
        context.template = "layout.jinja"

    @route(GET, "/session", "session")
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

    @route(GET, name="cookie_show")
    @template("layout.jinja")
    def cookie_show(self, context):
        return {
            "text": "COOKIES = %r" % context.get_cookies()
        }

    @route(GET, name="cookie_set")
    @template("layout.jinja")
    def cookie_set(self, context):
        cur_time = int(time())
        context.add_cookie(name="test", value=cur_time, lifetime=3600)
        context.add_cookie(
            name="test2", value=cur_time, path="/cookie_set", lifetime=7200
        )
        return {
            "text": u"Current time is %d, COOKIES = %r" % (
                cur_time, context.get_cookies()
            )
        }

    @route(GET, name="flash")
    def flash(self, context):
        context.flash("info", "First flash message.")
        context.flash("info", "Second flash message.")
        context.flash("layout", "This is 'layout' flash.")
        context.template = "flash.jinja"

    @route(GET, name="set_flash")
    def set_flash(self, context):
        context.flash(
            "info", "Current time: %s" % self._model.get_time().isoformat()
        )
        context.flash("layout", "This is flash with type 'layout'.")
        context.view_data.update({
            "text": (
                "This page sets two flash messages, one with type 'layout', "
                "other with type 'info'"
            )
        })
        context.template = "layout.jinja"

    @route(GET, "/template", "template")
    @template("layout.jinja")
    def use_template_display(self, context):
        return {
            "text": (
                "This method uses @template to set template and view "
                "(view is set via configured default view)."
            )
        }

    @route(GET, "/template_rewrite", "template_rewrite")
    @template("nonexisting.jinja")
    def use_template_override(self, context):
        context.template = "layout.jinja"
        return {
            "text": (
                u"This method uses @template decorator "
                u"and set a template to 'nonexisting.jinja'. "
                u"However, template is overriden to 'layout.jinja'. "
                u"This method also loads session."
            ),
            "session_text": context.session.get("text")
        }

    @route(
        GET, re_compile(r"/template/(?P<template>[^/]+)"), "template_show"
    )
    @template("layout.jinja")
    def template_show(self, context, template):
        return {
            "text": "Template %r is given" % template
        }

    @route(GET, name="type_error")
    def type_error(self, context):
        raise TypeError("This method raises 'TypeError'")

    @route(GET, name="runtime_error")
    def runtime_error(self, context):
        raise RuntimeError("This method raises 'RuntimeError'")

    @not_found_handler(path="/detail/")
    def detail_not_found(self, context, exc):
        context.view_data.update({
            "text": (
                u"404: This method is called when no route is registered "
                u"for given url and url starts with '/detail/'"
            )
        })
        context.template = "layout.jinja"

    @not_found_handler(path="/runtime_error/")
    def runtime_raising_not_found(self, context, exc):
        raise RuntimeError("This not-found handler raises RuntimeError!")

    @not_found_handler(path="/type_error/")
    def type_raising_not_found(self, context, exc):
        raise TypeError("This not-found handler raises TypeError!")

    @not_found_handler()
    def not_found(self, context, exc):
        context.view_data.update({
            "text": (
                u"404: This method is called when "
                u"no route is registered for given url."
            )
        })
        context.template = "layout.jinja"

    @error_handler(errors=TypeError)
    def type_error_handle(self, context, exc):
        context.view_data.update({
            "text": (
                u"501: This method is used when TypeError is raised. "
                "This handle sets http status to 501."
            ),
            "traceback": format_exc()
        })
        context.template = "error.jinja"
        context.set_response_status(501)

    @error_handler()
    @template("error.jinja")
    def ise_handle(self, context, exc):
        return {
            "text": (
                u"500: This method is used when exception is raised "
                u"and is handled by BaseException handler."
            ),
            "traceback": format_exc()
        }
