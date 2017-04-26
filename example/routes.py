# coding: utf8

from re import compile as re_compile
from pyGrim import Route, RouteGroup


class Routes(object):

    def _route_register_func(self, router):
        router.map(Route(("GET",), "/", "index", "home"))
        router.map(Route(("GET",), "/test", "test_cookie"))
        router.map(Route(("GET",), "/test2", "test_cookie"))
        router.map(Route(("GET",), "/internal_server_error", "ise"))
        router.map(Route(
            ("GET",),
            re_compile(r"/tpl_test/(?P<template>[^/]*)/"),
            "template_test"
        ))
        router.map(RouteGroup(
            "/konfigurator",
            [
                Route(
                    ("GET",),
                    re_compile("/(?P<world>[a-z-_]+)"),
                    "time_listing"
                ),
                RouteGroup(
                    "/asdf",
                    [
                        Route(
                            ("GET",),
                            re_compile("/(?P<world>[a-z-_]+)"),
                            "time_listing"
                        ),
                    ]
                )
            ]
        ))
        router.pop_group()
