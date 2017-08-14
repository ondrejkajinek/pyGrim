# coding: utf8

from gettext import translation as gettext_translation

# local
from .abstract_l10n import BaseL10n


class GettextL10n(BaseL10n):

    def __init__(self, config, *args, **kwargs):
        super(GettextL10n, self).__init__(config, *args, **kwargs)

    def _create_translation(self, **kwargs):
        gettext_kwargs = {
            "domain": kwargs["lang_domain"],
            "localedir": kwargs["locale_path"]
        }
        if "locales" in kwargs:
            gettext_kwargs["languages"] = kwargs["locales"]

        return gettext_translation(**gettext_kwargs)
