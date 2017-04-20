# coding: utf8

from re import compile as re_compile
from pyGrim import Route


class Routes(object):

    def _route_register_func(self, router):
        router.map(Route(("GET",), "/", "index", "home"))
        router.map(Route(("GET",), "/index", "index"))
        router.map(Route(
            ("GET",),
            re_compile(r"/tpl_test/(?P<template>[^/]*)/"),
            "template_test"
        ))
        router.push_group("/konfigurator")
        router.map(Route(
            ("GET",),
            re_compile("/(?P<world>[a-z-_]+)"),
            "time_listing")
        )
        router.pop_group()
