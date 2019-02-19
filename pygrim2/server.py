# std
from collections import OrderedDict
from inspect import getmembers, isclass, ismethod, getmro
from locale import LC_ALL, setlocale
from logging import getLogger
from os import path
from sys import exc_info

# non-std
from jinja2 import escape, Markup
try:
    from uwsgi import opt as uwsgi_opt
except ImportError:
    uwsgi_opt = {}

# local
from .components.config import AbstractConfig, JsonConfig, YamlConfig
from .components.exceptions import (
    ComponentTypeAlreadyRegistered, ControllerAttributeCollision,
    DuplicateContoller, UnknownView,
    WrongConfigBase, WrongL10nBase, WrongRouterBase, WrongSessionHandlerBase,
    WrongViewBase
)
from .components.containers import AttributeDict
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
    ensure_tuple, get_instance_name, get_class_name, get_method_name,
    remove_trailing_slash
)
from .components.view import (
    AbstractView, DummyView, DumpView, JsonView, JinjaView, RawView
)
from .http import Context, HeadersAlreadySent, Request, Response


start_log = getLogger("pygrim_start.server")
log = getLogger("pygrim.server")


def _register_component_type(name, cls, server_attr_name, component_name):
    server_attr = getattr(Server, server_attr_name)
    # TODO: what is faster, if name in server_attr, or try-except
    #       name collision is not happening in production env.
    if name in server_attr:
        raise ComponentTypeAlreadyRegistered(
            component_name, name, server_attr[name]
        )

    server_attr[name] = cls


def register_config_format(name, cls):
    _register_component_type(name, cls, "Config", "KNOWN_CONFIG_FORMATS")


def register_l10n_class(name, cls):
    _register_component_type(name, cls, "L10n", "KNONW_L10N_CLASSES")


def register_session_handler(name, cls):
    _register_component_type(
        name, cls, "SessionHandler", "KNOWN_SESSION_HANDLERS"
    )


def register_view_class(name, cls):
    _register_component_type(name, cls, "View", "KNOWN_VIEW_CLASSES")


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
        "json": JsonConfig,
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
        "dump": DumpView,
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
        self._context_class = Context
        self._request_class = Request
        self._response_class = Response

    def __call__(self, environment, start_response):
        context = self._context_class(
            self.config,
            self._model,
            self._session_handler,
            self._l10n,
            self._request_class(environment),
            self._response_class()
        )
        context.set_view(self._default_view)

        try:
            self._handle_request(context=context)
        except BaseException:
            context.set_response_body("Fatal Server Error")
            context.set_response_status(500)
            context.delete_response_headers()
            self._set_fallback_view(context)
        else:
            context.finalize_response()

        start_response = ResponseWrap(start_response)
        start_response(
            context.get_response_status_code(),
            context.get_response_headers()
        )
        return self._send_response(context)

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

    def get_config_dir(self):
        return self._config_dir

    def set_context_class(self, new_class):
        self._set_internal_class("_context_class", new_class, Context)

    def set_request_class(self, new_class):
        self._set_internal_class("_requst_class", new_class, Request)

    def set_response_class(self, new_class):
        self._set_internal_class("_response_class", new_class, Response)

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
        start_log.debug(
            "Controller %r registered", get_instance_name(controller)
        )

    def register_model(self, model_class):
        if self._model is not None:
            start_log.warning(
                "Model is already registered: %r",
                get_instance_name(self._model)
            )

        if isclass(model_class):
            self._model = model_class(self.config)
        else:
            # Compat with < 2.1.1 version of pyGrim
            log.warning(
                "You are using the 'old' register_model interface. "
                "From 2.1.1, register_model should get model class instead of "
                "its instance, and model constructor must accept server "
                "config as its only argument."
            )
            self._model = model_class

        # Rewrite _model in controllers that were registered so far,
        # destroying original one
        for controller in self._controllers.values():
            controller._model = self._model

    def _default_error_handler(self, context, exc):
        log.exception(exc.message)
        context.set_response_body("Internal Server Error")
        context.set_response_status(500)
        self._set_fallback_view(context)

    def _default_not_found_handler(self, context, exc):
        context.set_response_body("Not found")
        context.set_response_status(404)
        self._set_fallback_view(context)

    def _dump_request(self, context):
        log.error(
            "Fatal error occured during request handling. Request details: %s",
            context.dump_request()
        )

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
                self._config_dir = path.dirname(uwsgi_opt[key])
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
        storage_type = self.config.get("session:type", "file")
        try:
            storage_class = self.KNOWN_SESSION_HANDLERS[storage_type]
        except KeyError:
            raise RuntimeError("Unknown session handler: %r.", storage_type)
        else:
            if storage_type == "dummy":
                start_log.warning("Session is disabled!")

        return storage_class

    def _find_view_classes(self):
        view_types = self.config.getset("view:types", ("jinja",))
        # view is disabled when only dummy view is configured
        if view_types == ("dummy",):
            start_log.info("View is disabled, no output will be created!")
        else:
            view_types.update(("raw", "json"))

        if self.config.get("pygrim:dump_switch", "jkxd"):
            view_types.update(("dump",))

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
            self._dump_request(context)
        except StopDispatch:
            raise
        except BaseException:
            exc = exc_info()[1]
            try:
                self._default_error_handler(context=context, exc=exc)
                self._dump_request(context)
            except BaseException:
                log.critical("Error in default_error_handler.")
                log.exception("Error in default_error_handler.")
                raise

    def _handle_generic_error(self, context, exc):
        request_uri = context.get_request_uri()
        for handler in self._matching_error_handlers(
            request_uri, getmro(exc.__class__)
        ):
            try:
                handler(context=context, exc=exc)
            except RoutePassed:
                continue

            log.debug(
                "Error %r handled with %r.",
                get_class_name(exc.__class__), get_method_name(handler)
            )
            if getattr(handler, "_save_session", False):
                context.set_save_session(True)

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
                request_suffix = path.splitext(
                    context.get_request_uri()
                )[1]
                if request_suffix in self._plain_not_found_suffixes:
                    self._default_not_found_handler(context=context, exc=exc)
                else:
                    self._handle_not_found(context=context, exc=exc)
            finally:
                self._prepare_output(context)
        except StopDispatch:
            pass
        except BaseException:
            try:
                log.exception(
                    "Error while dispatching to: %r.",
                    context.current_route.get_handle_name()
                )
                context.current_route = NoRoute()
                context.set_save_session(False)
                self._handle_error(context=context, exc=exc_info()[1])
            except StopDispatch:
                pass
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
                if request_uri.startswith(prefix) and exc == err_cls:
                    yield handler

    def _prepare_output(self, context):
        if self._debug and self._dump_switch in context.GET():
            self._use_dump_view(context)

        try:
            view = self._views[context.get_view()]
        except KeyError as unknown_view:
            raise UnknownView(unknown_view)
        else:
            try:
                view.display(context)
            except BaseException:
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
                "Method %r registered to handle route %s",
                get_method_name(handle), route
            )

    def _register_l10n(self):
        l10n_class = self._find_l10n_class()
        l10n = l10n_class(self.config)
        if not isinstance(l10n, AbstractL10n):
            raise WrongL10nBase(l10n)

        self._l10n = l10n
        start_log.debug("Registered L10n class %r", get_instance_name(l10n))

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
            },
            "l10n": self._l10n
        }
        self._views = {}
        for view_name, view_class in self._find_view_classes():
            view = view_class(self.config, **view_kwargs)
            if not isinstance(view, AbstractView):
                raise WrongViewBase(view)

            self._views[view_name] = view
            start_log.debug(
                "Registering view class %r.", get_instance_name(view)
            )

    def _route_dump(self, context):
        self._set_json_view(context, "json")
        context.view_data = {
            "routes": [
                route._asdict()
                for route
                in self._router.get_routes()
            ]
        }

    def _send_response(self, context):
        is_head = context.is_request_head()
        if is_head:
            log.debug("This is HEAD request, not returning body.")

        try:
            if context.generates_response():
                for part in context.get_response_body():
                    if not is_head:
                        yield(
                            part
                            if isinstance(part, bytes)
                            else str(part).encode("utf8")
                        )
            elif not is_head:
                yield context.get_response_body()
        except HeadersAlreadySent as exc:
            yield "CRITICAL ERROR WHEN SENDING RESPONSE: %s" % exc
            for key, value in context.get_response_headers():
                if key == "content-length":
                    yield(" " * int(value)).encode("utf8")
                    break
        else:
            context.save_session()

    def _set_fallback_view(self, context):
        context.set_view("dummy" if self._view_disabled() else "raw")

    def _set_json_view(self, context, view):
        context.set_response_content_type("application/json")
        context.set_view(view)

    def _setup_env(self):
        self._debug = self.config.getbool("pygrim:debug", True)
        self._default_view = (
            "dummy"
            if self._view_disabled()
            else self.config.get("view:default", "raw")
        )
        self._dump_switch = self.config.get("pygrim:dump_switch", "jkxd")
        self._plain_not_found_suffixes = set(
            "." + suffix.lstrip(".")
            for suffix
            in self.config.get("pygrim:plain_not_found", ())
        )
        self._static_check = [
            remove_trailing_slash(prefix)
            for prefix
            in ensure_tuple(self.config.get("uwsgi:check-static", ()))
        ]
        self._static_map = OrderedDict(
            (remove_trailing_slash(prefix) + "/", mapped_dir)
            for prefix, mapped_dir
            in (
                [part.strip() for part in mapping.split("=", 1)]
                for mapping
                in ensure_tuple(self.config.get("uwsgi:static-map", ()))
                if "=" in mapping
            )
        )
        locale = self.config.get("pygrim:locale", None)
        if locale:
            setlocale(LC_ALL, str(locale))
            start_log.debug("Locale 'LC_ALL' set to %r.", locale)

        route_dump = self.config.get("pygrim:route_dump", None)
        if route_dump and self._debug:
            self._router.map(Route(
                ("GET", "POST"), "/" + route_dump.lstrip("/"), self._route_dump
            ))

        try:
            system_alive = self.config.get("pygrim:system_alive")
        except KeyError:
            log.warning(
                "pygrim:system_alive is not configured! "
                "Default /system_alive will be used. "
                "Please check if there is no route clash."
            )
            system_alive = "system_alive"

        if system_alive:
            self._router.map(Route(
                ("GET", "POST"), "/" + system_alive, self._status_alive
            ))

        start_log.debug("PyGrim environment set up.")

    def _set_internal_class(self, attr_name, new_class, required_parent):
        if issubclass(new_class, required_parent):
            setattr(self, attr_name, new_class)
        else:
            log.warning(
                "Given class %r is not subclass of %r",
                get_class_name(new_class), get_class_name(required_parent)
            )

    def _static_file_info(self, static_path):
        static_normpath = path.normpath(static_path)
        for dir_prefix, dir_abs_path in self._static_map.items():
            if static_normpath.startswith(dir_prefix):
                file_path = path.join(
                    dir_abs_path,
                    path.relpath(static_normpath, dir_prefix)
                )
                if path.isfile(file_path):
                    yield path.join(file_path)

        for dir_prefix in self._static_check:
            file_path = path.join(
                dir_prefix,
                static_normpath.lstrip("/")
            )
            if path.isfile(file_path):
                yield path.join(file_path)

    def _static_file_abs_path(self, static_file):
        try:
            abs_path = next(self._static_file_info(static_file))
        except StopIteration:
            abs_path = None

        return abs_path

    def _status_alive(self, context):
        self._set_json_view(context, "json")
        context.view_data = {
            "alive": True
        }

    def _use_dump_view(self, context):
        context.view_data["content_type"] = context._response.headers.get(
            "Content-Type"
        )
        context.view_data.update(
            ("__" + key, getattr(context, key))
            for key
            in ("current_route", "template", "_route_params")
        )
        if context.session_loaded():
            context.view_data["session"] = context.session

        self._set_json_view(context, "dump")

    def _versioned_file(self, static_file):
        abs_path = self._static_file_abs_path(static_file)
        return (
            "%s?v=%d" % (escape(static_file), int(path.getmtime(abs_path)))
            if abs_path and path.isfile(abs_path)
            else escape(static_file)
        )

    def _view_disabled(self):
        # it is a bit faster than self._views.keys() == ["dummy"]
        return len(self._views) == 1 and "dummy" in self._views

    # jinja extra methods
    def _view_print_css(self, css_list, **kwargs):
        return Markup("\n".join(
            """<link href="%s" rel="stylesheet" type="text/css" %s/>""" % (
                self._versioned_file(css),
                " ".join(
                    """%s="%s\"""" % (key, value)
                    for key, value
                    in kwargs.items()
                )
            )
            for css
            in css_list
        ))

    def _view_print_js(self, js_list, sync=True, *args, **kwargs):
        if sync is False:
            log.warning(
                "print_js parameter sync is deprecated. "
                "If you need async JS, call 'print_js(js_list, \"async\")' "
                "instead.\n"
                "In some future release, sync parameter will be removed."
            )
            args += ("async",)
        elif sync == "async":
            args += ("async",)

        scripts = []
        for js in js_list:
            attrs = ("src=\"%s\"" % (self._versioned_file(js),),)
            attrs += args
            attrs += tuple(
                """%s="%s\"""" % (key, value)
                for key, value
                in kwargs.items()
            )
            scripts.append("<script %s></script>" % (" ".join(attrs),))

        return Markup("\n".join(scripts))

    def _view_static_file(self, filename, prefixes):
        filename = filename.lstrip("/")
        try:
            file_path = next(
                (
                    file_path
                    for prefix in prefixes
                    for file_path in self._static_file_info(
                        path.join(prefix, filename)
                    )
                )
            )
        except StopIteration:
            if self._debug:
                raise RuntimeError("File %r could not be found in %r" % (
                    filename, prefixes
                ))
            else:
                file_path = ""

        return file_path

    def _view_url_for(self, route, params=None):
        params = params or {}
        try:
            url = self._router.url_for(route, params)
        except RouteNotRegistered:
            if self._debug:
                raise
            else:
                url = "#"

        return url
