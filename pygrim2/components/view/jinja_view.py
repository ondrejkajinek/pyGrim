# coding: utf8

# std
from os import getcwd, path

# non-std
from jinja2 import Environment, FileSystemLoader, select_autoescape

# local
from .abstract_view import BaseView
from ..jinja_ext import i18n
from ..utils import get_class_name

I18N_EXT_NAME = get_class_name(i18n)


def _suppress_none(self, variable):
    return (
        ""
        if variable is None
        else variable
    )

_suppress_none.contextfunction = True


class JinjaView(BaseView):

    def __init__(self, config, extra_functions, translations=None, **kwargs):
        self._debug = config.get("jinja:debug", False)
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
            auto_reload=config.get("jinja:environment:auto_reload", True),
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
        return tuple(self._env.loader.searchpath)

    def use_translation(self, translation):
        if self._has_i18n():
            self._env.install_gettext_translations(translation)

    def _get_extensions(self, config):
        extensions = set((
            "pygrim2.components.jinja_ext.BaseExtension",
            "pygrim2.components.jinja_ext.TimeExtension",
        ))
        extensions.update(
            config.get("jinja:extensions", ())
        )
        if (
            config.getboolean("pygrim:l10n", False) and
            config.get("pygrim:l10n:type") == "gettext"
        ):
            extensions.update(("pygrim2.components.jinja_ext.i18n",))

        return list(extensions)

    def _has_i18n(self):
        return I18N_EXT_NAME in self._env.extensions

    def _render_template(self, context):
        template = self._env.get_template(context.template)
        context.view_data.update({
            "context": context
        })
        return template.render(**context.view_data)
