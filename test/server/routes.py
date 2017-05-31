# coding: utf8

from pygrim.components.routing import Route
import re


class Routes(object):

    def _route_register_func(self, router):
        # zakladni routovani
        router.map(Route(("GET",), "/", "index", "index"))
        router.map(Route(("GET",), "/index.html", "index"))
        router.map(Route(("GET",), "/static_page", "static_page", "static_page"))

        # servirovani binarnich dat
        router.map(Route(("GET",), "/favicon.png", "favicon"))

        # flash
        router.map(Route(("GET",), "/flash", "flash"))

        # expozice
        router.map(Route(("GET",), "/method_decorator", "method_decorator"))
        router.map(Route(("GET",), "/template_method_decorator", "template_method_decorator"))

        # 404
        # /404 vrati http status 404

        # chytani parametru z rout
        router.map(Route(("GET",), re.compile(
            "/hitparady(/(?P<category_id>[0-9]+))?$"),
            "polls_list", "hitparady"))
        router.map(Route(("GET",), "/hitparady/", "polls_list"))

        router.map(Route(("GET",), re.compile(
            "world/(?P<world>[0-9a-z-_]+)/(?P<time_range>[0-9a-z-_]+)/finalize$"),
            "svety", "svety"))

        # redirectovani
        router.map(Route(("GET",), "redirect_url", "redirect_url"))
        router.map(Route(("GET",), "redirect_with_param", "redirect_with_param"))

        # url_for
        router.map(Route(("GET",), "url_for", "url_for"))





