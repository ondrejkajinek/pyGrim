# coding: utf8


from pygrim.server import Server as WebServer
from routes import Routes
from first_iface import FirstIface
from routing_iface import RoutingIface
from uwsgidecorators import postfork as postfork_decorator

import locale

locale.setlocale(locale.LC_ALL, "cs_CZ.UTF-8")


inheritance = (
    WebServer,
    Routes,

    FirstIface,
    RoutingIface,
)


def __init__(self, *args, **kwargs):
    WebServer.__init__(self, *args, **kwargs)


def postfork(self):
    for cls in inheritance:
        pfork = getattr(cls, "postfork", None)
        if pfork:
            pfork(self)


Server = type("Server", inheritance, {
    "__init__": __init__,
    "postfork": postfork
})


application = Server()


@postfork_decorator
def postfork():
    application.do_postfork()
