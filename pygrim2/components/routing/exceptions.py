# coding: utf8


class BaseRoutingException(Exception):
    pass


class PatternAlreadyExists(BaseRoutingException):

    def __init__(self, pattern):
        super(PatternAlreadyExists, self).__init__(
            "Route pattern '%s' already exists." % pattern
        )


class RouteAlreadyExists(BaseRoutingException):

    def __init__(self, route):
        super(RouteAlreadyExists, self).__init__(
            "Named route %r (pattern %r) already exists." % (
                route.get_name(), route.get_pattern()
            )
        )


class RouteNotFound(BaseRoutingException):
    pass


class RouteNotRegistered(BaseRoutingException):

    def __init__(self, route_name):
        super(RouteNotRegistered, self).__init__(
            "Route %r was not registered" % route_name
        )


class RoutePassed(BaseRoutingException):
    pass


class StopDispatch(BaseRoutingException):
    """
    Raised by:
        - context.redirect

    Can be used by user to stop anything after. It means:
        - finish request (session, etc.)
        - return data to browser
    """
