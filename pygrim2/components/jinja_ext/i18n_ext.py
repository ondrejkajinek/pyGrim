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
            lang = context.get("context").get_language()
            used = set()
            parts = (
                part
                for part
                in itertools.chain(*[
                    # orig, lowered and uppered locale name
                    (i, i.lower(), i.upper())
                    for i
                    # take every possible varint of lang
                    # <lang>_<territory>.<encoding>@<variant>
                    # <lang>_<territory>.<encoding>
                    # <lang>_<territory>
                    # <lang>
                    in (
                        lang,
                        lang.split("@", 1)[0],
                        lang.split(".", 1)[0],
                        lang.split("_", 1)[0]
                    )
                ])
                # don't add duplicate locale names
                if part not in used and (used.add(part) or True)
            )
            for part in parts:
                if part in source:
                    text = source[part]
                    break
            else:
                text = Undefined()
        elif isinstance(source, str):
            text = source
        else:
            text = Undefined()

        return text

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
