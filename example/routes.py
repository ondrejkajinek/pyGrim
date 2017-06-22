# coding: utf8

from re import compile as re_compile
from pygrim import Route, RouteGroup


def register_routes(router):
    # string routes
    router.map(Route(("GET",), "/", "Test:home", "home"))
    router.map(Route("GET", "/second", "Second:home", "second_home"))
    router.map(Route("GET", "/session", "Test:session_text"))
    router.map(Route("GET", "/cookie_show", "Test:cookie_show"))
    router.map(Route("GET", "/cookie_set", "Test:cookie_set"))
    router.map(Route("GET", "/redirect", "Second:redirect"))
    router.map(Route("GET", "/model", "Second:model"))
    router.map(Route("GET", "/generator", "Second:generator"))
    router.map(Route("GET", "/generator_fction", "Second:generator_fction"))
    router.map(Route(
        "GET", "/broken_generator_fction", "Second:broken_generator_fction"
    ))
    router.map(
        Route("GET", "/template_display", "Test:use_template_display")
    )
    router.map(Route(
        "GET",
        "/template_method",
        "Test:use_template_method")
    )
    router.map(Route("GET", "/type_error", "Test:type_error"))
    router.map(Route("GET", "/runtime_error", "Test:runtime_error"))

    # regexp routes
    router.map(Route(
        "GET",
        re_compile(r"/template/(?P<template>[^/]+)"),
        "Test:template_show",
        "template_show"
    ))
    router.map(Route(
        "GET",
        re_compile(r"/message/(?P<message>[^/]+)"),
        "Second:message",
        "message"
    ))

    # route groups
    router.map(RouteGroup(
        "/group",
        (
            Route("GET", "/test", "Test:group_test"),
            RouteGroup(
                "inner_group",
                (
                    Route(
                        "GET",
                        re_compile(r"/test/(?P<param>[0-9]+)"),
                        "Test:int_inner_group_test"
                    ),
                    Route(
                        "GET",
                        re_compile(r"/test/(?P<param>[a-z]+)[^/]*"),
                        "Test:str_inner_group_test_pass"
                    ),
                    Route(
                        "GET",
                        re_compile(r"/test(/(?P<param>[a-z0-9]+))?"),
                        "Test:inner_group_test"
                    ),
                )
            )
        )
    ))
