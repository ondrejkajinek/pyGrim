# std
from logging import getLogger
from re import compile as re_compile
from textwrap import wrap
import traceback
from configparser import ConfigParser

# non-std
from jinja2.ext import Extension
from jinja2.runtime import Undefined
from requests.utils import requote_uri

# local
from ..utils import Counter
from ..utils.functions import strip_accent
from ..utils.json2 import dumps as json_dumps
from ..config import YamlConfig

log = getLogger("pygrim.components.jinja_ext.base")


class BaseExtension(Extension):

    DASH_SQUEEZER = re_compile("r/-{2,}")
    SEO_DASHED = (" ", "/", "\\", ":")
    SEO_REMOVED = ("*", "?", "\"", "<", ">", "|", ",", "%")
    IEC_SIZE_PREFIXES = ("", "ki", "Mi", "Gi", "Ti")
    SI_SIZE_PREFIXES = ("", "k", "M", "G", "T")

    tags = set()

    def __init__(self, environment):
        super(BaseExtension, self).__init__(environment)
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
        environment.filters.update(self._get_filters())
        environment.globals.update(self._get_functions())

    def as_json(self, data):
        log.warning(
            "Filter `as_json` is deprecated and will be removed soon. "
            "Use 'tojson' instead."
        )
        return self.to_json(data)

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

        res = "".join(
            c
            for c
            in strip_accent(text).replace(" ", "_")
            if c.isalnum() or c in "_-.:"
        )
        return res or "_"

    def seo(self, text, replace_char="-"):
        return self.DASH_SQUEEZER.sub(
            replace_char,
            self._seo_dashize(
                self._seo_remove(strip_accent(text).lower(), replace_char),
                replace_char
            )
        )

    def split_to_length(self, value, length):
        # bool is subtype of int
        if isinstance(value, bool):
            raise TypeError("int or string expected not bool")
        elif isinstance(value, int):
            value = str(value)
        elif isinstance(value, str):
            pass
        else:
            raise TypeError("int or string expected not %r" % (value,))

        if not value:
            return Undefined()

        return wrap(value, length)

    def to_json(self, value, indent=None, pretty=None):
        return json_dumps(value, nice=pretty)

    def _get_filters(self):
        return {
            "as_json": self.as_json,
            "fit_image": self.fit_image,
            "readable_size": self.readable_size,
            "readable_si_size": self.readable_si_size,
            "safe_title": self.safe_title,
            "seo": self.seo,
            "split_to_length": self.split_to_length,
            # override Jinja builtin with json2.dumps
            "tojson": self.to_json
        }

    def _get_functions(self):
        return {
            "counter": Counter,
            "set": set,  # add set constructor to use sets in jinja2
        }

    def _readable_size(self, size, precision, multiple, prefixes):
        if size is None:
            return Undefined()

        index = 0
        while size >= multiple:
            size /= multiple
            index += 1

        return ("%%0.%df %%sB" % precision) % (size, prefixes[index])

    def _seo_dashize(self, text, replace_char):
        return self._seo_replace(text, self.SEO_DASHED, replace_char)

    def _seo_remove(self, text, replace_char):
        return self._seo_replace(text, self.SEO_REMOVED, "")

    def _seo_replace(self, text, changed, replacement):
        return "".join(replacement if c in changed else c for c in text or "")

    def _fit_image_imager(
        self, path, size=None, proxy=False, width=None, height=None,
        method=None
    ):
        width = width or ""
        height = height or ""
        if path and not path.startswith("/"):
            start = "/" if proxy else "//"
            log.debug(
                "IMG: %r - %r - %r - %r %r",
                start, method or "fit", width, height, path
            )
            path = "%simg.grandit.cz/%s,img,%s,%s;%s" % (
                start, method or "fit", width, height, path)
        return path
    # enddef

    def _fit_image_nginx(
        self, path, size=None, proxy=False, width=None, height=None,
        method=None
    ):
        image = path
        image = requote_uri(image)
        if path.startswith("http"):
            domain, img = image.split("/", 2)[-1].split("/", 1)
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

    def fit_image(
        self, path, size=None, proxy=False, width=None, height=None,
        method=None
    ):
        if not size:
            size = 160
        if not width and not height:
            width = size

        if self.use_nginx:
            m = self._fit_image_nginx
        else:
            m = self._fit_image_imager
        # endif

        return m(
            path, size=size, proxy=proxy, width=width, height=height,
            method=method
        )
