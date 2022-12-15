# coding: utf8

from ..formater import Formater
from ..utils import Counter
from ..utils.functions import strip_accent
from json2 import dumps as json_dumps
from pygrim.components.config import YamlConfig
from jinja2.ext import Extension, Markup
from jinja2.runtime import Undefined
from logging import getLogger
from re import compile as re_compile
from textwrap import wrap
import traceback
from requests.utils import requote_uri
from configparser import ConfigParser

try:
    from seo_helper import SeoHelper
except ImportError:
    class SeoHelper(object):
        DASH_SQUEEZER = re_compile("r/-{2,}")
        SEO_DASHED = (" ", "/", "\\", ":")
        SEO_REMOVED = ("*", "?", "\"", "<", ">", "|", ",", "%", "!", )

        def safe_title(self, text):
            if not isinstance(text, str):
                text = str(text)

            res = "".join(
                c.lower()
                for c
                in strip_accent(text).replace(" ", "-")
                if c.isalnum() or c in "_-.:"
            )
            return res or "-"

        def seo(self, text, replace_char="-"):
            ret = self.DASH_SQUEEZER.sub(
                replace_char,
                self._seo_dashize(
                    self._seo_remove(strip_accent(text).lower()),
                    replace_char
                )
            )
            if not ret and replace_char:
                ret = replace_char
            return ret

    def _seo_dashize(self, text, replace_char):
        return "".join(
            replace_char
            if c in self.SEO_DASHED
            else c
            for c in text or ""
        )

    def _seo_remove(self, text):
        return "".join("" if c in self.SEO_REMOVED else c for c in text or "")

log = getLogger("pygrim.components.jinja_ext.base")


class BaseExtension(Extension):

    IEC_SIZE_PREFIXES = ("", "ki", "Mi", "Gi", "Ti")
    SI_SIZE_PREFIXES = ("", "k", "M", "G", "T")

    tags = set()

    def __init__(self, environment):
        super(BaseExtension, self).__init__(environment)
        environment.filters.update(self._get_filters())
        environment.globals.update(self._get_functions())
        self.formater = Formater("en_US.UTF8")
        # pro imager
        config = getattr(environment, "config", None) or {}
        self._debug = False
        self.use_imager_fallback = False
        self.use_nginx = False
        self.imager_relative_prefix = None
        self.imager_domain_prefixes = {
            "content-core.grandit.cz": "coc",
            "content-core.test.mopa.cz": "coct",
            "img.floowie.com": "flw",
            "mainstorage.musicjet.cz": "mjd",
            "storage.palmknihy.cz": "pkn",
        }

        if isinstance(config, (YamlConfig, dict)):
            self._debug = bool(config.get("jinja:debug", self._debug))
            self.use_nginx = bool(config.get(
                "jinja:imager:use_nginx", self.use_nginx
            ))
            self.use_imager_fallback = bool(config.get(
                "jinja:imager:use_imager_fallback", self.use_imager_fallback
            ))
            self.imager_relative_prefix = config.get(
                "jinja:imager:relative_prefix", self.imager_relative_prefix
            )
            self.imager_domain_prefixes = config.get(
                "jinja:imager:domain_prefixes", self.imager_domain_prefixes
            )
        elif isinstance(config, ConfigParser):
            self._debug = bool(config.get("jinja", "debug", self._debug))
            self.use_nginx = bool(config.get(
                "jinja", "imager_use_nginx", self.use_nginx
            ))
            self.use_imager_fallback = bool(config.get(
                "jinja", "imager_use_imager_fallback", self.use_imager_fallback
            ))
            self.imager_relative_prefix = config.get(
                "jinja", "imager_relative_prefix", self.imager_relative_prefix
            )
            if config.has_section("jinja-imager-domain-prefixes"):
                pfxs = config.optionsdict(
                    "jinja-imager-domain-prefixes", None
                )
                if pfxs:
                    self.imager_domain_prefixes = pfxs
            # endif
        else:
            log.critical("Unknown config class %s", type(config))
        # endif

    def as_json(self, data):
        log.warning("Filter `as_json` is deprecated and will be removed soon.")
        return self.to_json(data)

    def currency_format(self, amount, currency, locale=None, **kwargs):
        amount, currency, curr_last, sep = self.formater.format_currency(
            amount, currency, locale
        )
        return self._format_currency(
            amount, currency, curr_last, sep, **kwargs
        )

    def currency_int_format(self, amount, currency, locale=None, **kwargs):
        amount, currency, curr_last, sep = self.formater.format_currency_int(
            amount, currency, locale
        )
        return self._format_currency(
            amount, currency, curr_last, sep, **kwargs
        )

    def decimal_format(self, number, precision, locale=None):
        return self.formater.format_decimal(number, precision, locale)

    def _fit_image_imager(
        self, path, size=None, proxy=False, width=None, height=None,
        method=None
    ):
        width = width or ""
        height = height or ""
        if not path.startswith("/"):
            start = "/" if proxy else "//"
            log.debug(
                "IMG: %r - %r - %r - %r %r",
                start, method or "fit", width, height, path
            )
            path = "%simg.grandit.cz/%s,img,%s,%s;%s" % (
                start, method or "fit", width, height, path)
        return path
    # enddef

    def fit_image(
        self, path, size=None, proxy=False, width=None, height=None,
        method=None
    ):
        if not size:
            size = 160
        if not width and not height:
            width = size

        if self.use_nginx:
            image = path
            image = requote_uri(image)
            if path.startswith("http"):
                domain, img = image .split("/", 2)[-1].split("/", 1)
                prefix = self.imager_domain_prefixes.get(domain)
                if not prefix:
                    log.warning(
                        "IMAGER: unsupported domain %r in image", domain
                    )
                    if self._debug:
                        raise RuntimeError(
                            "unsupported domain %r in image", domain
                        )
                    else:
                        if self.use_imager_fallback:
                            log.warning(
                                "IMAGER: using old imager for url %r", path
                            )
                            return self._fit_image_imager(
                                path, size=size, proxy=proxy, width=width,
                                height=height, method=method
                            )
                        else:
                            return path
                image = img
            else:
                if self.imager_relative_prefix:
                    # pokud mame relativni prefix, tak jej pouzijeme
                    prefix = self.imager_relative_prefix
                    image = path.lstrip("/")
                elif self.use_imager_fallback:
                    # jdeme na stary imager, ale chceme o tom vedet
                    log.warning("IMAGER: using old imager for url %r", path)
                    return self._fit_image_imager(
                        path, size=size, proxy=proxy, width=width,
                        height=height, method=method
                    )
                else:
                    # relativni linky neumime, tak vratime puvodni link
                    log.warning("IMAGER: found relative url %r", image)
                    log.warning(
                        "using relative URL:%r from %s",
                        image, "".join(traceback.format_stack())
                    )
                    return path
            # endif
            use_width = width or 0
            use_height = height or 0
            new_path = "/im/%s/%s/%s/%s" % (
                prefix, use_width, use_height, image
            )
            log.debug("PATH: %r => %r", path, new_path)
            return new_path
        # endif

        return self._fit_image_imager(
            path, size=size, proxy=proxy, width=width, height=height,
            method=method
        )

    def number_format(self, number, locale=None):
        return self.formater.format_number(number, locale)

    def readable_size(self, size, precision=0):
        return self._readable_size(
            size, precision, 1024.0, self.IEC_SIZE_PREFIXES
        )

    def readable_si_size(self, size, precision=0):
        return self._readable_size(
            size, precision, 1000.0, self.SI_SIZE_PREFIXES
        )

    def safe_title(self, text):
        if not isinstance(text, str):
            text = str(text)
        c = getattr(SeoHelper, "safe_title", SeoHelper.seo)
        return c(text)

    def seo(self, text, replace_char="-"):
        return SeoHelper.seo(text, replace_char=replace_char)

    def split_to_length(self, value, length):
        if not value:
            return None

        if isinstance(value, int):
            value = str(value)
        elif isinstance(value, str):
            pass
        else:
            raise ValueError("int or string expected not %r" % (value,))

        return wrap(value, length)

    def to_json(self, value, indent=None):
        return json_dumps(value)

    def _format_currency(
        self, amount, currency, currency_last, separator, **kwargs
    ):
        if kwargs:
            amount = """<span %s data-sep="%s">%s</span>""" % (
                " ".join(
                    '%s="%s"' % (key, value)
                    for key, value
                    in list(kwargs.items())
                ),
                separator,
                amount
            )

        params = (
            (amount, currency)
            if currency_last
            else (currency, amount)
        )

        return Markup("%s%s" % params)

    def _get_filters(self):
        return {
            "as_json": self.as_json,
            "fit_image": self.fit_image,
            "readable_size": self.readable_size,
            "readable_si_size": self.readable_si_size,
            "safe_title": self.safe_title,
            "seo": self.seo,
            "split_to_length": self.split_to_length,
            "tojson": self.to_json
        }

    def _get_functions(self):
        return {
            "counter": Counter,
            "currency_format": self.currency_format,
            "currency_int_format": self.currency_int_format,
            "decimal_format": self.decimal_format,
            "number_format": self.number_format
        }

    def _readable_size(self, size, precision, multiple, prefixes):
        if not size:
            return Undefined()

        index = 0
        while size >= multiple:
            size /= multiple
            index += 1

        return ("%%0.%df %%sB" % precision) % (size, prefixes[index])
