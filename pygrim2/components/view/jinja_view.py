# coding: utf8

# std
from os import getcwd, path
from logging import getLogger

# non-std
from jinja2 import Environment, FileSystemLoader, select_autoescape

# local
from .base_view import BaseView
from ..jinja_ext import i18n
from ..utils import get_class_name

I18N_EXT_NAME = get_class_name(i18n)
log = getLogger(__file__)


def _suppress_none(self, variable):
    return (
        ""
        if variable is None
        else variable
    )


_suppress_none.contextfunction = True


class JinjaView(BaseView):

    def __init__(self, config, extra_functions, l10n, **kwargs):
        self._debug = config.getbool("jinja:debug", False)
        self._l10n = l10n
        self._env_kwargs = {
            "extensions": self._get_extensions(config),
            "loader": FileSystemLoader(
                searchpath=path.join(
                    getcwd(),
                    config.get("jinja:template_path", "templates")
                )
            ),
            "autoescape": select_autoescape(
                enabled_extensions=config.get(
                    "jinja:environment:autoescape",
                    ("jinja",)
                )
            ),
            "auto_reload": config.getbool(
                "jinja:environment:auto_reload", True
            )
        }
        if config.getbool("jinja:suppress_none", True):
            self._env_kwargs["finalize"] = _suppress_none

        self._extra_functions = extra_functions
        self._initialize_assets(config)

    def get_template_directory(self):
        return tuple(self._env_kwargs["loader"].searchpath)

    def _create_env(self, context):
        env = Environment(**self._env_kwargs)
        env.globals.update(self._extra_functions)

        log.debug("Select translations? :%s", self._has_gettext())
        if self._has_gettext():
            log.info(
                "Selecting translations %s from => %s",
                context.get_language(),
                self._l10n.get(context.get_language())
            )
            env.install_gettext_translations(
                self._l10n.get(context.get_language())
            )

        return env

    def _get_extensions(self, config):
        extensions = set((
            "pygrim2.components.jinja_ext.BaseExtension",
            "pygrim2.components.jinja_ext.TimeExtension",
            "pygrim2.components.jinja_ext.UrlExtension",
        ))
        extensions.update(
            config.get("jinja:extensions", ())
        )
        if (
            config.getboolean("pygrim:l10n", False) and
            config.get("pygrim:l10n:type") == "gettext"
        ):
            extensions.update((I18N_EXT_NAME,))

        return map(str, extensions)

    def _has_gettext(self):
        return I18N_EXT_NAME in self._env_kwargs["extensions"]

    def _render_template(self, context):
        env = self._create_env(context)
        template = env.get_template(context.template)
        context.view_data.update({
            "context": context
        })
        return template.render(**context.view_data)
