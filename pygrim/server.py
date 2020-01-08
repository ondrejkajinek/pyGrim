# coding: utf8
from .components.config import AbstractConfig, YamlConfig
from .components.exceptions import (
    WrongConfigBase, WrongRouterBase, WrongSessionHandlerBase, WrongViewBase
)
from .components.log import initialize_loggers
from .components.routing import AbstractRouter, Route, Router
from .components.routing import (
    DispatchFinished, MissingRouteHandle, RouteNotRegistered, RoutePassed
)
from .components.session import (
    DummySession, FileSessionStorage, RedisSessionStorage,
    RedisSentinelSessionStorage, SessionStorage
)
from .components.utils import ensure_tuple, get_class_name, get_method_name
from .components.utils import remove_trailing_slash
from .components.view import AbstractView, DummyView, JinjaView
from .decorators import method
from .http import Context, Request, Response

from inspect import getmembers, ismethod, getmro
from jinja2 import escape, Markup
from json import dumps as json_dumps
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


def register_view_class(name, cls):
    if name in Server.KNOWN_VIEW_CLASSES:
        raise RuntimeError("")

    Server.KNOWN_VIEW_CLASSES[name] = cls


def register_session_handler(name, cls):
    if name in Server.KNOWN_SESSION_HANDLERS:
        raise RuntimeError("")

    Server.KNOWN_SESSION_HANDLERS[name] = cls


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
        "jinja": JinjaView
    }

    def __init__(self):
        self._initialize_basic_components()
        self._setup_env()
        self._methods = {}
        # temporary
        # self._not_found_methods will be changed to tuple
        # during postfork-time method _collect_exposed_methods
        self._not_found_methods = {}
        self._error_method = self._default_error_method
        self._custom_error_handlers = {}
        self._context_class = Context
        self._requst_class = Request
        self._response_class = Response

    def __call__(self, environment, start_response):
        start_response = ResponseWrap(start_response)
        context = self._context_class(
            environment, self.config, self._requst_class, self._response_class,
            debug=self._debug
        )
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

            # to keep errors and other cases iteration should stay where it is
            body = context.get_response_body()
            if context.generates_response():
                do_yield = not context.is_request_head()
                parts = body() if context.is_generator_function() else body
                for part in parts:
                    if do_yield:
                        yield part
            elif context.is_request_head():
                log.debug("HEAD - not returning body")
            else:
                yield body
            # endif
        return

    def display(self, *args, **kwargs):
        self.view.display(*args, **kwargs)
        raise DispatchFinished()

    def get_config_dir(self):
        return self._config_dir

    def redirect(self, context, **kwargs):
        if "route_name" in kwargs:
            url = "".join((
                context.get_request_url(),
                self.router.url_for(
                    kwargs.pop("route_name"),
                    kwargs.pop("params", None) or {}
                )
            ))
            # safety
            kwargs.pop("url", None)
        elif "url" in kwargs:
            url = kwargs.pop("url")
            # safety
            kwargs.pop("route_name", None)
        else:
            raise RuntimeError("Redirect needs 'url' or 'route_name' param.")

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

    def set_context_class(self, new_class):
        self._set_internal_class("_context_class", new_class, Context)

    def set_request_class(self, new_class):
        self._set_internal_class("_requst_class", new_class, Request)

    def set_response_class(self, new_class):
        self._set_internal_class("_response_class", new_class, Response)

    def _collect_exposed_methods(self):
        for unused_, member in getmembers(self, predicate=ismethod):
            if getattr(member, "_exposed", False) is True:
                self._process_exposed_method(member)

        if ("", 0) not in self._not_found_methods:
            self._not_found_methods[("", 0)] = self._default_not_found_method

        self._finalize_not_found_handlers()

    def _default_error_method(self, context, exc):
        log.exception(exc.message)
        context.set_response_body("Internal Server Error")
        context.set_response_status(500)

    def _default_not_found_method(self, context):
        context.set_response_body("Not found")
        context.set_response_status(404)

    def _dump_request(self, context):
        log.error(
            "Error occured during request handling. Request details: %s",
            context.dump_request()
        )

    def _finalize_not_found_handlers(self):
        self._not_found_methods = tuple(
            (prefix, priority, self._not_found_methods[(prefix, priority)])
            for prefix, priority
            in sorted(
                self._not_found_methods.keys(),
                key=lambda x: x[0].count("/") * 10000 + x[1],
                reverse=True
            )
        )

    def _finalize_routes(self):
        for route in self.router.get_routes():
            try:
                method = self._methods[route.get_handle_name()]
            except KeyError:
                raise MissingRouteHandle(
                    route._handle_name,
                    route.get_name() or route.pattern
                )
            else:
                route.assign_method(method)
                log.debug(
                    "Method '%s' registered to handle route '%s'",
                    get_method_name(method),
                    route.pattern
                )

    def _find_config_class(self):
        for key in self.KNOWN_CONFIG_FORMATS:
            if key in uwsgi_opt:
                self._config_dir = path.dirname(uwsgi_opt[key])
                if not self._config_dir:
                    self._config_dir = uwsgi_opt["chdir"] + "conf/"
                    uwsgi_opt[key] = self._config_dir + uwsgi_opt[key]
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

    def _find_view_class(self):
        view_type = (
            self.config.get("view:type")
            if self.config.getboolean("view:enabled", True)
            else DummyView
        )
        try:
            view_class = self.KNOWN_VIEW_CLASSES[view_type]
        except KeyError:
            raise RuntimeError("Unknown view class: %r.", view_class)

        return view_class

    def load_session(self, context):
        context.load_session(self.session_handler)

    @method(session=False)
    def status_alive(self, context):
        context.set_response_content_type("application/json")
        context.set_response_body(json_dumps({
            "status": 200,
            "status_message": "OK",
            "system_alive": 1
        }))

    def _handle_by_route(self, route, context):
        if route.requires_session():
            self.load_session(context)

        try:
            route.dispatch(context=context)
        except DispatchFinished:
            pass
        except RoutePassed:
            raise

        log.debug("Dispatch succeded on: %r.", context.current_route)
        if context.session_loaded():
            context.save_session(self.session_handler)

    def _handle_error(self, context, exc):
        log.exception(
            "Error while dispatching to: %r.",
            (
                context.current_route._handle_name
                if context.current_route
                else "<no route>"
            )
        )
        try:

            for one in getmro(exc.__class__):
                log.debug("Looking up error handler for %r.", one)
                if one in self._custom_error_handlers:
                    log.debug("Found error handler for %r.", one)
                    handle = self._custom_error_handlers[one]
                    try:
                        handle(context=context, exc=exc)
                    except DispatchFinished:
                        pass
                    if getattr(handle, "_save_session", False):
                        context.save_session(self.session_handler)
                    raise DispatchFinished()
            self._error_method(context=context, exc=exc)
            raise DispatchFinished()
        except DispatchFinished:
            self._dump_request(context)
            return
        except:
            exc = exc_info()[1]

        try:
            self._default_error_method(context=context, exc=exc)
        except DispatchFinished:
            self._dump_request(context)
            return
        except:
            log.critical("Error in default_error_method.")
            log.exception("Error in default_error_method.")
            raise

    def _handle_not_found(self, context):
        context.current_route = None
        log.debug(
            "No route found to handle request %r.",
            context.get_request_uri()
        )
        try:
            request_uri = context.get_request_uri()
            request_suffix = path.splitext(request_uri)[1]
            if request_suffix in self._plain_not_found_suffixes:
                self._default_not_found_method(context)
            else:
                for prefix, priority, handle in self._not_found_methods:
                    if request_uri.startswith(prefix):
                        log.debug(
                            "Using %r %r %r for not_found handling %r",
                            prefix, priority, handle, request_uri
                        )
                        if not context.session and handle._session:
                            self.load_session(context)
                        try:
                            handle(context=context)
                        except RoutePassed:
                            log.debug(
                                "Not used %r %r %r for not_found on %r",
                                prefix, priority, handle, request_uri
                            )
                            continue
                        except DispatchFinished:
                            pass
                        if context.session_loaded():
                            context.save_session(self.session_handler)
                        break
        except DispatchFinished:
            pass

        log.debug("Not found state handled.")

    def _handle_request(self, context):
        try:
            for route in self.router.matching_routes(context):
                try:
                    self._handle_by_route(route=route, context=context)
                    break
                except RoutePassed:
                    continue
            else:
                self._handle_not_found(context=context)
        except:
            self._handle_error(context=context, exc=exc_info()[1])

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

    def _load_translations(self):
        from gettext import translation as gettext_translation

        i18n_kwargs = {
            "domain": self.config.get("pygrim:i18n:lang_domain"),
            "localedir": path.join(
                self.config.get("uwsgi:chdir"),
                self.config.get("pygrim:i18n:locale_path")
            )
        }
        translations = {}
        for lang in self.config.get("pygrim:i18n:locales"):
            i18n_kwargs["languages"] = (lang,)
            try:
                translation = gettext_translation(**i18n_kwargs)
            except IOError:
                msg = "No translation file found for language %r in domain %r"
                log.error(msg, lang, i18n_kwargs["domain"])
                raise RuntimeError(msg % (lang, i18n_kwargs["domain"]))
            else:
                translations[lang] = translation

        try:
            default_locale = self.config.get("pygrim:i18n:default_locale")
        except KeyError:
            raise
        else:
            if default_locale not in translations:
                msg = "Default locale %r is not enabled. Known locales: %r"
                log.error(msg, default_locale, translations.keys())
                raise RuntimeError(msg % (default_locale, translations.keys()))

        log.debug("Loaded translations: %r", translations.keys())
        log.debug("Default translation: %r", default_locale)
        return translations

    def _process_custom_error_handler(self, method, err_cls):
        if err_cls in self._custom_error_handlers:
            raise RuntimeError(
                "Duplicate handling of error %r with %r and %r.",
                err_cls, self._custom_error_handlers[err_cls], method
            )
        log.debug("Registered %r to handle %r.", method, err_cls)
        self._custom_error_handlers[err_cls] = method

    def _process_error_handler(self, method):
        log.debug("Method %r registered as default exception handler", method)
        self._error_method = method

    def _process_exposed_method(self, method):
        self._methods[method._dispatch_name] = method

        for (prefix, priority) in getattr(method, "_not_found", ()):
            self._process_not_found_method(method, prefix, priority)

        if getattr(method, "_error", False) is True:
            self._process_error_handler(method)

        for err_cls in getattr(method, "_custom_error", ()):
            self._process_custom_error_handler(method, err_cls)

    def _process_not_found_method(self, method, prefix, priority=0):
        key = (prefix, priority)
        if key in self._not_found_methods:
            raise RuntimeError(
                "Duplicate handling of not-found %r with %r and %r.",
                key, self._not_found_methods[key], method
            )
        log.debug("Method %r registered to handle not-found state", method)
        self._not_found_methods[key] = method

    def _register_router(self):
        router_class = self._find_router_class()
        router = router_class()
        if not isinstance(router, AbstractRouter):
            raise WrongRouterBase(router)

        self.router = router

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
        view_class = self._find_view_class()

        view_kwargs = {
            "extra_functions": {
                "print_css": self._jinja_print_css,
                "print_js": self._jinja_print_js,
                "static_file": self._jinja_static_file,
                "static_file_exists": self._jinja_static_file_exists,
                "url_for": self._jinja_url_for,
            }
        }
        if self.config.getboolean("pygrim:i18n", False):
            view_kwargs["translations"] = self._load_translations()

        view = view_class(self.config, **view_kwargs)
        if not isinstance(view, AbstractView):
            raise WrongViewBase(view)

        self.view = view

    def _setup_env(self):
        self._debug = self.config.getbool("pygrim:debug", True)
        self._plain_not_found_suffixes = set(
            "." + suffix.lstrip(".")
            for suffix
            in self.config.get("pygrim:plain_not_found", ())
        )
        self._static_map = {
            remove_trailing_slash(prefix) + "/": mapped_dir
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
            log.debug("Setting locale 'LC_ALL' to %r", locale)
            setlocale(LC_ALL, str(locale))

        try:
            system_alive = (
                "/" + self.config.get("pygrim:system_alive").lstrip("/")
            )
        except (AttributeError, KeyError):
            log.warning(
                "pygrim:system_alive is not configured! "
                "Default /system_alive will be used. "
                "Please check if there is no route clash."
            )
            system_alive = "/system_alive"

        if system_alive:
            self.router.map(Route(
                ("GET", "POST"), system_alive, "status_alive"
            ))

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
        for dir_prefix, dir_abs_path in self._static_map.iteritems():
            if static_normpath.startswith(dir_prefix):
                static_relpath = path.relpath(static_normpath, dir_prefix)
                if path.isfile(path.join(dir_abs_path, static_relpath)):
                    yield dir_prefix, static_relpath

    def _static_file_abs_path(self, static_file):
        try:
            dir_prefix, static_relpath = next(
                self._static_file_info(static_file)
            )
            abs_path = path.join(self._static_map[dir_prefix], static_relpath)
        except StopIteration:
            abs_path = None

        return abs_path

    # jinja extra methods
    def _jinja_print_css(self, css_list, **kwargs):
        return Markup("\n".join(
            """<link href="%s" rel="stylesheet" type="text/css" %s/>""" % (
                self._versioned_file(css),
                " ".join(
                    """%s="%s\"""" % (key, value)
                    for key, value
                    in kwargs.iteritems()
                )
            )
            for css
            in css_list
        ))

    def _jinja_print_js(self, js_list, sync=True, *args, **kwargs):
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
                in kwargs.iteritems()
            )
            scripts.append("<script %s></script>" % (" ".join(attrs),))

        return Markup("\n".join(scripts))

    def _jinja_static_file(self, filename, prefixes):
        if isinstance(filename, basestring):
            filenames = [filename]
        else:
            filenames = filename
        for prefix in prefixes:
            for filename in filenames:
                filename = filename.lstrip("/")
                file_path = next(
                    (
                        path.join(dir_pfx, static_relpath)
                        for dir_pfx, static_relpath in self._static_file_info(
                            path.join(prefix, filename) if prefix else filename
                        )
                    ),
                    None
                )
                if file_path:
                    break
            if file_path:
                break
        if not file_path:
            if self._debug:
                raise RuntimeError("File %r could not be found in %r" % (
                    filenames, prefixes
                ))
            else:
                log.error(
                    "File %r not present in static-map: %r",
                    filenames, prefixes
                )
                file_path = ""

        return file_path

    def _jinja_static_file_exists(self, filename, prefixes=None):
        if isinstance(filename, basestring):
            filenames = [filename]
        else:
            filenames = filename
        if prefixes is None:
            prefixes = ("",)
        for prefix in prefixes:
            prefix = prefix or "/"
            for filename in filenames:
                filename = filename.lstrip("/")
                file_path = next(
                    (
                        path.join(dir_pfx, static_relpath)
                        for dir_pfx, static_relpath in self._static_file_info(
                            path.join(prefix, filename)
                        )
                    ),
                    None
                )
                if file_path:
                    break
            if file_path:
                break
        return bool(file_path)

    def _jinja_url_for(self, route, params=None):
        params = params or {}
        try:
            url = self.router.url_for(route, params)
        except RouteNotRegistered:
            if self._debug:
                raise
            else:
                log.error("Route not registered: %r", route)
                url = "#"

        return url

    def _versioned_file(self, static_file):
        timestamp = (
            None
            if self.view._debug
            else self.view.timestamp_cache.get(static_file)
        )
        if timestamp is None:
            abs_path = self._static_file_abs_path(static_file)
            if abs_path and path.isfile(abs_path):
                timestamp = int(path.getmtime(abs_path))
                if not self.view._debug:
                    self.view.timestamp_cache[static_file] = timestamp

        return (
            "%s?v=%d" % (escape(static_file), timestamp)
            if timestamp
            else escape(static_file)
        )
