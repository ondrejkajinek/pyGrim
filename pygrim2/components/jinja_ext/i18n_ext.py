import itertools

from jinja2.ext import InternationalizationExtension
from jinja2.runtime import Undefined
from jinja2.filters import contextfilter


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
            fallbacks is not None and
            len(fallbacks) == 2
        ):
            result = method(fallbacks[0], fallbacks[1], number)

        return result

    return ngettext


def lang_text_factory():

    @contextfilter
    def lang_text(context, source):
        if isinstance(source, dict) and source:
            for lang in context.get("context").get_language_priority():
                if lang in source:
                    return source[lang]
            return source.values()[0]
        elif isinstance(source, str):
            return source
        else:
            return Undefined()

    return lang_text


class I18NExtension(InternationalizationExtension):

    def __init__(self, environment):
        super().__init__(environment)
        environment.filters.update(self._get_filters())

    def _get_filters(self):
        return {
            "lang_text": lang_text_factory()
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
