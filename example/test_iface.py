# coding: utf8

from pyGrim import method


class Test(object):

    @method
    def index(self, request, response):
        data = {
            "text": u"Hello, index here! :)"
        }
        self._dic.view.display(
            "layout.jinja", data, request, response
        )
