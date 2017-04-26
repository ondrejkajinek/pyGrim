# coding: utf8


from pygrim import Server as WebServer
from routes import Routes
from test_iface import Test
from uwsgidecorators import postfork as postfork_decorator
from pygrim.session import FileSessionStorage


inheritance = (
    WebServer,
    Test,
    Routes
)


def __init__(self, *args, **kwargs):
    # call base class at first
    WebServer.__init__(self, *args, **kwargs)

    # register session handler (if you need)
    # sometimes you need to register this in postfork (see comment there)
    self.register_session_handler(FileSessionStorage(self.config))


def postfork(self):
    # some types of handlers should be initialized in postfrork
    #   because of conflicts while forking (for example DB connections)
    # self.register_session_handler(FileSessionStorage())

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
