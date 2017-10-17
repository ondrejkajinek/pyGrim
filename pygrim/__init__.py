# coding: utf8

from . import decorators, server

# compat, remove asap
from .components.routing import Route, RouteGroup
from .components import session
from .decorators import (
    error_handler, error_method, method, not_found_method,
    template_display, template_method, uses_data, error_handler,
    json_method,
)
from .server import register_session_handler, register_view_class
from .server import Server
