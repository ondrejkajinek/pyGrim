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
