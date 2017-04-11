# coding: utf8


class BaseRouterException(Exception):
    pass


class RouteAlreadyExists(BaseRouterException):

    def __init__(self, name):
        super(RouteAlreadyExists, self).__init__(
            "Named route %r already exists." % name
        )


class RouteDispatched(BaseRouterException):
    pass


class RouteNotFound(BaseRouterException):
    pass


class RoutePassed(BaseRouterException):
    pass
