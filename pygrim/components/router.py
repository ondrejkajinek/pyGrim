# coding: utf8

from logging import getLogger
from os.path import join as path_join
from re import compile as re_compile
from ..router_exceptions import RouteAlreadyExists
from .route import Route, RouteGroup

log = getLogger("pygrim.components.router")


class Router(object):

    def __init__(self):
        self._named_routes = None
        self._routes = []
        self._route_groups = []

    def get_routes(self):
        return self._routes

    def map(self, route):
        if isinstance(route, Route):
            full_pattern = path_join(
                "/" + self.group_pattern(), route.get_pattern()
            )
            if route._is_regex:
                route.set_pattern(re_compile(full_pattern))
            else:
                route.set_pattern(full_pattern)
            self._routes.append(route)
        elif isinstance(route, RouteGroup):
            self.push_group(route.pattern.strip("/"))
            for one in route:
                self.map(one)

            self.pop_group()
        else:
            raise ValueError("Unknown type:%s to map" % (type(route),))

    def matching_routes(self, context):
        for route in self._routes:
            if route.matches(context):
                context.current_route = route
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
        pattern = (
            path_join(*tuple(
                group_pattern
                for group_pattern
                in self._route_groups
            ))
            if self._route_groups
            else ""
        )
        return pattern

    def _has_named_route(self, route_name):
        if self._named_routes is None:
            self._get_named_routes()
        return route_name in self._named_routes
