# local
from .abstract_router import AbstractRouter
from .exceptions import PatternAlreadyExists
from .exceptions import RouteAlreadyExists, RouteNotRegistered
from .route import NoRoute, Route


class Router(AbstractRouter):

    def __init__(self):
        self._named_routes = {}
        self._routes = []

    def get_routes(self):
        return self._routes

    def has_routes(self):
        return bool(self._routes)

    def map(self, route):
        if not isinstance(route, Route):
            raise TypeError("Router can map only Route instance, %s given" % (
                type(route)
            ))

        route_name = route.get_name()
        if route_name in self._named_routes:
            raise RouteAlreadyExists(route)

        if any((existing for existing in self._routes if existing == route)):
            raise PatternAlreadyExists(route.pattern)

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
        self._named_routes[route_name] = route

    def matching_routes(self, context):
        for route in self._routes:
            if route.matches(context):
                context.current_route = route
                yield route
        else:
            context.current_route = NoRoute()
            context.set_route_params()
            context.session_changed = False

    def url_for(self, route_name, params):
        try:
            route = self._named_routes[route_name]
        except KeyError:
            raise RouteNotRegistered(route_name)
        else:
            return route.url_for(params)
