# coding: utf8


class BaseRouterException(Exception):
    pass


class RouteAlreadyExists(BaseRouterException):

    def __init__(self, name):
        super(RouteAlreadyExists, self).__init__(
            "Named route %r already exists." % name
        )


class RouteSuccessfullyDispatched(BaseRouterException):
    pass


class RouteNotFound(BaseRouterException):
    pass


class RouteNotRegistered(BaseRouterException):
    pass


class RoutePassed(BaseRouterException):
    pass


class DispatchFinished(BaseRouterException):
    """Raised by:
    - server.display
    - server.redirect
Can be used by user to stop anything after. It means:
    - finish request (session, etc.)
    - return data to browser
"""
