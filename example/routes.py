# coding: utf8

from re import compile as re_compile
from pygrim import Route, RouteGroup


class Routes(object):

    def _route_register_func(self, router):
        # string routes
        router.map(Route(("GET",), "/", "Test:home", "home"))
        router.map(Route(("GET",), "/session", "Test:session_text"))
        router.map(Route(("GET",), "/cookie_show", "Test:cookie_show"))
        router.map(Route(("GET",), "/cookie_set", "Test:cookie_set"))
        router.map(
            Route(("GET",), "/template_display", "Test:use_template_display")
        )
        router.map(Route(
            ("GET",),
            "/template_method",
            "Test:use_template_method")
        )
        router.map(Route(("GET",), "/type_error", "Test:type_error"))
        router.map(Route(("GET",), "/runtime_error", "Test:runtime_error"))

        # regexp routes
        router.map(Route(
            ("GET",),
            re_compile(r"/template/(?P<template>[^/]+)"),
            "Test:template_show",
            "template_show"
        ))

        # route groups
        router.map(RouteGroup(
            "/group",
            (
                Route(("GET",), "/test", "Test:group_test"),
                RouteGroup(
                    "inner_group",
                    (
                        Route(
                            ("GET",),
                            re_compile(r"/test/(?P<param>[0-9]+)"),
                            "Test:int_inner_group_test"
                        ),
                        Route(
                            ("GET",),
                            re_compile(r"/test(/(?P<param>[^/]+))?"),
                            "Test:inner_group_test"
                        ),
                    )
                )
            )
        ))
