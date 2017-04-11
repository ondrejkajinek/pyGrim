# coding: utf8

import inspect
import sys

from .components import DependencyContainer, Router, View
from .configuration import config
from logging import getLogger
from .http import Request, Response
from os import path
from .router_exceptions import RouteDispatched, RouteNotFound, RoutePassed


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

    def __init__(self):
        self._initialize_basic_components()
        self._methods = {}
        self._not_found_method = None

    # TODO: put decorators
    def __call__(self, environment, start_response):
        """
        called when request comes
        """
        start_response = ResponseWrap(start_response)
        response = self._handle_request(Request(environment))
        response.finalize()
        start_response(response.status_code(), response.headers)
        """
        yield response.body
        return
        """
        return tuple(response.body)

    # napojit na postfork
    def do_postfork(self):
        self._collect_exposed_methods()
        if hasattr(self, "_route_register_func"):
            self._route_register_func(self._dic.router)
            self._finalize_routes()
        else:
            log.warning("No function for registering routes found!")

        if hasattr(self, "postfork"):
            self.postfork()

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

    def _default_error_method(self, request, response, exc):
        from traceback import print_exc
        print_exc()
        log.exception(exc.message)
        response.body = "TODO: Internal Server Error"
        response.status = 500

    def _finalize_routes(self):
        for route in self._dic.router.get_routes():
            try:
                method = self._methods[route.get_handle_name()]
            except KeyError:
                raise RuntimeError(
                    u"Server nemá metodu %s pro obsluhu routy %s" % (
                        route._handle_name,
                        route.get_name() or str(route.get_pattern())
                    )
                )
            else:
                route.assign_method(method)

    def _handle_request(self, request):
        response = Response()
        try:
            for route in self._dic.router.matching_routes(request):
                try:
                    route.dispatch(request, response)
                    raise RouteDispatched()
                except RoutePassed:
                    pass
            else:
                if self._not_found_method:
                    self._not_found_method(request, response)
                else:
                    raise RouteNotFound()
        except RouteDispatched:
            # everything was ok
            pass
        except RouteNotFound:
            response.body = "Not found"
            response.status = 404
        except:
            exc = sys.exc_info()[1]
            if hasattr(self, "_error_method"):
                try:
                    self._error_method(request, response, exc)
                    return response
                except:
                    exc = sys.exc_info()[1]

            self._default_error_method(request, response, exc)

        return response

    def _initialize_basic_components(self):
        self._dic = DependencyContainer()

        self._dic.config = config
        self._dic.mode = config.get("grim.mode")
        self._dic.router = Router()
        # TODO: config
        # if config.getboolean("view.enabled", True):
        if config.get("view.enabled", True):
            self._register_view()

    def _register_view(self):
        self._dic.view = View(config, None)

    # jinja extra methods
    def _jinja_base_url(self):
        return "%s%s" % ("request.get_url()", "request.get_root_uri()")

    def _jinja_site_url(self, site):
        return path.join(self._jinja_base_url(), site)

    def _jinja_url_for(self, route, params=None):
        params = params or {}
        return "%s%s" % (
            "NEED request._request_uri",
            self._dic.router.url_for(route, params)
        )
