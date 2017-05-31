# coding: utf8


from pygrim import Server as WebServer
from routes import Routes
from test_iface import Test
from uwsgidecorators import postfork as postfork_decorator
# from pygrim.components.session import FileSessionStorage


# to create custom session handler, view, etc:
"""
class MySessionClass(SessionStorage):
    pass

from pygrim import register_session_handler
register_session_handler("myhandler", MySessionClass)
"""


inheritance = (
    WebServer,
    Test,
    Routes
)


def __init__(self, *args, **kwargs):
    WebServer.__init__(self, *args, **kwargs)


def postfork(self):
    # for all interfaces call postfork to ensure all will be called
    for cls in inheritance:
        pfork = getattr(cls, "postfork", None)
        if pfork:
            pfork(self)

# Dynamicaly creating type.
# It allows me to do the trick with inheritance in postfork without
#   using inspect

Server = type("Server", inheritance, {
    "__init__": __init__,
    "postfork": postfork
})

# naming instance of Server as application
#   can bee seen in configfile in section uwsgi->module=server:application
#   server is filename and application is method (uwsgi will do __call__ on
#   this object on every request)
application = Server()


@postfork_decorator
def postfork():
    application.do_postfork()
