# std
from logging import getLogger
from re import compile as re_compile
from textwrap import wrap

# non-std
from jinja2.ext import Extension
from jinja2.runtime import Undefined

# local
from ..utils import Counter
from ..utils.functions import strip_accent
from ..utils.json2 import dumps as json_dumps

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
        environment.filters.update(self._get_filters())
        environment.globals.update(self._get_functions())

    def as_json(self, data):
        log.warning("Filter `as_json` is deprecated and will be removed soon.")
        return self.to_json(data)

    # TODO: remove, put to some GIT specific extension!
    def fit_image(self, path, size=None, proxy=False, width=None, height=None):
        size = size or 160
        if not width and not height:
            width = size

        width = width or ""
        height = height or ""
        if path and not path.startswith("/"):
            start = "/" if proxy else "//"
            path = "%simg.grandit.cz/fit,img,%s,%s;%s" % (
                start, width, height, path
            )

        return path

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
                self._seo_remove(strip_accent(text).lower()),
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

    def to_json(self, value, indent=None):
        return json_dumps(value)

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
            "counter": Counter
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
