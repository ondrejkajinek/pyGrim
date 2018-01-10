# coding: utf8

from logging import getLogger
import datetime

log = getLogger("pygrim.http.formater")

try:
    import babel
    from babel import dates as babel_dates
    print "!! Babel library not availbale"
    log.warning(
        "Babel library not availabe - "
        "locale dependent translates could be wrong"
    )
except ImportError:
    babel = None

# endtry


def py_2_babel_dateformat(fmt):

    fmt = fmt.replace("%B", "LLLL")  # full month name - infinitive
    #  fmt = fmt.replace("%B", "MMMM")  # full month name - depends on day
    fmt = fmt.replace("%H", "HH")  # 24 Hour
    fmt = fmt.replace("%-H", "H")  # 24 Hour not padded
    fmt = fmt.replace("%I", "hh")  # 12 Hour
    fmt = fmt.replace("%-I", "h")  # 12 Hour not padded
    fmt = fmt.replace("%M", "mm")  # minutes
    fmt = fmt.replace("%-M", "mm")  # minutes not padded
    fmt = fmt.replace("%d", "dd")  # day of month
    fmt = fmt.replace("%-d", "d")  # day of month not padded

    # check if any percent remains
    if "%" in fmt.replace("%%", ""):
        raise RuntimeError("Need to implement replacement in format %r" % (
            fmt,
        ))
    # replace quoted percent to percent
    fmt.replace("%%", "%")
    return fmt


DTT = type(datetime.datetime.min)


class Formater(object):
    def __init__(self, locale):
        log.warning(
            "Babel library not availabe - "
            "locale dependent translates could be wrong"
        )
        self._locale = locale

    def _set_locale(self, locale):
        log.warning(
            "Babel library not availabe - "
            "locale dependent translates could be wrong"
        )
        self._locale = locale

    def format(self, what, fmt=None, locale=None):
        if not babel:
            log.warning(
                "Babel library not availabe - "
                "locale dependent translates could be wrong"
            )
        locale = locale or self._locale

        if isinstance(what, DTT):
            if babel:
                fmt = py_2_babel_dateformat(fmt)
                if fmt:
                    return babel_dates.format_datetime(
                        what, fmt, locale=locale
                    )
                else:
                    return babel_dates.format_datetime(what, locale=locale)
            else:
                return what.strftime(fmt)
            # endif
        raise RuntimeError("formating %s not implemented" % (type(what),))

# eof
