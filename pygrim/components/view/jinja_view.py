# coding: utf8

from .abstract_view import AbstractView
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
        return tuple(self._env.loader.searchpath)

    def _get_extensions(self, config):
        extensions = set((
            "pygrim.components.jinja_ext.BaseExtension",
            "pygrim.components.jinja_ext.TimeExtension",
        ))
        extensions.update(
            config.get("jinja:extensions", ())
        )
        return list(extensions)

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

    def _render(self, context):
        template = self._env.get_template(context.template)
        context.view_data.update({
            "context": context
        })
        return template.render(**context.view_data)
