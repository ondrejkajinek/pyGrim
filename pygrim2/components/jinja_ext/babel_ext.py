# std
import datetime
import re

# non-std
import babel.dates
import babel.numbers
from jinja2.runtime import Undefined
from jinja2.utils import pass_context

# local
from .time_base import TimeBase


DDT = type(datetime.datetime.min)
DD = type(datetime.date.min)
DT = type(datetime.time.min)


def py_2_babel_dateformat(fmt):
    if not fmt:
        return None

    # don't use datetime, date and time locale format,
    # use appropriate format function
    if fmt in ("%x", "%X", "%c"):
        return None

    # taken from
    # https://docs.python.org/3/library/datetime.html?highlight=datetime#strftime-strptime-behavior
    translates = (
        # abbreviated day of week name
        ("%a", "EEE"),
        # full day of week name
        ("%A", "EEEE"),
        # OndraK: intentionally left unimplemented
        # weekday number, 0 Sunday, 6 Saturday
        # ("%w", ""),
        # day of month, zero-padded
        ("%d", "dd"),
        # day of month
        ("%-d", "d"),
        # abbreviated month name
        ("%b", "MMM"),
        # month name
        ("%B", "MMMM"),
        # month number, zero-padded
        ("%m", "MM"),
        # month number
        ("%-m", "M"),
        # year without century, zero-padded
        ("%y", "yy"),
        # year with century, zero-padded
        ("%Y", "yyyy"),
        # hour, 24-hour clock, zero-padded
        ("%H", "HH"),
        # hour, 24-hour clock
        ("%-H", "H"),
        # hour, 12-hour clock, zero-padded
        ("%I", "hh"),
        # hour, 12-hour clock
        ("%-I", "h"),
        # abbreviation of either ante-meridiem ro poste-meridiem
        ("%p", "a"),
        # minute, zero-padded
        ("%M", "mm"),
        # minute
        ("%-M", "m"),
        # second, zero-padded
        ("%S", "ss"),
        # second
        ("%-S", "s"),
        # OndraK: intentionally left unimplemented
        # microsecond, zero-padded
        # ("%f", ""),
        # UTC offset in form +- HHMM[SS[.ffffff]]
        ("%z", "xx"),
        # time zone name
        ("%Z", "VV"),
        # day of year, zero-padded
        ("%j", "DDD"),
        # OndraK: intentionally left unimplemented
        # week number of the year (Sunday as the first day), zero-padded
        # ("%U", ""),
        # OndraK: intentionally left unimplemented
        # week number of the year (Monday as the first day), zero-padded
        # ("%W", "")
    )
    for trans_from, trans_to in translates:
        fmt = fmt.replace(trans_from, trans_to)

    # check if any unreplaced directive remains
    if "%" in fmt.replace("%%", ""):
        raise RuntimeError(
            "Not all directives are implemented in format %r", fmt)

    fmt.replace("%%", "%")
    return fmt


class BabelExtension(TimeBase):

    @pass_context
    def currency_format(self, context, amount, currency):
        return babel.numbers.format_currency(
            amount, currency, locale=context.get("context").get_language())

    @pass_context
    def currency_int_format(self, context, amount, currency):
        locale = context.get("context").get_language()
        text = babel.numbers.format_currency(amount, currency, locale=locale)
        return re.sub(
            babel.numbers.get_decimal_symbol(locale) + r"\d+",
            "",
            text
        )

    @pass_context
    def currency_parts(self, context, amount, currency):
        amount, currency = self._formatted_currency(context, amount, currency)
        return {
            "amount": amount,
            "currency": currency
        }

    @pass_context
    def currency_int_parts(self, context, amount, currency):
        locale = context.get("context").get_language()
        amount, currency = self._formatted_currency(context, amount, currency)

        return {
            "amount": re.sub(
                babel.numbers.get_decimal_symbol(locale) + r"\d+",
                "",
                amount
            ),
            "currency": currency
        }

    @pass_context
    def date_format(self, context, source, format_str=None):
        locale = context.get("context").get_language()
        obj = self._parse_date(source)
        if format_str == "%x" and isinstance(obj, DDT):
            obj = obj.date()
        elif format_str == "%X" and isinstance(obj, DDT):
            obj = obj.time()

        format_str = py_2_babel_dateformat(format_str)
        if isinstance(obj, DDT):
            return (
                babel.dates.format_datetime(obj, format_str, locale=locale)
                if format_str
                else babel.dates.format_datetime(obj, locale=locale)
            )
        elif isinstance(obj, DD):
            return (
                babel.dates.format_date(obj, format_str, locale=locale)
                if format_str
                else babel.dates.format_date(obj, locale=locale)
            )
        elif isinstance(obj, DT):
            return (
                babel.dates.format_time(obj, format_str, locale=locale)
                if format_str
                else babel.dates.format_time(obj, locale=locale)
            )
        elif obj is None:
            return Undefined()

        raise ValueError("Cannot format type %s", type(obj))

    @pass_context
    def number_format(self, context, number):
        locale = context.get("context").get_language()
        return (
            babel.numbers.format_decimal(number, locale=locale)
            if isinstance(number, float)
            else babel.numbers.format_number(number, locale)
        )

    @pass_context
    def time_format(self, context, source, format_str=None):
        obj = self._parse_time(source)
        if isinstance(obj, DT):
            return babel.dates.format_time(
                obj,
                format_str or "medium",
                locale=context.get("context").get_language()
            )
        elif obj is None:
            return Undefined()

        raise ValueError("Cannot format type %s", type(obj))

    def _formatted_currency(self, context, amount, currency):
        locale = context.get("context").get_language()
        formatted = babel.numbers.format_currency(
            amount, currency, locale=locale
        )

        currency_first = formatted[-1].isdigit()
        currency = ""
        if currency_first:
            while not formatted[0].isdigit():
                currency += formatted[0]
                formatted = formatted[1:]
        else:
            while not formatted[-1].isdigit():
                currency = formatted[-1] + currency
                formatted = formatted[:-1]

        return formatted, currency

    def _get_filters(self):
        filters = super()._get_filters()
        filters.update({
            "number_format": self.number_format
        })
        return filters

    def _get_functions(self):
        functions = super()._get_functions()
        functions.update({
            "currency_format": self.currency_format,
            "currency_int_format": self.currency_int_format,
            "currency_parts": self.currency_parts,
            "currency_int_parts": self.currency_int_parts
        })
        return functions
