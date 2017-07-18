# coding: utf8


# uwsgi and libs
from pygrim import Server
from uwsgidecorators import postfork as postfork_decorator

# local
from model import Model
from first_controller import First
from group_controller import Group
from inner_group_controller import InnerGroup
from second_controller import Second


# to create custom session handler, view, etc:
"""
class MySessionClass(SessionStorage):
    pass

from pygrim import register_session_handler
register_session_handler("myhandler", MySessionClass)
"""


controllers = (
    First,
    Second,
    Group,
    InnerGroup
)


# naming instance of Server as application
#   can bee seen in configfile in section uwsgi->module=server:application
#   server is filename and application is method (uwsgi will do __call__ on
#   this object on every request)
application = Server()
application.register_model(Model())
for controller_class in controllers:
    application.register_controller(controller_class())


@postfork_decorator
def postfork():
    application.do_postfork()
