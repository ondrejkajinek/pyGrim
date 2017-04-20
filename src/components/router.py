# coding: utf8

from os.path import join as path_join
from ..router_exceptions import RouteAlreadyExists


class Router(object):

    def __init__(self):
        self._named_routes = None
        self._routes = []
        self._route_groups = []

    def get_routes(self):
        return self._routes

    def map(self, route):
        route.set_pattern(self.group_pattern() + route.get_pattern())
        self._routes.append(route)

    def matching_routes(self, request):
        for route in self._routes:
            if route.matches(request):
                request.current_route = route
                yield route

    def pop_group(self):
        try:
            self._route_groups.pop()
        except IndexError:
            pass

    def push_group(self, group):
        self._route_groups.append(group)

    def url_for(self, route_name, params):
        route = self._get_named_route(route_name)
        return route.url_for(params)

    def _get_named_route(self, name):
        if not self._has_named_route(name):
            raise RuntimeError(u"Route %r was not found" % name)
        return self._named_routes[name]

    def _get_named_routes(self):
        self._named_routes = {}
        for route in self._routes:
            name = route.get_name()
            if name:
                if name in self._named_routes:
                    raise RouteAlreadyExists
                self._named_routes[name] = route

    def group_pattern(self):
        return (
            path_join(*tuple(
                group_pattern
                for group_pattern
                in self._route_groups
            ))
            if self._route_groups
            else ""
        )

    def _has_named_route(self, route_name):
        if self._named_routes is None:
            self._get_named_routes()
        return route_name in self._named_routes
