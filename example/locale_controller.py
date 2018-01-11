# coding: utf8

from re import compile as re_compile

from pygrim2 import GET
from pygrim2 import RouteGroup
from pygrim2 import route, template


class LocaleController(object):

    _route_group = RouteGroup("/locale/")

    @route(GET, "/", "locale")
    @template("locale.jinja")
    def locale(self, context):
        default_locale = context.get_language()
        return {
            "default_locale": default_locale,
            "locale": default_locale
        }

    @route(GET, "/temp_en", "locale_temp_en")
    @template("locale.jinja")
    def locale_temp_en(self, context):
        default_locale = context.get_language()
        temp_locale = "en_GB.UTF-8"
        context.set_temp_language(temp_locale)
        return {
            "default_locale": default_locale,
            "locale": temp_locale
        }

    @route(GET, re_compile("/set/(?P<locale>[^/]+)"), "locale_set")
    @template("locale.jinja")
    def locale_set(self, context, locale):
        default_locale = context.get_language()
        context.set_language(locale)
        return {
            "default_locale": default_locale,
            "locale": locale
        }
