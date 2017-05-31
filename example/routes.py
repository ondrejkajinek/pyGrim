# coding: utf8

from re import compile as re_compile
from pygrim import Route, RouteGroup


class Routes(object):

    def _route_register_func(self, router):
        # string routes
        router.map(Route(("GET",), "/", "home", "home"))
        router.map(Route(("GET",), "/session", "session_text"))
        router.map(Route(("GET",), "/cookie_show", "cookie_show"))
        router.map(Route(("GET",), "/cookie_set", "cookie_set"))
        router.map(
            Route(("GET",), "/template_display", "use_template_display")
        )
        router.map(Route(("GET",), "/template_method", "use_template_method"))
        router.map(Route(("GET",), "/type_error", "type_error"))
        router.map(Route(("GET",), "/runtime_error", "runtime_error"))

        # regexp routes
        router.map(Route(
            ("GET",),
            re_compile(r"/template/(?P<template>[^/]+)"),
            "template_show"
        ))

        # route groups
        router.map(RouteGroup(
            "/group",
            (
                Route(("GET",), "/test", "group_test"),
                RouteGroup(
                    "inner_group",
                    (
                        Route(
                            ("GET",),
                            re_compile(r"/test/(?P<param>[0-9]+)"),
                            "int_inner_group_test"
                        ),
                        Route(
                            ("GET",),
                            re_compile(r"/test(/(?P<param>[^/]+))?"),
                            "inner_group_test"
                        ),
                    )
                )
            )
        ))
