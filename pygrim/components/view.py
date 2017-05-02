# coding: utf8

from jinja2 import Environment, FileSystemLoader, select_autoescape
from json import dumps as json_dumps
from os import getcwd, path


class View(object):

    def __init__(self, config, extra_functions):
        self._debug = config.get("jinja:debug", False)
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
            )
        )
        self._env.filters.update({
            "url_for": extra_functions["url_for"]
        })
        self._env.globals.update(extra_functions)
        self._initialize_assets(config)
        self._initialize_extensions(config)

    def display(self, context):
        body, headers = self.render(context)
        context.set_response_body(body)
        context.add_response_headers(headers)

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
            headers = {
                "Content-Type": "application/json"
            }
            result = json_dumps(context.view_data)
        else:
            template = self._env.get_template(context.template)
            headers = {}
            context.view_data.update({
                "context": context
            })
            result = template.render(**context.view_data)

        if context.session is not None:
            context.session.del_flashes()  # smazem flashes

        return result, headers

    def _get_extensions(self, config):
        extensions = [
            "pygrim.components.jinja_ext.BaseExtension"
        ]
        if self._has_i18n(config):
            extensions.append("jinja2.ext.i18n")

        return extensions

    def _has_i18n(self, config):
        return config.get("jinja:i18n:enabled", False)

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
        if self._has_i18n(config):
            self._initialize_i18n(config)

    def _initialize_i18n(self, config):
        import gettext
        translations = gettext.translation(
            domain=config.get("jinja:i18n:lang_domain"),
            localedir=config.get("jinja:i18n:locale_path"),
            languages=config.get("jinja:i18n:locales")
        )
        self._env.install_gettext_translations(translations)
