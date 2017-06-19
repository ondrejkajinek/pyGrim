# coding: utf8


# uwsgi and libs
from pygrim import Server as WebServer
from uwsgidecorators import postfork as postfork_decorator

# local
from model import Model
from routes import register_routes
from test_iface import Test
from second_controller import Second


# to create custom session handler, view, etc:
"""
class MySessionClass(SessionStorage):
    pass

from pygrim import register_session_handler
register_session_handler("myhandler", MySessionClass)
"""


inheritance = (
    WebServer,
)
controllers = (
    Test,
    Second
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
application.register_model(Model())
application.register_router_creator(register_routes)
for controller_class in controllers:
    application.register_controller(controller_class())


@postfork_decorator
def postfork():
    application.do_postfork()
