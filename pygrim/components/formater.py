# coding: utf8

from datetime import date, datetime, timedelta
from logging import getLogger

log = getLogger("pygrim.http.formater")

try:
    import babel
    from babel import dates as babel_dates
    log.debug("Babel translations available")
except ImportError:
    print "!! Babel library not availbale"
    log.warning(
        "Babel library not availabe - "
        "locale dependent translates could be wrong"
    )
    babel = None

# endtry


def py_2_babel_dateformat(fmt):
    if not fmt:
        return None

    if fmt == "%x":
        return None
    if fmt == "%c":
        return None
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


DT_DT = type(datetime.min)
DT_D = type(date.min)
DT_TD = type(timedelta.min)


class Formater(object):
    def __init__(self, locale):
        self._set_locale(locale)

    def _set_locale(self, locale):
        if not babel:
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

        if isinstance(what, DT_DT):
            if fmt == "%c":
                what = what.date()
                # change format and let it on date formater
            elif babel:
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
        if isinstance(what, DT_D):
            if babel:
                fmt = py_2_babel_dateformat(fmt)
                if fmt:
                    return babel_dates.format_date(
                        what, fmt, locale=locale
                    )
                else:
                    return babel_dates.format_date(what, locale=locale)
            else:
                return what.strftime(fmt)
            # endif
        if isinstance(what, DT_TD):
            if babel:
                fmt = py_2_babel_dateformat(fmt)
                if fmt:
                    return babel_dates.format_timedelta(
                        what, fmt, locale=locale
                    )
                else:
                    return babel_dates.format_timedelta(what, locale=locale)
            else:
                return what.strftime(fmt)
            # endif
        raise RuntimeError("formating %s not implemented" % (type(what),))

# eof
