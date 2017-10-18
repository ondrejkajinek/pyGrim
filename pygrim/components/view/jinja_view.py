# coding: utf8

from os import getcwd, path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .abstract_view import AbstractView
from ..utils.json2 import dumps as json_dumps

I18N_EXT_NAME = "pygrim.components.jinja_ext.i18n.I18NExtension"


def _suppress_none(self, variable):
    return (
        ""
        if variable is None
        else variable
    )

_suppress_none.contextfunction = True


class JinjaView(AbstractView):

    def __init__(self, config, extra_functions, translations=None, **kwargs):
        self._debug = config.getbool("jinja:debug", False)
        self._dump_switch = config.get("jinja:dump_switch", "jkxd")
        self._env = Environment(
            extensions=self._get_extensions(config),
            loader=FileSystemLoader(
                searchpath=path.join(
                    getcwd(),
                    config.get("jinja:template_path")
                )
            ),
            autoescape=select_autoescape(
                enabled_extensions=config.get(
                    "jinja:environment:autoescape",
                    ("jinja",)
                )
            ),
            auto_reload=config.get("jinja:environment:auto_reload", True)
        )
        self._translations = translations or {}

        if "url_for" in extra_functions:
            self._env.filters.update({
                "url_for": extra_functions["url_for"]
            })

        self._env.globals.update(extra_functions)
        if config.get("jinja:suppress_none"):
            self._env.finalize = _suppress_none

        self._initialize_assets(config)

    def get_template_directory(self):
        return self._env.loader.searchpath

    def render(self, context):
        if not context.template:
            raise RuntimeError(
                "Trying to render response but no template has been set."
            )

        if context.session is not None:
            context.view_data["flashes"] = context.session.get_flashes()

        context.view_data.update({
            "css": self._merge_assets(
                self._css, context.view_data.pop("extra_css", [])
            ),
            "debug": self._debug,
            "js_header_sync": self._merge_assets(
                self._js["header"]["sync"],
                context.view_data.pop("extra_js_header_sync", [])
            ),
            "js_header_async": self._merge_assets(
                self._js["header"]["async"],
                context.view_data.pop("extra_js_header_async", [])
            ),
            "js_footer_sync": self._merge_assets(
                self._js["footer"]["sync"],
                context.view_data.pop("extra_js_footer_sync", [])
            ),
            "js_footer_async": self._merge_assets(
                self._js["footer"]["async"],
                context.view_data.pop("extra_js_footer_async", [])
            )
        })

        if self._has_i18n() and context.get_language():
            self._env.install_gettext_translations(
                self._translations[context.get_language()]
            )

        if self._debug and self._dump_switch in context.GET():
            result = self._handle_dump(context)
        else:
            template = self._env.get_template(context.template)
            context.view_data.update({
                "context": context
            })
            result = template.render(**context.view_data)

            if context.session is not None:
                context.session.del_flashes()

        return result

    def _handle_dump(self, context):
        dump_data = context.view_data.copy()  # shallow copy
        dump_data["content_type"] = context._response.headers.get(
            "Content-Type"
        )
        dump_data["session"] = context.session
        dump_data["template_path"] = context.template

        context.set_response_content_type("application/json")
        return json_dumps(dump_data)

    def _has_i18n(self):
        return I18N_EXT_NAME in self._env.extensions

    def _get_extensions(self, config):
        extensions = set((
            "pygrim.components.jinja_ext.BaseExtension",
            "pygrim.components.jinja_ext.TimeExtension",
            "pygrim.components.jinja_ext.UrlExtension"
        ))
        extensions.update(
            config.get("jinja:extensions", ())
        )
        if config.getboolean("pygrim:i18n", False):
            extensions.update(("pygrim.components.jinja_ext.i18n",))

        return map(str, extensions)

    def _initialize_assets(self, config):
        self._css = config.get("assets:css", [])
        js_assets = config.get("assets:js", {})
        self._js = {
            "header": {
                "async": js_assets.get("header", {}).get("async", []),
                "sync": js_assets.get("header", {}).get("sync", [])
            },
            "footer": {
                "async": js_assets.get("footer", {}).get("async", []),
                "sync": js_assets.get("footer", {}).get("sync", [])
            }
        }

    def _merge_assets(self, first, second):
        merged = []
        seen = {}
        for item in first + second:
            if item not in seen:
                seen[item] = True
                merged.append(item)

        return merged
