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
    DispatchFinished, MissingRouteHandle, RouteNotFound, RouteNotRegistered,
    RoutePassed
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
            body = (
                None
                if context.is_request_head()
                else context.get_response_body()
            )
            if context.generates_response():
                for part in body():
                    yield part
            else:
                yield body

    def do_postfork(self):
        """
        This method needs to be called in uwsgi postfork
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

        self._enhance_controller(controller, self._controllers, "_controllers")
        self._enhance_controller(controller, self._router, "_router")
        self._enhance_controller(controller, self._model, "_model")
        self._process_decorated_methods(controller)
        self._controllers[controller.__class__.__name__] = controller

    def register_model(self, model):
        if self._model is not None:
            log.warning(
                "Model is already registered: %r",
                self._model.__class__.__name__
            )

        self._model = model
        for controller in self._controllers.itervalues():
            self._enhance_controller(controller, self._model, "_model")

    def register_router_creator(self, register_func):
        self._route_register_func = register_func

    def _default_error_method(self, context, exc):
        log.exception(exc.message)
        context.set_response_body("Internal Server Error")
        context.set_response_status(500)

    def _default_not_found_method(self, context):
        context.set_response_body("Not found")
        context.set_response_status(404)

    def _enhance_controller(self, controller, attribute, attr_name):
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
        if len(view_types) == 1 and view_types[0] == "dummy":
            log.info(
                "View is disabled. No sensible output will be created"
            )
        else:
            for view_type in ("json", "raw"):
                if view_type not in view_types:
                    view_types += (view_type,)

        for view_type in view_types:
            try:
                view_class = self.KNOWN_VIEW_CLASSES[view_type]
            except KeyError:
                raise RuntimeError("Unknown view class: %r.", view_class)
            else:
                yield view_type, view_class

    def _handle_by_route(self, route, context):
        if route.requires_session():
            context.load_session(self.session_handler)

        try:
            route.dispatch(context=context)
        except DispatchFinished:
            pass
        except RoutePassed:
            raise

        log.debug("Dispatch succeded on: %r.", context.current_route)
        # when exception is raised, we're not sure if session is valid,
        # so we only store it when no exception was raised
        if context.session_loaded():
            context.save_session(self.session_handler)

    def _handle_error(self, context, exc):
        log.exception(
            "Error while dispatching to: %r.",
            (
                context.current_route.full_handle_name()
                if context.current_route
                else "<no route>"
            )
        )
        try:
            for one in getmro(exc.__class__):
                if one in self._custom_error_handlers:
                    self._custom_error_handlers[one](context=context, exc=exc)
                    raise DispatchFinished()
            self._error_method(context=context, exc=exc)
            raise DispatchFinished()
        except DispatchFinished:
            return
        except:
            exc = exc_info()[1]

        try:
            self._default_error_method(context=context, exc=exc)
        except DispatchFinished:
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
        except DispatchFinished:
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
                raise RouteNotFound()
        except RouteNotFound:
            self._handle_not_found(context=context)
        except:
            self._handle_error(context=context, exc=exc_info()[1])

        if self._debug and self._dump_switch in context.GET():
            context.set_response_content_type("application/json")
            context.view_data["template_path"] = context.template
            context.set_view("json")

        view = context.get_view()
        if view is None or view not in self._views:
            raise UnknownView(view)

        self._views[view].display(context)

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
            "print_css": self._jinja_print_css,
            "print_js": self._jinja_print_js,
            "url_for": self._jinja_url_for,
        }
        self._views = {}
        for view_name, view_class in self._find_view_classes():
            view = view_class(self.config, extra_functions)
            if not isinstance(view, AbstractView):
                raise WrongViewBase(view)

            log.debug("Registering view class %r", view.__class__.__name__)
            self._views[view_name] = view

    def _setup_env(self):
        self._debug = self.config.getbool("pygrim:debug", True)
        self._dump_switch = self.config.get("pygrim:dump_switch", "jkxd")
        locale = self.config.get("pygrim:locale", None)
        if locale:
            log.debug("Setting locale 'LC_ALL' to %r", locale)
            setlocale(LC_ALL, str(locale))

        log.debug("PyGrim environment set up.")

    def _static_file_mtime(self, static_file):

        def get_static_file_abs_path(static_file):
            static_map = ensure_tuple(self.config.get("uwsgi:static-map", ()))
            for mapping in static_map:
                prefix, mapped_dir = map(string_strip, mapping.split("="))
                if static_file.startswith(prefix):
                    return path.join(
                        mapped_dir, path.relpath(static_file, prefix)
                    )
            else:
                return ""

        abs_path = get_static_file_abs_path(static_file)
        return (
            "v=%d" % int(path.getmtime(abs_path))
            if path.isfile(abs_path)
            else ""
        )

    def _view_disabled(self):
        return len(self._views) == 1 and "dummy" in self._views

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
            url = self._router.url_for(route, params)
        except RouteNotRegistered:
            if self._debug is False:
                url = "#"
            else:
                raise

        return url
