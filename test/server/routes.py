# coding: utf8

from pygrim.components.routing import Route
import re


class Routes(object):

    def _route_register_func(self, router):
        router.map(Route(("GET",), "/", "index", "index"))
        router.map(Route(("GET",), "/index.html", "index"))

        router.map(Route(("GET",), re.compile("/hitparady(/(?P<category_id>[0-9]+))?$"), "polls_list", "hitparady"))
        router.map(Route(("GET",), "/hitparady.html", "polls_list"))
        router.map(Route(("GET",), "/hitparady/", "polls_list"))

        router.map(Route(("GET",), "/favicon.png", "favicon"))
