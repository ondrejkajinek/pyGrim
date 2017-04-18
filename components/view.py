# coding: utf8

from jinja2 import Environment, FileSystemLoader, select_autoescape
from json import dumps as json_dumps
from os import getcwd, path


class View(object):

    # TODO: add filters
    def __init__(self, config, extra_functions):
        self._debug = config.get("jinja.debug", False)
        self._dump_switch = config.get("jinja.dump_switch", "jkxd")
        self._env = Environment(
            extensions=self._get_extensions(config),
            loader=FileSystemLoader(
                searchpath=path.join(
                    getcwd(),
                    config.get("jinja.template_path")
                )
            ),
            autoescape=select_autoescape(
                enabled_extensions=config.get(
                    "jinja.environment.autoescape",
                    ("jinja",)
                )
            )
        )
        # TODO: can extra functions be registered via Environment?
        self._extra_functions = extra_functions
        self._initialize_extensions(config)

    def display(self, template, data, request, response):
        body, headers = self.render(template, data, request)
        response.body = body
        response.headers.update(headers)

    def get_template_directory(self):
        return self._env.loader.searchpath

    def render(self, template, data, request):
        # TODO: enable when flash is ready
        # self._load_flash_data()
        if self._debug and self._dump_switch in request.GET:
            data["template_path"] = path.join(
                self.get_template_directory(),
                template
            )
            template = self._dump_switch

        data["debug"] = self._debug
        if template == self._dump_switch:
            headers = {
                "Content-Type": "application/json"
            }
            result = json_dumps(data)
        else:
            template = self._env.get_template(template)
            headers = {}
            data.update(self._get_extension_methods())
            result = template.render(**data)

        return result, headers

    def _get_extensions(self, config):
        extensions = [
            # "jinja2_git.GitExtension"
        ]
        if self._has_i18n(config):
            extensions.append("jinja2.ext.i18n")

        return extensions

    def _get_extension_methods(self):
        return self._extra_functions

    def _has_i18n(self, config):
        return config.get("jinja.i18n.enabled", False)

    def _initialize_extensions(self, config):
        if self._has_i18n(config):
            self._initialize_i18n(config)

    def _initialize_i18n(self, config):
        import gettext
        translations = gettext.translation(
            domain=config.get("jinja.i18n.lang_domain"),
            localedir=config.get("jinja.i18n.locale_path"),
            languages=config.get("jinja.i18n.locales")
        )
        self._env.install_gettext_translations(translations)

    def _load_flash_data(self):
        self._data.update({
            self._flash.get_key(): self._flash.get_messages()
        })
