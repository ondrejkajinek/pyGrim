# coding: utf8

from .components.config import AbstractConfig, YamlConfig
from .components.exceptions import (
    ComponentTypeAlreadyRegistered, ControllerAttributeCollision,
    DuplicateContoller, UnknownController, UnknownView,
    WrongConfigBase, WrongRouterBase, WrongSessionHandlerBase, WrongViewBase
)
from .components.grim_dicts import AttributeDict
from .components.log import initialize_loggers
from .components.routing import AbstractRouter, Router
from .components.routing import (
    MissingRouteHandle, RouteNotRegistered, RoutePassed, StopDispatch
)
from .components.session import (
    DummySession, FileSessionStorage, RedisSessionStorage,
    RedisSentinelSessionStorage, SessionStorage
)
from .components.utils import ensure_tuple
from .components.view import (
    AbstractView, DummyView, JsonView, JinjaView, RawView
)
from .http import Context

from inspect import getmembers, ismethod, getmro
from jinja2 import escape, Markup
from locale import LC_ALL, setlocale
from logging import getLogger
from os import path
from string import strip as string_strip
from sys import exc_info
try:
    from uwsgi import opt as uwsgi_opt
except ImportError:
    uwsgi_opt = {}


log = getLogger("pygrim.server")


def register_session_handler(name, cls):
    if name in Server.KNOWN_SESSION_HANDLERS:
        raise ComponentTypeAlreadyRegistered(
            "SessionHandler", name, Server.KNOWN_SESSION_HANDLERS[name]
        )

    Server.KNOWN_SESSION_HANDLERS[name] = cls


def register_view_class(name, cls):
    if name in Server.KNOWN_VIEW_CLASSES:
        raise ComponentTypeAlreadyRegistered(
            "View", name, Server.KNOWN_VIEW_CLASSES[name]
        )

    Server.KNOWN_VIEW_CLASSES[name] = cls


class ResponseWrap(object):
    def __init__(self, start_response):
        self._start_response = start_response

    def __call__(self, status, headers):
        log.debug("starting response with:%r:%r", status, headers)
        self._start_response(status, headers)
        self._start_response = self.noop

    def noop(self, status, headers):
        pass


class Server(object):

    KNOWN_CONFIG_FORMATS = {
        "yaml": YamlConfig
    }

    KNOWN_SESSION_HANDLERS = {
        "file": FileSessionStorage,
        "redis": RedisSessionStorage,
        "redis-sentinel": RedisSentinelSessionStorage
    }

    KNOWN_VIEW_CLASSES = {
        "dummy": DummyView,
        "jinja": JinjaView,
        "json": JsonView,
        "raw": RawView
    }

    def __init__(self):
        self._initialize_basic_components()
        self._setup_env()

        self._controllers = AttributeDict()
        self._custom_error_handlers = {}
        self._error_method = self._default_error_method
        self._model = None
        # temporary
        # _not_found_methods will be turned into tuples at postfork time
        self._not_found_methods = {}
        self._route_register_func = None

    def __call__(self, environment, start_response):
        start_response = ResponseWrap(start_response)
        context = Context(environment, self.config, self._model)
        # if views are disabled, set view to dummy
        if self._view_disabled():
            context.set_view("dummy")

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
            is_head = context.is_request_head()
            if context.generates_response():
                for part in context.get_response_body():
                    if not is_head:
                        yield part
            else:
                if is_head:
                    log.debug("HEAD - not returning body")
                else:
                    yield context.get_response_body()

    def do_postfork(self):
        """
        This method needs to be called in uwsgi postfork,
        or after server instance has been initialized.
        """
        self._finalize_not_found_handlers()
        if self._route_register_func is not None:
            self._route_register_func(self._router)
            self._finalize_routes()
            log.debug("Routes loaded")
        else:
            log.warning("There is no function to register routes!")

        if hasattr(self, "postfork"):
            self.postfork()

    def register_controller(self, controller):
        if controller.__class__.__name__ in self._controllers:
            raise DuplicateContoller(controller)

        self._enhance_controller(controller, "_controllers", self._controllers)
        self._enhance_controller(controller, "_router", self._router)
        self._enhance_controller(controller, "_model", self._model)
        self._process_decorated_methods(controller)
        self._controllers[controller.__class__.__name__] = controller

    def register_model(self, model):
        if self._model is not None:
            log.warning(
                "Model is already registered: %r",
                self._model.__class__.__name__
            )

        self._model = model
        # Rewrite _model in controllers that were registered so far,
        # destroying original one
        for controller in self._controllers.itervalues():
            controller._model = self._model

    def register_routes_creator(self, register_func):
        self._route_register_func = register_func

    def _default_error_method(self, context, exc):
        log.exception(exc.message)
        context.set_response_body("Internal Server Error")
        context.set_response_status(500)
        context.set_view("raw")

    def _default_not_found_method(self, context):
        context.set_response_body("Not found")
        context.set_response_status(404)
        context.set_view("raw")

    def _enhance_controller(self, controller, attr_name, attribute):
        if hasattr(controller, attr_name):
            raise ControllerAttributeCollision(controller, attr_name)

        setattr(controller, attr_name, attribute)

    def _finalize_not_found_handlers(self):
        self._not_found_methods = tuple(
            (prefix, self._not_found_methods[prefix])
            for prefix
            in sorted(
                self._not_found_methods,
                key=lambda x: x.count("/"),
                reverse=True
            )
        )

    def _finalize_routes(self):
        for route in self._router.get_routes():
            try:
                controller = self._controllers[route.get_controller_name()]
            except KeyError:
                raise UnknownController(route.get_controller_name())

            try:
                # raises if method does not exist
                method = getattr(controller, route.get_handle_name())
                # raises if method is not exposed
                if method._exposed is True:
                    route.assign_method(method)
            except AttributeError:
                raise MissingRouteHandle(
                    controller,
                    route.get_handle_name(),
                    route.get_name() or route.get_pattern()
                )

        self._controllers = tuple(self._controllers.itervalues())

    def _find_config_class(self):
        for key in self.KNOWN_CONFIG_FORMATS:
            if key in uwsgi_opt:
                return uwsgi_opt[key], self.KNOWN_CONFIG_FORMATS[key]
        else:
            raise RuntimeError("No known config format used to start uwsgi!")

    def _find_router_class(self):
        return Router

    def _find_session_handler(self):
        storage_type = self.config.get("session:type")
        try:
            storage_class = self.KNOWN_SESSION_HANDLERS[storage_type]
        except KeyError:
            raise RuntimeError("Unknown session handler: %r.", storage_type)

        return storage_class

    def _find_view_classes(self):
        view_types = self.config.gettuple("view:types")
        # view is disabled when only dummy view is configured
        if view_types == ("dummy",):
            log.info("View is disabled, no output will be created!")
        else:
            for view_type in ("json", "raw"):
                if view_type not in view_types:
                    view_types += (view_type,)

        for view_type in view_types:
            try:
                yield view_type, self.KNOWN_VIEW_CLASSES[view_type]
            except KeyError:
                raise RuntimeError("Unknown view class: %r.", view_type)

    def _handle_by_route(self, route, context):
        if route.requires_session():
            context.load_session(self.session_handler)

        try:
            route.dispatch(context=context)
        except StopDispatch:
            pass
        except RoutePassed:
            raise

        log.debug("Dispatch succeeded on: %r.", context.current_route)

    def _handle_error(self, context, exc):
        log.exception(
            "Error while dispatching to: %r.",
            (
                context.current_route.get_full_handle_name()
                if context.current_route
                else "<no route>"
            )
        )
        try:
            for one in getmro(exc.__class__):
                if one in self._custom_error_handlers:
                    self._custom_error_handlers[one](context=context, exc=exc)
                    raise StopDispatch()
            self._error_method(context=context, exc=exc)
            raise StopDispatch()
        except StopDispatch:
            return
        except:
            exc = exc_info()[1]

        try:
            self._default_error_method(context=context, exc=exc)
        except StopDispatch:
            return
        except:
            log.critical("Error in default_error_method.")
            log.exception("Error in default_error_method.")
            raise

    def _handle_not_found(self, context):
        request_uri = context.get_request_uri()
        log.debug("No route found to handle request %r.", request_uri)
        try:
            for prefix, handle in self._not_found_methods:
                if request_uri.startswith(prefix):
                    handle(context=context)
                    log.debug("RouteNotFound exception successfully handled.")
                    break
        except StopDispatch:
            pass

    def _handle_request(self, context):
        try:
            for route in self._router.matching_routes(context):
                try:
                    self._handle_by_route(route=route, context=context)
                    break
                except RoutePassed:
                    continue
            else:
                self._handle_not_found(context=context)
        except:
            context.current_route = None
            self._handle_error(context=context, exc=exc_info()[1])

        if self._debug and self._dump_switch in context.GET():
            self._set_dump_view(context)

        view = context.get_view()
        if view is None or view not in self._views:
            raise UnknownView(view)

        self._views[view].display(context)
        # We want to save session only when request was handled with route
        # handle -- current_route is set
        if context.current_route and context.session_loaded():
            context.save_session(self.session_handler)

    def _initialize_basic_components(self):
        self._load_config()
        self._register_logger(self.config)
        self._register_router()
        self._register_view()
        self._register_session_handler()
        log.debug("Basic components initialized.")

    def _load_config(self):
        config_path, config_class = self._find_config_class()
        config = config_class(config_path)
        if not isinstance(config, AbstractConfig):
            raise WrongConfigBase(config)

        self.config = config

    def _process_custom_error_handler(self, method, err_cls):
        if err_cls in self._custom_error_handlers:
            raise RuntimeError(
                "Duplicate handling of error %r with %r and %r.",
                err_cls, self._custom_error_handlers[err_cls], method
            )
        log.debug("Method %r registered to handle %r.", method, err_cls)
        self._custom_error_handlers[err_cls] = method

    def _process_decorated_methods(self, controller):
        """
        Does not process exposed methods,
        those are processed when routes are finalized.
        """
        for unused_, member in getmembers(controller, predicate=ismethod):
            if getattr(member, "_error", False) is True:
                self._process_error_handler(member)

            for prefix in getattr(member, "_not_found", ()):
                self._process_not_found_method(member, prefix)

            for err_cls in getattr(member, "_custom_error", ()):
                self._process_custom_error_handler(member, err_cls)

        if "" not in self._not_found_methods:
            self._not_found_methods[""] = self._default_not_found_method

    def _process_error_handler(self, method):
        log.debug("Method %r registered as default exception handler", method)
        self._error_method = method

    def _process_not_found_method(self, method, prefix):
        if prefix in self._not_found_methods:
            raise RuntimeError(
                "Duplicate handling of not-found %r with %r and %r.",
                prefix, self._not_found_methods[prefix], method
            )

        log.debug("Method %r registered to handle not-found state", method)
        self._not_found_methods[prefix] = method

    def _register_router(self):
        router_class = self._find_router_class()
        router = router_class()
        if not isinstance(router, AbstractRouter):
            raise WrongRouterBase(router)

        self._router = router

    def _register_session_handler(self):
        if self.config.get("session:enabled", False):
            storage_class = self._find_session_handler()
        else:
            storage_class = DummySession

        handler = storage_class(self.config)
        if not isinstance(handler, SessionStorage):
            raise WrongSessionHandlerBase(handler)

        self.session_handler = handler

    def _register_logger(self, config):
        initialize_loggers(config)

    def _register_view(self):
        extra_functions = {
            "print_css": self._view_print_css,
            "print_js": self._view_print_js,
            "url_for": self._view_url_for,
        }
        self._views = {}
        for view_name, view_class in self._find_view_classes():
            view = view_class(self.config, extra_functions)
            if not isinstance(view, AbstractView):
                raise WrongViewBase(view)

            log.debug("Registering view class %r", view.__class__.__name__)
            self._views[view_name] = view

    def _set_dump_view(self, context):
        context.set_response_content_type("application/json")
        context.view_data.update(
            (key, getattr(context, key))
            for key
            in ("current_route", "session", "template", "_route_params")
        )
        context.set_view("json")

    def _setup_env(self):
        self._debug = self.config.getbool("pygrim:debug", True)
        self._dump_switch = self.config.get("pygrim:dump_switch", "jkxd")
        self._static_map = {
            fix_trailing_slash(prefix): mapped_dir
            for prefix, mapped_dir
            in (
                map(string_strip, mapping.split("="))
                for mapping
                in ensure_tuple(self.config.get("uwsgi:static-map", ()))
            )
        }
        locale = self.config.get("pygrim:locale", None)
        if locale:
            log.debug("Setting locale 'LC_ALL' to %r", locale)
            setlocale(LC_ALL, str(locale))

        log.debug("PyGrim environment set up.")

    def _static_file_abs_path(self, static_file):
        for prefix, mapped_dir in self._static_map.iteritems():
            if static_file.startswith(prefix):
                return path.join(
                    mapped_dir, path.relpath(static_file, prefix)
                )
        else:
            return ""

    def _versioned_file(self, static_file):
        abs_path = self._static_file_abs_path(static_file)
        return (
            "%s?v=%d" % (escape(static_file), int(path.getmtime(abs_path)))
            if path.isfile(abs_path)
            else escape(static_file)
        )

    def _view_disabled(self):
        # it is a bit faster than self._views == ["dummy"]
        return len(self._views) == 1 and "dummy" in self._views

    # jinja extra methods
    def _view_print_css(self, css_list):
        return Markup("\n".join(
            """<link href="%s" rel="stylesheet" type="text/css" />""" % (
                self._versioned_file(css)
            )
            for css
            in css_list
        ))

    def _view_print_js(self, js_list, sync=True):
        return Markup("\n".join(
            """<script src="%s"%s></script>""" % (
                self._versioned_file(js), "" if sync else " async"
            )
            for js
            in js_list
        ))

    def _view_url_for(self, route, params=None):
        params = params or {}
        try:
            url = self._router.url_for(route, params)
        except RouteNotRegistered:
            if self._debug is False:
                url = "#"
            else:
                raise

        return url
