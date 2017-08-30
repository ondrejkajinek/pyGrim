# coding: utf8

# std
from inspect import getmembers, ismethod, getmro
from locale import LC_ALL, setlocale
from logging import getLogger
from os import path
from string import strip as string_strip
from sys import exc_info

# non-std
from jinja2 import escape, Markup
try:
    from uwsgi import opt as uwsgi_opt
except ImportError:
    uwsgi_opt = {}

# local
from .components.config import AbstractConfig, YamlConfig
from .components.exceptions import (
    ComponentTypeAlreadyRegistered, ControllerAttributeCollision,
    DuplicateContoller, UnknownView,
    WrongConfigBase, WrongL10nBase, WrongRouterBase, WrongSessionHandlerBase,
    WrongViewBase
)
from .components.grim_dicts import AttributeDict
from .components.l10n import AbstractL10n, DummyL10n, GettextL10n
from .components.log import initialize_loggers
from .components.routing import AbstractRouter, NoRoute, Route, Router
from .components.routing import (
    RouteNotFound, RouteNotRegistered, RoutePassed, StopDispatch
)
from .components.session import (
    DummySession, FileSessionStorage, RedisSessionStorage,
    RedisSentinelSessionStorage, SessionStorage
)
from .components.utils import (
    ensure_tuple, fix_trailing_slash, get_instance_name, get_class_name,
    get_method_name
)
from .components.view import (
    AbstractView, DummyView, JsonView, JinjaView, RawView
)
from .http import Context, HeadersAlreadySent


start_log = getLogger("pygrim_start.server")
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
        log.debug("Starting response with: %r: %r", status, headers)
        self._start_response(status, headers)
        self._start_response = self.noop

    def noop(self, status, headers):
        pass


class Server(object):

    KNOWN_CONFIG_FORMATS = {
        "yaml": YamlConfig
    }

    KNONW_L10N_CLASSES = {
        "dummy": DummyL10n,
        "gettext": GettextL10n
    }

    KNOWN_SESSION_HANDLERS = {
        "dummy": DummySession,
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
        self._error_handlers = {}
        self._model = None

    def __call__(self, environment, start_response):
        start_response = ResponseWrap(start_response)
        context = Context(
            environment,
            self.config,
            self._model,
            self._session_handler,
            self._l10n
        )
        context.set_view(self._default_view)

        try:
            self._handle_request(context=context)
        except:
            start_response("500: Fatal Server Error", [])
            yield "Fatal Server Error"
        else:
            context.finalize_response()
            start_response(
                context.get_response_status_code(),
                context.get_response_headers()
            )
            is_head = context.is_request_head()
            if is_head:
                log.debug("This is HEAD request, not returning body.")

            try:
                if context.generates_response():
                    for part in context.get_response_body():
                        if not is_head:
                            yield part
                elif not is_head:
                    yield context.get_response_body()
            except HeadersAlreadySent as exc:
                yield "CRITICAL ERROR WHEN SENDING RESPONSE: %s" % exc
                for key, value in context.get_response_headers():
                    if key == "content-length":
                        yield " " * int(value)
                        break
            else:
                # We want to save session only when request was handled with
                # route handle -- current_route is set
                if context.current_route and context.session_loaded():
                    context.save_session()

    def do_postfork(self):
        """
        This method needs to be called in uwsgi postfork,
        or after server instance has been initialized.
        """
        self._finalize_error_handlers()
        if not self._router.has_routes():
            start_log.warning(
                "No routes were registered, no requests will be handled!"
            )

    def register_controller(self, controller):
        # Do not use get_instance_name,
        # since it would append file name to controller class name
        controller_name = controller.__class__.__name__
        if controller_name in self._controllers:
            raise DuplicateContoller(controller)

        self._enhance_controller(controller, "_controllers", self._controllers)
        self._enhance_controller(controller, "_router", self._router)
        self._enhance_controller(controller, "_model", self._model)
        self._process_decorated_methods(controller)
        self._controllers[controller_name] = controller
        start_log.debug("Controller %r registered", controller_name)

    def register_model(self, model):
        if self._model is not None:
            start_log.warning(
                "Model is already registered: %r",
                get_instance_name(self._model)
            )

        self._model = model
        # Rewrite _model in controllers that were registered so far,
        # destroying original one
        for controller in self._controllers.itervalues():
            controller._model = self._model

    def _default_error_handler(self, context, exc):
        log.exception(exc.message)
        context.set_response_body("Internal Server Error")
        context.set_response_status(500)
        self._set_fallback_view(context)

    def _default_not_found_handler(self, context):
        context.set_response_body("Not found")
        context.set_response_status(404)
        self._set_fallback_view(context)

    def _enhance_controller(self, controller, attr_name, attribute):
        try:
            attr = getattr(controller, attr_name)
            raise ControllerAttributeCollision(controller, attr_name, attr)
        except AttributeError:
            setattr(controller, attr_name, attribute)

    def _finalize_error_handlers(self):
        has_not_found = ("", RouteNotFound) in self._error_handlers
        has_base_exception = ("", BaseException) in self._error_handlers
        self._error_handlers = tuple(
            (key[0], key[1], self._error_handlers[key])
            for key
            in sorted(
                self._error_handlers,
                key=lambda x: 1e3 * len(getmro(x[1])) + x[0].count("/"),
                reverse=True
            )
        )
        if not has_not_found:
            self._error_handlers += (
                ("", RouteNotFound, self._default_not_found_handler),
            )

        if not has_base_exception:
            self._error_handlers += (
                ("", BaseException, self._default_error_handler),
            )

    def _find_config_class(self):
        for key in self.KNOWN_CONFIG_FORMATS:
            if key in uwsgi_opt:
                return uwsgi_opt[key], self.KNOWN_CONFIG_FORMATS[key]
        else:
            raise RuntimeError("No known config format used to start uwsgi!")

    def _find_l10n_class(self):
        l10n_type = self.config.get("pygrim:l10n:type", "dummy")
        try:
            l10n_class = self.KNONW_L10N_CLASSES[l10n_type]
        except KeyError:
            raise RuntimeError("Unknown l10n class: %r.", l10n_type)

        return l10n_class

    def _find_router_class(self):
        return Router

    def _find_session_handler(self):
        storage_type = self.config.get("session:type")
        try:
            storage_class = self.KNOWN_SESSION_HANDLERS[storage_type]
        except KeyError:
            raise RuntimeError("Unknown session handler: %r.", storage_type)
        else:
            if storage_type == "dummy":
                start_log.warning("Session is disabled!")

        return storage_class

    def _find_view_classes(self):
        view_types = self.config.getset("view:types")
        # view is disabled when only dummy view is configured
        if view_types == ("dummy",):
            start_log.info("View is disabled, no output will be created!")
        else:
            view_types.update(("raw", "json"))

        for view_type in view_types:
            try:
                yield view_type, self.KNOWN_VIEW_CLASSES[view_type]
            except KeyError:
                raise RuntimeError("Unknown view class: %r.", view_type)

    def _handle_by_route(self, context):
        for route in self._router.matching_routes(context):
            try:
                route.dispatch(context=context)
                break
            except RoutePassed:
                continue
        else:
            raise RouteNotFound()

        log.debug(
            "Request handled by route %s.", context.current_route.get_pattern()
        )

    def _handle_error(self, context, exc):
        try:
            self._handle_generic_error(context, exc)
        except StopDispatch:
            raise
        except:
            exc = exc_info()[1]
            try:
                self._default_error_handler(context=context, exc=exc)
            except:
                log.critical("Error in default_error_handler.")
                log.exception("Error in default_error_handler.")
                raise

    def _handle_generic_error(self, context, exc):
        request_uri = context.get_request_uri()
        for handler in self._matching_error_handlers(
            request_uri, getmro(exc.__class__)
        ):
            handler(context=context, exc=exc)
            log.debug(
                "Error %r handled with %r.",
                get_class_name(exc.__class__), get_method_name(handler)
            )
            break

    def _handle_not_found(self, context, exc):
        request_uri = context.get_request_uri()
        log.debug("No route found to handle request %r.", request_uri)
        # let all its exceptions be raised to the caller
        self._handle_generic_error(context=context, exc=exc)

    def _handle_request(self, context):
        try:
            try:
                self._handle_by_route(context=context)
            except RouteNotFound as exc:
                self._handle_not_found(context=context, exc=exc)
        except StopDispatch:
            pass
        except:
            try:
                log.exception(
                    "Error while dispatching to: %r.",
                    context.current_route.get_handle_name()
                )
                context.current_route = NoRoute()
                self._handle_error(context=context, exc=exc_info()[1])
            except StopDispatch:
                pass
            else:
                self._prepare_output(context)
        else:
            self._prepare_output(context)

    def _initialize_basic_components(self):
        self._load_config()
        self._register_logger(self.config)
        self._register_router()
        self._register_l10n()
        self._register_view()
        self._register_session_handler()
        start_log.debug("Basic components initialized.")

    def _load_config(self):
        config_path, config_class = self._find_config_class()
        config = config_class(config_path)
        if not isinstance(config, AbstractConfig):
            raise WrongConfigBase(config)

        self.config = config

    def _matching_error_handlers(self, request_uri, exc_mro):
        for exc in exc_mro:
            for prefix, err_cls, handler in self._error_handlers:
                if request_uri.startswith(prefix) and exc is err_cls:
                    yield handler

    def _prepare_output(self, context):
        if self._debug and self._dump_switch in context.GET():
            self._set_dump_view(context)

        try:
            view = self._views[context.get_view()]
        except KeyError:
            raise UnknownView(context.get_view())
        else:
            view.use_translation(self._l10n.get(context.get_language()))

            try:
                view.display(context)
            except:
                log.exception("Error when calling View.display")
                raise

    def _process_error_handler(self, method):
        for prefix in method._paths:
            for error in method._errors:
                self._process_error_handler_part(prefix, error, method)

    def _process_error_handler_part(self, prefix, error, method):
        key = (prefix, error)
        if key in self._error_handlers:
            raise RuntimeError(
                "Duplicate handling of error %r on %r with %r and %r." % (
                    get_class_name(error),
                    prefix,
                    get_method_name(self._error_handlers[key]),
                    get_method_name(method)
                )
            )

        self._error_handlers[key] = method
        start_log.debug(
            "Method %r registered to handle %r for request %r.",
            get_method_name(method), get_class_name(error), prefix
        )

    def _process_decorated_methods(self, controller):
        """
        Does not process exposed methods,
        those are processed when routes are finalized.
        """
        for unused_, member in getmembers(controller, predicate=ismethod):
            if getattr(member, "_errors", None):
                self._process_error_handler(member)

            if getattr(member, "_route", None):
                self._process_route_handler(controller, member)

    def _process_route_handler(self, controller, handle):
        routes = handle.__dict__.pop("_route")
        for kwargs in routes:
            kwargs["handle"] = handle
            route = Route(**kwargs)
            route_group = getattr(controller, "_route_group", None)
            if route_group:
                route = route_group + route

            self._router.map(route)
            start_log.debug(
                "Method %r registered to handle route %s", handle, route
            )

    def _register_l10n(self):
        l10n_class = self._find_l10n_class()
        l10n = l10n_class(self.config)
        if not isinstance(l10n, AbstractL10n):
            raise WrongL10nBase(l10n)

        self._l10n = l10n
        start_log.debug("Registered L10n class: %r", self._l10n)

    def _register_router(self):
        router_class = self._find_router_class()
        router = router_class()
        if not isinstance(router, AbstractRouter):
            raise WrongRouterBase(router)

        self._router = router

    def _register_session_handler(self):
        storage_class = self._find_session_handler()
        handler = storage_class(self.config)
        if not isinstance(handler, SessionStorage):
            raise WrongSessionHandlerBase(handler)

        self._session_handler = handler

    def _register_logger(self, config):
        initialize_loggers(config)

    def _register_view(self):
        view_kwargs = {
            "extra_functions": {
                "print_css": self._view_print_css,
                "print_js": self._view_print_js,
                "url_for": self._view_url_for,
            }
        }
        if self.config.getbool("pygrim:l10n", False):
            view_kwargs["translations"] = self._l10n.translations()

        self._views = {}
        for view_name, view_class in self._find_view_classes():
            view = view_class(self.config, **view_kwargs)
            if not isinstance(view, AbstractView):
                raise WrongViewBase(view)

            self._views[view_name] = view
            start_log.debug(
                "Registering view class %r.", get_instance_name(view)
            )

    def _set_dump_view(self, context):
        context.set_response_content_type("application/json")
        context.view_data.update(
            (key, getattr(context, key))
            for key
            in ("current_route", "session", "template", "_route_params")
        )
        context.set_view("json")

    def _set_fallback_view(self, context):
        context.set_view("dummy" if self._view_disabled() else "raw")

    def _setup_env(self):
        self._debug = self.config.getbool("pygrim:debug", True)
        self._default_view = (
            "dummy"
            if self._view_disabled()
            else self.config.get("view:default", "raw")
        )
        self._dump_switch = self.config.get("pygrim:dump_switch", "jkxd")
        self._static_map = {
            fix_trailing_slash(prefix): mapped_dir
            for prefix, mapped_dir
            in (
                map(string_strip, mapping.split("=", 1))
                for mapping
                in ensure_tuple(self.config.get("uwsgi:static-map", ()))
                if "=" in mapping
            )
        }
        locale = self.config.get("pygrim:locale", None)
        if locale:
            setlocale(LC_ALL, str(locale))
            start_log.debug("Locale 'LC_ALL' set to %r.", locale)

        start_log.debug("PyGrim environment set up.")

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
        # it is a bit faster than self._views.keys() == ["dummy"]
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
