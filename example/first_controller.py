# coding: utf8

from logging import getLogger
from pygrim import (
    error_handler, not_found_handler, route, template, RoutePassed
)
from re import compile as re_compile
from time import time

log = getLogger(__file__)


class First(object):

    @route("GET", "/", "home")
    def home(self, context):
        context.view_data.update({
            "text": u"Hello, this is the most simple case."
        })
        context.add_js("/tmp/added_header_async.js", sync=False)
        context.template = "layout.jinja"
        context.set_view("jinja")

    @route("GET", "/session", "session")
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

    @route("GET", "/cookie_show", "cookie_show")
    @template("layout.jinja", "jinja")
    def cookie_show(self, context):
        return {
            "data": {
                "text": "COOKIES = %r" % context.get_cookies()
            }
        }

    @route("GET", "/cookie_set", "cookie_set")
    @template("layout.jinja", "jinja")
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

    @route("GET", "/flash", "flash")
    def flash(self, context):
        context.flash("info", "First flash message")
        context.flash("info", "Second flash message")
        context.template = "flash.jinja"
        context.set_view("jinja")

    @route("GET", "/template", "template")
    @template("layout.jinja", "jinja")
    def use_template_display(self, context):
        return {
            "data": {
                "text": (
                    "This method uses @template to set template and view."
                )
            }
        }

    @route("GET", "/template_rewrite", "template_rewrite")
    @template("nonexisting.jinja", "jinja")
    def use_template_override(self, context):
        return {
            "data": {
                "text": (
                    u"This method uses @template decorator "
                    u"and set a template to 'nonexisting.jinja'. "
                    u"However, template is overriden to 'layout.jinja'. "
                    u"This method also loads session."
                ),
                "session_text": context.session.get("text")
            },
            "_template": "layout.jinja"
        }

    @route(
        "GET", re_compile(r"/template/(?P<template>[^/]+)"), "template_show"
    )
    @template("layout.jinja", "jinja")
    def template_show(self, context, template):
        return {
            "data": {
                "text": "Template %r is given" % template
            }
        }

    @route("GET", "/type_error", "type_error")
    def type_error(self, context):
        raise TypeError("This method raises 'TypeError'")

    @route("GET", "/runtime_error", "runtime_error")
    def runtime_error(self, context):
        raise RuntimeError("This method raises 'RuntimeError'")

    @route("GET", "/group/test")
    @template("layout.jinja", "jinja")
    def group_test(self, context):
        return {
            "data": {
                "text": "This method is mapped to route in group."
            }
        }

    @route("GET", re_compile("/group/inner_group/test/(?P<param>[0-9]+)"))
    @template("layout.jinja", "jinja")
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

    @route("GET", re_compile("/group/inner_group/test/(?P<param>[a-z0-9]+)"))
    @template("layout.jinja", "jinja")
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

    @route("GET", re_compile("/group/inner_group/test/(?P<param>[a-z]+)[^/]*"))
    def str_inner_group_test_pass(self, context, param=None):
        context.view_data.update({
            "previous_text": (
                "This method received route params %r. "
                "It does nothing but RoutePassed, so another matching route "
                "will be searched for." % context.get_route_params()
            )
        })
        raise RoutePassed()

    @not_found_handler(path="/detail/")
    def detail_not_found(self, context, exc):
        context.view_data.update({
            "text": (
                u"404: This method is called when no route is registered "
                u"for given url and url starts with '/detail/'"
            )
        })
        context.template = "layout.jinja"
        context.set_view("jinja")

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
        context.set_view("jinja")

    @error_handler(errors=TypeError)
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
                u"and is handled by BaseException handler."
            )
        })
        context.template = "layout.jinja"
        context.set_view("jinja")
