# coding: utf8

# std
from re import compile as re_compile

# local
from .abstract_router import AbstractRouter
from .exceptions import RouteAlreadyExists, RouteNotRegistered
from .route import NoRoute, Route, RouteGroup


class Router(AbstractRouter):

    def __init__(self):
        self._named_routes = None
        self._routes = []
        self._route_groups = []

    def get_routes(self):
        return self._routes

    def has_routes(self):
        return bool(self._routes)

    def map(self, route):
        if isinstance(route, Route):
            full_pattern = self._join(
                self._group_pattern(), route.get_pattern().strip("/")
            )
            route.set_pattern(
                re_compile("^" + full_pattern.lstrip("^"))
                if route.is_regular() or self._is_group_regular()
                else full_pattern
            )
            specificity = route.specificity()
            index = next(
                (
                    i
                    for i, r
                    in enumerate(self._routes)
                    if r.specificity() < specificity
                ),
                len(self._routes)
            )
            self._routes.insert(index, route)
        elif isinstance(route, RouteGroup):
            self.push_group(route)
            for one in route:
                self.map(one)

            self.pop_group()
        else:
            raise ValueError("Unknown type: %s to map" % (type(route),))

    def matching_routes(self, context):
        for route in self._routes:
            if route.matches(context):
                context.current_route = route
                yield route
        else:
            context.current_route = NoRoute()
            context.set_route_params()
            context.set_save_session(False)

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
            raise RouteNotRegistered(name)

        return self._named_routes[name]

    def _get_named_routes(self):
        self._named_routes = {}
        for route in self._routes:
            name = route.get_name()
            if name:
                if name in self._named_routes:
                    raise RouteAlreadyExists
                self._named_routes[name] = route

    def _group_pattern(self):
        pattern = (
            self._join(*tuple(
                group.get_pattern()
                for group
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

    def _is_group_regular(self):
        return any(
            group.is_regular()
            for group
            in self._route_groups
        )

    def _join(self, *args):
        return "".join(
            part if part.lstrip("(").startswith("/") else "/" + part
            for part
            in args
            if part
        )
