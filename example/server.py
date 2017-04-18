# coding: utf8


from pyGrim import Server as WebServer
from routes import Routes
from test_iface import Test
from uwsgidecorators import postfork as postfork_decorator


inheritance = (
    WebServer,
    Test,
    Routes
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
