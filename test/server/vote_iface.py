# coding: utf8

from logging import getLogger
from pygrim.decorators import method, template_method

log = getLogger(__file__)


class VoteIface(object):

    @template_method("polls.jinja", session=True)
    def polls_list(self, context, category_id=None, **kwargs):
        if category_id is None:
            category_id = context.GET('category_id')
        if category_id is None:
            data = {"category_empty": u"Kategorie Prázdná"}
        else:
            data = {"category_id": category_id}
        return {
            "data": data
        }

    @template_method('svety.jinja', session=True)
    def svety(self, context, world=None, time_range=None):
        return {
            "data": {
                "world": world,
                "time_range": time_range,
            }
        }

    @template_method('static_page.jinja', session=True)
    def static_page(self, context):
        return {"data": {}}

    @method(session=True)
    def redirect_url(self, context):
        self.redirect(context, url="/")

    @method()
    def redirect_with_param(self, context):
        self.redirect(
            context, route_name="hitparady",
            params={"category_id": 999}
        )

    @template_method('url_for.jinja')
    def url_for(self, context):
        return {"data": {}}
