# coding: utf8

from .components import ConfigObject, Router, View
from .components import initialize_loggers
from .components.session import (
    FileSessionStorage, MockSession, RedisSessionStorage,
    RedisSentinelSessionStorage, SessionStorage
)
from .http import Context
from .router_exceptions import (
    DispatchFinished, RouteSuccessfullyDispatched, RouteNotFound,
    RouteNotRegistered, RoutePassed
)

from inspect import getmembers, ismethod
from jinja2 import escape, Markup
from logging import getLogger
from os import path
from string import strip as string_strip
from sys import exc_info
from uwsgi import opt as uwsgi_opt


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

    KNOWN_SESSION_HANDLERS = {
        "file": FileSessionStorage,
        "redis": RedisSessionStorage,
        "redis-sentinel": RedisSentinelSessionStorage
    }

    def __init__(self):
        self._initialize_basic_components()
        self._methods = {}
        self._not_found_method = None
        self._error_method = None

    def __call__(self, environment, start_response):
        start_response = ResponseWrap(start_response)
        context = Context(environment, self.config)
        try:
            self._handle_request(context=context)
        except:
            log.exception("Fatal Error")
            start_response("500: Fatal Server Error", [])
            yield "Fatal Server Error"
        else:
            context.finalize_response()
            start_response(
                context.get_response_status_code(),
                context.get_response_headers()
            )
            body = context.get_response_body()
            if context.generates_response():
                for part in body():
                    yield part
            else:
                yield body

        return

    def display(self, *args, **kwargs):
        self.view.display(*args, **kwargs)
        raise DispatchFinished()

    def redirect(self, context, **kwargs):
        if "url" in kwargs:
            url = kwargs.pop("url")
        elif "route_name" in kwargs:
            url = "".join((
                context.get_request_url(),
                self.router.url_for(
                    kwargs.pop("route_name"),
                    kwargs.pop("params", None) or {}
                )
            ))
        else:
            raise RuntimeError("redirect needs url or route_name params")

        context.redirect(url, **kwargs)
        raise DispatchFinished()

    def do_postfork(self):
        """
        This method needs to be called in uwsgi postfork
        """
        self._collect_exposed_methods()
        if hasattr(self, "_route_register_func"):
            self._route_register_func(self.router)
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
        for unused_, member in getmembers(self, predicate=ismethod):
            if getattr(member, "_exposed", False) is True:
                self._methods[member._dispatch_name] = member

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
        for route in self.router.get_routes():
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
        try:
            storage_class = self.KNOWN_SESSION_HANDLERS[storage_type]
        except KeyError:
            raise RuntimeError("Unknown session handler: %r", storage_type)

        return storage_class

    def _get_config_path(self):
        for key in self.KNOWN_CONFIG_FORMATS:
            if key in uwsgi_opt:
                return uwsgi_opt[key]
        else:
            raise RuntimeError("No known config format used to start uwsgi!")

    def _handle_by_route(self, route, context):
        try:
            route.dispatch(context=context)
        except DispatchFinished:
            pass
        except RoutePassed:
            raise

        raise RouteSuccessfullyDispatched()

    def _handle_error(self, context, exc):
        log.error(
            "Error while dispatching to: %r",
            (
                context.current_route._handle_name
                if context.current_route
                else "<no route>"
            )
        )
        if self._error_method is not None:
            try:
                self._error_method(context=context, exc=exc)
                return
            except DispatchFinished:
                return
            except:
                exc = exc_info()[1]

        try:
            self._default_error_method(context=context, exc=exc)
        except:
            log.critical("Error in default_error_method")
            log.exception("Error in default_error_method")
            raise

    def _handle_not_found(self, context):
        not_found_method = (
            self._not_found_method or self._default_not_found_method
        )
        try:
            not_found_method(context=context)
        except DispatchFinished:
            pass

        raise RouteNotFound

    def _handle_request(self, context):
        try:
            session_loaded = False
            for route in self.router.matching_routes(context):
                if route.requires_session() and context.session is None:
                    context.load_session(self.session_handler)
                    session_loaded = True
                    log.debug(
                        "Session handler: %r loaded session: %r",
                        type(self.session_handler), context.session
                    )

                try:
                    self._handle_by_route(route=route, context=context)
                except RoutePassed:
                    continue
            else:
                self._handle_not_found(context=context)
        except RouteSuccessfullyDispatched:
            log.debug("Dispatch succeded on: %r", context.current_route)
            if session_loaded:
                context.save_session(self.session_handler)
        except RouteNotFound:
            log.debug(
                "No route found to handle request %r, handled by not_found",
                context.get_request_uri()
            )
        except:
            self._handle_error(context=context, exc=exc_info()[1])

    def _initialize_basic_components(self):
        self.config = ConfigObject(self._get_config_path())
        self._register_logger(self.config)
        self.router = Router()

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
            "print_css": self._jinja_print_css,
            "print_js": self._jinja_print_js,
            "url_for": self._jinja_url_for,
        }
        self.view = View(config, extra_functions)

    def _static_file_mtime(self, static_file):

        def get_static_file_abs_path(static_file):
            for option, mapping in self.config.get("uwsgi").iteritems():
                if option == "static-map":
                    prefix, mapped_dir = map(
                        string_strip, mapping.split("=")
                    )
                    if static_file.startswith(prefix):
                        return path.join(
                            mapped_dir,
                            path.relpath(static_file, prefix)
                        )
            else:
                return ""

        abs_path = get_static_file_abs_path(static_file)
        return (
            "v=%d" % int(path.getmtime(abs_path))
            if path.isfile(abs_path)
            else ""
        )

    # jinja extra methods
    def _jinja_print_css(self, css_list):
        return Markup("\n".join(
            """<link href="%s?%s" rel="stylesheet" type="text/css" />""" % (
                escape(css), self._static_file_mtime(css)
            )
            for css
            in css_list
        ))

    def _jinja_print_js(self, js_list, sync=True):
        return Markup("\n".join(
            """<script %ssrc="%s?%s"></script>""" % (
                "" if sync else "async ", js, self._static_file_mtime(js)
            )
            for js
            in js_list
        ))

    def _jinja_url_for(self, route, params=None):
        params = params or {}
        try:
            url = self.router.url_for(route, params)
        except RouteNotRegistered:
            if self.config.get("pygrim:debug", True) is False:
                url = "#"
            else:
                raise

        return url
