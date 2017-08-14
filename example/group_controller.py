# coding: utf8

from pygrim2 import RouteGroup
from pygrim2 import route, template


class Group(object):

    _route_group = RouteGroup("/group")

    @route("GET", "/test")
    @template("layout.jinja")
    def group_test(self, context):
        return {
            "text": "This method is mapped to route in group."
        }
