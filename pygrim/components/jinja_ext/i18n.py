# coding: utf8
from logging import getLogger
from jinja2.ext import InternationalizationExtension
from jinja2.runtime import Undefined


log = getLogger("pygrim.jinja_ext.i18n")


def gettext_factory(method):

    def gettext(message, fallback=None):
        result = method(message)
        if result == message and fallback is not None:
            result = method(fallback)

        return result

    return gettext


def ngettext_factory(method):

    def ngettext(singular, plural, number, *fallbacks):
        result = method(singular, plural, number)
        message = singular if number == 1 else plural
        if (
            result == message and
            fallbacks is not None and len(fallbacks) == 2
        ):
            result = method(fallbacks[0], fallbacks[1], number)

        return result

    return ngettext


class I18NExtension(InternationalizationExtension):

    def __init__(self, environment):
        super(I18NExtension, self).__init__(environment)
        environment.globals.update(self._get_functions())

    def lang_text(self, source, language, order=None):
        text = None
        if source and isinstance(source, dict):
            text = source.get(language)
            if not text:
                for key in (order or sorted(source.keys())):
                    text = source.get(key)
                    if text:
                        break
        if not text:
            text = Undefined()

        return text

    def _get_functions(self):
        return {
            "lang_text": self.lang_text
        }

    def _install(self, translations, newstyle=None):
        gettext = getattr(translations, 'ugettext', None)
        if gettext is None:
            gettext = translations.gettext
        ngettext = getattr(translations, 'ungettext', None)
        if ngettext is None:
            ngettext = translations.ngettext

        self._install_callables(
            gettext_factory(gettext),
            ngettext_factory(ngettext),
            newstyle
        )

i18n = I18NExtension
