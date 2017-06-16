# coding: utf8

from .abstract_view import AbstractView
from ..utils.json2 import dumps as json_dumps
from jinja2 import Environment, FileSystemLoader, select_autoescape
from os import getcwd, path


def _suppress_none(self, variable):
    return (
        ""
        if variable is None
        else variable
    )

_suppress_none.contextfunction = True


class JinjaView(AbstractView):

    def __init__(self, config, extra_functions):
        self._debug = config.get("jinja:debug", False)
        self._dump_switch = config.get("jinja:dump_switch", "jkxd")
        auto_reload = config.get("jinja:environment:auto_reload", True)
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
            auto_reload=auto_reload,
        )
        self._env.filters.update({
            "url_for": extra_functions["url_for"]
        })
        self._env.globals.update(extra_functions)
        if config.get("jinja:suppress_none"):
            self._env.finalize = _suppress_none

        self._initialize_assets(config)
        self._initialize_extensions(config)

    def get_template_directory(self):
        return self._env.loader.searchpath

    def render(self, context):
        if not context.template:
            raise RuntimeError(
                "Trying to render response but no template has been set."
            )

        if context.session is not None:
            context.view_data["flashes"] = context.session.get_flashes()

        if self._debug and self._dump_switch in context.GET():
            context.view_data["template_path"] = context.template
            context.template = self._dump_switch

        context.view_data.update({
            "css": tuple(self._css | set(
                set(context.view_data.pop("extra_css", ()))
            )),
            "debug": self._debug,
            "js_header_sync": tuple(self._js["header"]["sync"] | set(
                context.view_data.pop("extra_js_header_sync", ())
            )),
            "js_header_async": tuple(self._js["header"]["async"] | set(
                context.view_data.pop("extra_js_header_async", ())
            )),
            "js_footer_sync": tuple(self._js["footer"]["sync"] | set(
                context.view_data.pop("extra_js_footer_sync", ())
            )),
            "js_footer_async": tuple(self._js["footer"]["async"] | set(
                context.view_data.pop("extra_js_footer_async", ())
            ))
        })
        if context.template == self._dump_switch:
            context.set_response_content_type("application/json")
            dump_data = context.view_data.copy()  # shallow copy
            dump_data["session"] = context.session
            result = json_dumps(dump_data)
        else:
            template = self._env.get_template(context.template)
            context.view_data.update({
                "context": context
            })
            result = template.render(**context.view_data)

        if context.session is not None:
            context.session.del_flashes()

        return result

    def _get_extensions(self, config):
        extensions = set((
            "pygrim.components.jinja_ext.BaseExtension",
        ))
        extensions.update(
            config.get("jinja:extensions", ())
        )
        return list(extensions)

    def _initialize_assets(self, config):
        self._css = set(config.get("assets:css", ()))
        self._js = {
            "header": {
                "async": set(),
                "sync": set()
            },
            "footer": {
                "async": set(),
                "sync": set()
            }
        }
        self._js.update(config.get("assets:js", {}))

    def _initialize_extensions(self, config):
        if "jinja2.ext.i18n" in self._env.extensions:
            self._initialize_i18n(config)

    def _initialize_i18n(self, config):
        import gettext
        translations = gettext.translation(
            domain=config.get("jinja:i18n:lang_domain"),
            localedir=config.get("jinja:i18n:locale_path"),
            languages=config.get("jinja:i18n:locales")
        )
        self._env.install_gettext_translations(translations)
