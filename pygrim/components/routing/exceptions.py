# coding: utf8


class BaseRoutingException(Exception):
    pass


class DispatchFinished(BaseRoutingException):
    """Raised by:
    - server.display
    - server.redirect
Can be used by user to stop anything after. It means:
    - finish request (session, etc.)
    - return data to browser
"""


class MissingRouteHandle(BaseRoutingException):

    def __init__(self, controller, handle, route):
        super(MissingRouteHandle, self).__init__(
            "Controller %r has no method %r to handle route %r." % (
                controller, handle, route
            )
        )


class RouteAlreadyExists(BaseRoutingException):

    def __init__(self, name):
        super(RouteAlreadyExists, self).__init__(
            "Named route %r already exists." % name
        )


class RouteNotFound(BaseRoutingException):
    pass


class RouteNotRegistered(BaseRoutingException):
    pass


class RoutePassed(BaseRoutingException):
    pass
