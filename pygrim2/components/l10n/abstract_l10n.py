# coding: utf8

from logging import getLogger
from os import path

start_log = getLogger("pygrim_start.components.l10n.gettext")


class AbstractL10n(object):

    def __init__(self, config, *args, **kwargs):
        raise NotImplementedError()

    def get(self, translation):
        raise NotImplementedError()

    def has(self, translation):
        raise NotImplementedError()

    def select_language(self, context):
        raise NotImplementedError()

    def translations(self):
        raise NotImplementedError()


class BaseL10n(AbstractL10n):

    def __init__(self, config, *args, **kwargs):
        self._lang_key = config.get("pygrim:l10n:cookie_key", "site_language")
        self._lang_switch = config.get("pygrim:l10n:locale_switch", "lang")
        self._load_translations(config)
        self._load_locale_map(config)
        self._set_default_locale(config)

    def get(self, translation):
        return self._translations.get(
            translation, self._translations[self._default_locale]
        )

    def has(self, translation):
        return translation in self._translations

    def lang_key(self):
        return self._lang_key

    def select_language(self, context):
        language = context.GET(self._lang_switch)
        if language not in self._translations:
            language = context._request.cookies.get(self._lang_key)
            # fix for situation with multiple lang cookies
            if isinstance(language, list):
                language = language[-1] if language else None

        if language not in self._translations:
            try:
                accept_languages = (
                    lang.split(";")[0]
                    for lang
                    in context._request.environment["accept_language"]
                    if lang.split(";")[0] in self._translations
                )
            except KeyError:
                language = self._default_locale
            else:
                language = (
                    next((lang for lang in accept_languages if lang), None) or
                    self._default_locale
                )

        return language

    def translations(self):
        return self._translations

    def _create_translation(self, **kwargs):
        return None

    def _load_locale_map(self, config):
        locale_map = config.get("pygrim:l10n:locale_map", {})
        for shortcut, locale in locale_map.iteritems():
            if locale in self._translations:
                self._translations[shortcut] = self._translations[locale]

    def _load_translations(self, config):
        l10n_kwargs = {
            "lang_domain": config.get("pygrim:l10n:lang_domain"),
            "locale_path": path.join(
                config.get("uwsgi:chdir"),
                config.get("pygrim:l10n:locale_path")
            )
        }
        self._translations = {}
        for lang in config.get("pygrim:l10n:locales"):
            l10n_kwargs["locales"] = (lang,)
            try:
                translation = self._create_translation(**l10n_kwargs)
            except IOError:
                msg = "No translation file found for language %r in domain %r"
                start_log.error(msg, lang, l10n_kwargs["lang_domain"])
                raise RuntimeError(msg % (lang, l10n_kwargs["lang_domain"]))
            else:
                self._translations[lang] = translation

        start_log.debug("Loaded translations: %r", self._translations.keys())

    def _set_default_locale(self, config):
        try:
            default_locale = config.get("pygrim:l10n:default_locale")
        except KeyError:
            raise
        else:
            if default_locale not in self._translations:
                msg = "Default locale %r is not enabled. Known locales: %r"
                start_log.error(msg, default_locale, self._translations.keys())
                raise RuntimeError(
                    msg % (default_locale, self._translations.keys())
                )

        start_log.debug("Default translation: %r", default_locale)
        self._default_locale = default_locale
