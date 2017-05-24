# coding: utf8

from .components.config import ConfigObject
from .components.log import initialize_loggers
from .components.routing import AbstractRouter, Router
from .components.routing import (
    DispatchFinished, RouteNotFound, RouteNotRegistered, RoutePassed
)
from .components.session import (
    FileSessionStorage, MockSession, RedisSessionStorage,
    RedisSentinelSessionStorage, SessionStorage
)
from .components.view import AbstractView, JinjaView, MockView
from .http import Context

from inspect import getmembers, ismethod, getmro
from jinja2 import escape, Markup
from logging import getLogger
from os import path
from string import strip as string_strip
from sys import exc_info
try:
    from uwsgi import opt as uwsgi_opt
except ImportError:
    uwsgi_opt = {}


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

    KNOWN_VIEW_CLASSES = {
        "jinja": JinjaView
    }

    def __init__(self):
        self._initialize_basic_components()
        self._methods = {}
        self._not_found_method = None
        self._default_error_method = self.__default_error_method
        self._custom_error_handlers = {}

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

                if getattr(member, "_default_error", False) is True:
                    self._default_error_method = member

                errs = getattr(member, "_error", ())
                for err_cls in errs:
                    if err_cls in self._custom_error_handlers:
                        raise RuntimeError(
                            "duplicate handling of error %r with %r and %r",
                            err_cls,
                            self._custom_error_handlers[err_cls], member
                        )
                    # endif
                    log.debug("Registered %r to handle %r", member, err_cls)
                    self._custom_error_handlers[err_cls] = member
                # endfor
            # endfor

    def __default_error_method(self, context, exc):
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

    def _find_router_class(self):
        return Router

    def _find_session_handler(self):
        storage_type = self.config.get("session:type")
        try:
            storage_class = self.KNOWN_SESSION_HANDLERS[storage_type]
        except KeyError:
            raise RuntimeError("Unknown session handler: %r", storage_type)

        return storage_class

    def _find_view_class(self):
        view_type = self.config.get("view:type")
        try:
            view_class = self.KNOWN_VIEW_CLASSES[view_type]
        except KeyError:
            raise RuntimeError("Unknown view class: %r", view_class)

        return view_class

    def _get_config_path(self):
        for key in self.KNOWN_CONFIG_FORMATS:
            if key in uwsgi_opt:
                return uwsgi_opt[key]
        else:
            raise RuntimeError("No known config format used to start uwsgi!")

    def _handle_by_route(self, route, context):
        if route.requires_session():
            context.load_session(self.session_handler)

        try:
            route.dispatch(context=context)
        except DispatchFinished:
            pass
        except RoutePassed:
            raise

        log.debug(
            "Dispatch succeded on: %r", context.current_route
        )
        if context.session_loaded():
            context.save_session(self.session_handler)

    def _handle_error(self, context, exc):
        log.exception(
            "Error while dispatching to: %r",
            (
                context.current_route._handle_name
                if context.current_route
                else "<no route>"
            )
        )
        try:

            for one in getmro(exc.__class__):
                log.debug("Looking up error handler for %r", one)
                if one in self._custom_error_handlers:
                    self._custom_error_handlers[one](context=context, exc=exc)
                    raise DispatchFinished
            if self._default_error_method is not None:
                self._default_error_method(context=context, exc=exc)
                raise DispatchFinished
        except DispatchFinished:
            return
        except:
            exc = exc_info()[1]

        try:
            self._default_error_method(context=context, exc=exc)
        except DispatchFinished:
            return
        except:
            log.critical("Error in default_error_method")
            log.exception("Error in default_error_method")
            raise

    def _handle_not_found(self, context):
        log.debug(
            "No route found to handle request %r",
            context.get_request_uri()
        )
        not_found_method = (
            self._not_found_method or self._default_not_found_method
        )
        try:
            not_found_method(context=context)
        except DispatchFinished:
            pass
        log.debug("RouteNotFound exception successfully handled")

    def _handle_request(self, context):
        try:
            for route in self.router.matching_routes(context):
                try:
                    self._handle_by_route(route=route, context=context)
                except RoutePassed:
                    continue
                else:
                    break
            else:
                raise RouteNotFound()
        except RouteNotFound:
            self._handle_not_found(context=context)
        except:
            self._handle_error(context=context, exc=exc_info()[1])

    def _initialize_basic_components(self):
        self.config = ConfigObject(self._get_config_path())
        self._register_logger(self.config)
        self._register_router()
        self._register_view()
        self._register_session_handler()
        log.debug("Basic components initialized")

    def _register_router(self):
        router_class = self._find_router_class()
        router = router_class()
        if not isinstance(router, AbstractRouter):
            raise ValueError(
                "Router class has to be derived from AbstractRouter"
            )

        self.router = router

    def _register_session_handler(self):
        if self.config.get("session:enabled", False):
            storage_class = self._find_session_handler()
        else:
            storage_class = MockSession

        handler = storage_class(self.config)
        if not isinstance(handler, SessionStorage):
            raise ValueError(
                "Session handler has to be derived from SessionStorage"
            )

        self.session_handler = handler

    def _register_logger(self, config):
        initialize_loggers(config)

    def _register_view(self):
        if self.config.get("view:enabled", True):
            view_class = self._find_view_class()
        else:
            view_class = MockView

        extra_functions = {
            "print_css": self._jinja_print_css,
            "print_js": self._jinja_print_js,
            "url_for": self._jinja_url_for,
        }
        view = view_class(self.config, extra_functions)
        if not isinstance(view, AbstractView):
            raise ValueError("View class has to be derived from AbstractView")

        self.view = view

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
