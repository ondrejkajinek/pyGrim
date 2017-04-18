# coding: utf8

from pyGrim import Route


class Routes(object):

    def _route_register_func(self, router):
        router.map(Route(("GET",), "/", "index", "home"))
        router.map(Route(("GET",), "/index", "index"))
