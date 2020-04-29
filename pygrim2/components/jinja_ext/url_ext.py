from os import path

from jinja2.ext import Extension


class UrlExtension(Extension):

    def __init__(self, environment):
        super(UrlExtension, self).__init__(environment)
        environment.filters.update(self._get_filters())
        environment.globals.update(self._get_functions())

    def base_url(self, context):
        return "%s%s" % (
            context.get_request_url(), context.get_request_root_uri()
        )

    def site_url(self, context, site):
        return path.join(self.base_url(context), site.lstrip("/"))

    def srcset_width(self, target, path, sizes):
        return ", ".join([
            "/img/%s/%s/0/%s %sw" % (target, w, path, w)
            for w in sizes
        ])

    def _get_filters(self):
        return {
            "base_url": self.base_url,
            "site_url": self.site_url
        }

    def _get_functions(self):
        return {
            "base_url": self.base_url,
            "site_url": self.site_url,
            "srcset_width": self.srcset_width
        }
