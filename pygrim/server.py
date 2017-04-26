# coding: utf8

import inspect
import sys

from .components import ConfigObject, DependencyContainer, Router, View
from .components import initialize_loggers
from .http import Context
from .router_exceptions import (
    RouteSuccessfullyDispatched, RouteNotFound, RoutePassed
)
from .session import MockSession, SessionStorage, FileSessionStorage
from logging import getLogger
from os import path
from uwsgi import opt as uwsgi_opt
import json


log = getLogger("pygrim.server")


class ResponseWrap(object):
    def __init__(self, start_response):
        self._start_response = start_response

    def __call__(self, status, headers):
        self._start_response(status, headers)
        self._start_response = self.noop

    def noop(self, status, headers):
        pass


class Server(object):

    KNOWN_CONFIG_FORMATS = (
        "yaml", "ini"
    )

    def __init__(self):
        self._initialize_basic_components()
        self._methods = {}
        self._not_found_method = None

    def __call__(self, environment, start_response):
        start_response = ResponseWrap(start_response)
        context = Context(environment)
        self._handle_request(context)
        context.finalize_response()
        start_response(
            context.get_response_status_code(), context.get_response_headers()
        )
        yield context.get_response_body()
        return

    def display(self, *args, **kwargs):
        return self._dic.view.display(*args, **kwargs)

    # napojit na postfork
    def do_postfork(self):
        self._collect_exposed_methods()
        if hasattr(self, "_route_register_func"):
            self._route_register_func(self._dic.router)
            self._finalize_routes()
            log.debug("Routes loaded")
        else:
            log.warning("There is no function to register routes!")

        if hasattr(self, "postfork"):
            self.postfork()

    def render(self, *args, **kwargs):
        log.warning(
            "STOP CALLING AWFUL %r, CALL %r INSTEAD!",
            "server.render", "server.display"
        )
        return self.display(*args, **kwargs)

    def _collect_exposed_methods(self):
        def is_exposed(member, member_name):
            return (
                member_name[0] != "_" and
                getattr(member, "_exposed", False) is True
            )

        for member_name, member in inspect.getmembers(self):
            if is_exposed(member, member_name):
                try:
                    self._methods[member._dispatch_name] = member
                except AttributeError:
                    self._methods[member_name] = member

                if getattr(member, "_not_found", False) is True:
                    self._not_found_method = member

                if getattr(member, "_error", False) is True:
                    self._error_method = member

    def _default_error_method(self, context, exc):
        log.exception(exc.message)
        context.set_response_body("Internal Server Error")
        context.set_response_status(500)

    def _default_not_found_method(self, context):
        context.set_response_body("Not found")
        context.set_response_status(404)

    def _finalize_routes(self):
        for route in self._dic.router.get_routes():
            try:
                method = self._methods[route.get_handle_name()]
            except KeyError:
                raise RuntimeError(
                    u"Server has no method %r to handle route %r" % (
                        route._handle_name,
                        route.get_name() or route.get_pattern()
                    )
                )
            else:
                route.assign_method(method)

    def _find_session_handler(self):
        storage_type = self.config.get("session:type")
        if storage_type == "file":
            storage_class = FileSessionStorage
        else:
            raise RuntimeError("Unknown session handler: %r", storage_type)

        return storage_class

    def _get_config_path(self):
        for key in self.KNOWN_CONFIG_FORMATS:
            if key in uwsgi_opt:
                return uwsgi_opt[key]
        else:
            raise RuntimeError("No known config format used to start uwsgi!")

    def _handle_request(self, context):
        try:
            for route in self._dic.router.matching_routes(context):
                if route.requires_session() and context.session is None:
                    context.load_session(self.session_handler)

                try:
                    route.dispatch(context=context)
                    if route.requires_session():
                        context.save_session(self.session_handler)

                    raise RouteSuccessfullyDispatched()
                except RoutePassed:
                    pass
            else:
                if self._not_found_method:
                    self._not_found_method(context=context)
                else:
                    raise RouteNotFound()
        except RouteSuccessfullyDispatched:
            # everything was ok
            pass
        except RouteNotFound:
            self._default_not_found_method(context=context)
        except:
            log.error(
                "Error while dispatching to: %r",
                (
                    context.current_route._handle_name
                    if context.current_route
                    else "<no route>"
                )
            )
            exc = sys.exc_info()[1]
            if hasattr(self, "_error_method"):
                try:
                    self._error_method(context=context, exc=exc)
                    return
                except:
                    exc = sys.exc_info()[1]

            self._default_error_method(context=context, exc=exc)

    def _initialize_basic_components(self):
        self._dic = DependencyContainer()

        self.config = ConfigObject(self._get_config_path())
        self._register_logger(self.config)
        self._dic.mode = self.config.get("grim:mode")
        self._dic.router = Router()

        if self.config.get("view:enabled", True):
            self._register_view(self.config)

        self._register_session_handler()
        log.debug("Basic components initialized")

    def _register_session_handler(self):
        if self.config.get("session:enabled", False):
            storage_class = self._find_session_handler()
        else:
            storage_class = MockSession

        handler = storage_class(self.config)
        if not isinstance(handler, SessionStorage):
            raise ValueError(
                "SessionHandler should be derived from SessionStorage"
            )

        self.session_handler = handler

    def _register_logger(self, config):
        initialize_loggers(config)

    def _register_view(self, config):
        extra_functions = {
            "base_url": self._jinja_base_url,
            "site_url": self._jinja_site_url,
            "url_for": self._jinja_url_for,
            "as_json": self._jinja_as_json,
        }
        self._dic.view = View(config, extra_functions)

    # jinja extra methods
    def _jinja_as_json(self, data):
        return json.dumps(data)

    def _jinja_base_url(self, context):
        return "%s%s" % (
            context.get_request_url(), context.get_request_root_uri()
        )

    def _jinja_site_url(self, context, site):
        return path.join(self._jinja_base_url(context), site)

    def _jinja_url_for(self, context, route, params=None, add_domain=False):
        params = params or {}
        url = self._dic.router.url_for(route, params)
        if add_domain:
            url = context.get_request_url() + url
        return url

# eof
