# coding: utf8

from re import compile as re_compile

from pygrim import RouteGroup, RoutePassed
from pygrim import route, template
from group_controller import Group


class InnerGroup(Group):

    _route_group = Group._route_group + RouteGroup("/inner/test/")

    @route("GET", re_compile("/(?P<param>[0-9]+)"))
    @template("layout.jinja")
    def int_inner_group_test(self, context, param):
        return {
            "text": (
                "This method is mapped to route in inner group. "
                "Regexp route is used with integer parameter 'param'. "
                "Given value is: %r" % param
            )
        }

    @route("GET", re_compile("/(?P<param>[a-z]+)[^/]*"))
    def str_inner_group_test_pass(self, context, param=None):
        context.view_data.update({
            "previous_text": (
                "This method received route params %r. "
                "It does nothing but RoutePassed, so another matching route "
                "will be searched for." % context.get_route_params()
            )
        })
        raise RoutePassed()

    @route("GET", re_compile("/(?P<param>[a-z0-9]+)"))
    @template("layout.jinja")
    def inner_group_test(self, context, param=None):
        text = context.view_data.get("previous_text") or ""
        text += (
            "This method is mapped to route in inner group. "
            "Regexp route is used with optional parameter 'param'. "
            "Given value is: %r" % param
        )
        return {
            "text": text
        }
