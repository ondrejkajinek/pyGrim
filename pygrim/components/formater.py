# coding: utf8

from datetime import date, datetime, timedelta, time
from logging import getLogger

log = getLogger("pygrim.http.formater")

try:
    import babel
    from babel import dates as babel_dates
    from babel import numbers as babel_numbers
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
    if fmt == "%X":
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
    fmt = fmt.replace("%A", "EEEE")  # WEkkday name FULL
    fmt = fmt.replace("%a", "EEE")  # WEkkday name SHORT
    fmt = fmt.replace("%B", "MMMM")  # Month name FULL
    fmt = fmt.replace("%b", "MMM")  # Month name SHORT
    fmt = fmt.replace("%y", "YY")  # last 2 digits of year
    fmt = fmt.replace("%Y", "YYYY")  # full year

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
DT_T = type(time.min)


class Formater(object):

    def __init__(self, locale):
        self._set_locale(locale)

    def __getattr__(self, key):
        if key.endswith("_babel") or key.endswith("_nobabel"):
            raise AttributeError(key.rsplit("_", 1)[0])

        if babel:
            attr_name = "_%s_babel" % key
        else:
            log.warning(
                "Babel library not availabe - "
                "locale dependent translates could be wrong"
            )
            attr_name = "_%s_nobabel" % key

        method = getattr(self, attr_name)

        return method

    def _format_currency_babel(self, amount, currency, locale=None):
        return self._get_currency_parts(
            amount, currency, locale or self._locale
        )

    def _format_currency_nobabel(self, amount, currency, locale=None):
        return amount, currency, False

    def _format_currency_int_babel(self, amount, currency, locale=None):
        amount, currency, currency_last, separator = self._get_currency_parts(
            amount, currency, locale or self._locale
        )
        amount = int(babel_numbers.parse_decimal(amount, locale))
        return amount, currency, currency_last, separator

    def _format_currency_int_nobabel(self, amount, currency, locale=None):
        return int(amount), currency, False

    def _format_date_babel(self, what, fmt=None, locale=None):
        locale = locale or self._locale
        if fmt == "%x" and isinstance(what, DT_DT):
            what = what.date()
        elif fmt == "%X" and isinstance(what, DT_DT):
            what = what.time()

        if isinstance(what, DT_DT):

            fmt = py_2_babel_dateformat(fmt)
            if fmt:
                return babel_dates.format_datetime(
                    what, fmt, locale=locale
                )
            else:
                return babel_dates.format_datetime(what, locale=locale)

        if isinstance(what, DT_D):
            fmt = py_2_babel_dateformat(fmt)
            if fmt:
                return babel_dates.format_date(
                    what, fmt, locale=locale
                )
            else:
                return babel_dates.format_date(what, locale=locale)

        if isinstance(what, DT_TD):
            fmt = py_2_babel_dateformat(fmt)
            if fmt:
                return babel_dates.format_timedelta(
                    what, fmt, locale=locale
                )
            else:
                return babel_dates.format_timedelta(what, locale=locale)

        if isinstance(what, DT_T):
            return self._format_time_babel(what, fmt, locale)

        raise RuntimeError("formating %s not implemented" % (type(what),))

    def _format_date_nobabel(self, what, fmt=None, locale=None):
        locale = locale or self._locale

        if isinstance(what, DT_DT):
            if fmt == "%c":
                what = what.date()

            return what.strftime(fmt)

        if isinstance(what, DT_D):
            return what.strftime(fmt)

        if isinstance(what, DT_TD):
            return what.strftime(fmt)

        raise RuntimeError("formating %s not implemented" % (type(what),))

    def _format_decimal_babel(self, number, precision=None, locale=None):
        return babel_numbers.format_decimal(
            number=number,
            format="#.%s" % "".join("#" for _ in xrange(precision)),
            locale=locale or self._locale
        )

    def _format_decimal_nobabel(self, number, precision=None, locale=None):
        return ("%%0.%df" % precision) % int(number)

    def _format_number_babel(self, number, locale=None):
        return babel_numbers.format_number(number, locale or self._locale)

    def _format_number_nobabel(self, number, locale=None):
        return number

    def _format_time_babel(self, what, fmt=None, locale=None):
        locale = locale or self._locale

        if isinstance(what, DT_T):
            fmt = py_2_babel_dateformat(fmt)
            if fmt:
                return babel_dates.format_time(
                    what, fmt, locale=locale
                )
            else:
                return babel_dates.format_time(what, locale=locale)

        raise RuntimeError("formating %s not implemented" % (type(what),))

    def _format_time_nobabel(self, what, fmt=None, locale=None):
        locale = locale or self._locale

        if isinstance(what, DT_T):
            return what.strftime(fmt)

        raise RuntimeError("formating %s not implemented" % (type(what),))

    def _get_currency_parts(self, amount, currency, locale):
        formatted = babel_numbers.format_currency(
            number=amount,
            currency=currency,
            locale=locale
        )
        amount = formatted
        currency = ""
        currency_last = amount[0].isdigit()
        if currency_last:
            while not amount[-1].isdigit():
                currency = amount[-1] + currency
                amount = amount[:-1]
        else:
            while not amount[0].isdigit():
                currency += amount[0]
                amount = amount[1:]

        return (
            amount,
            currency,
            currency_last,
            babel_numbers.get_decimal_symbol(locale)
        )

    def _set_locale(self, locale):
        self._locale = locale
