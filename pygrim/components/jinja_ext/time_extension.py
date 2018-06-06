# coding: utf8

from __future__ import unicode_literals
from datetime import date, datetime, timedelta, time
from dateutil.parser import parse as parse_dt
from jinja2.ext import Extension
from time import gmtime, strftime
from ..formater import Formater

DTS = (
    type(datetime.min),
    type(date.min),
)
DTT = type(time.min)

months = {
    "cs": [
        {
            'singular': ['Leden', 'Únor', 'Březen', 'Duben', 'Květen', 'Červen', 'Červenec', 'Srpen', 'Září', 'Říjen', 'Listopad', 'Prosinec'],
            'plural': ['Ledny', 'Únory', 'Březny', 'Dubny', 'Květny', 'Červny', 'Července', 'Srpny', 'Září', 'Říjny', 'Listopady', 'Prosince']
        }, {
            'singular': ['Ledna', 'Února', 'Března', 'Dubna', 'Května', 'Června', 'Července', 'Srpna', 'Září', 'Října', 'Listopadu', 'Prosince'],
            'plural': ['Lednů', 'Únorů', 'Březnů', 'Dubnů', 'Květnů', 'Červnů', 'Červenců', 'Srpnů', 'Září', 'Říjnů', 'Listopadů', 'Prosinců']
        }, {
            'singular': ['Lednu', 'Únoru', 'Březnu', 'Dubnu', 'Květnu', 'Červnu', 'Červenci', 'Srpnu', 'Září', 'Říjnu', 'Listopadu', 'Prosinci'],
            'plural': ['Lednům', 'Únorům', 'Březnům', 'Dubnům', 'Květnům', 'Červnům', 'Červencům', 'Srpnům', 'Zářím', 'Říjnům', 'Listopadům', 'Prosincům']
        }, {
            'singular': ['Leden', 'Únor', 'Březen', 'Duben', 'Květen', 'Červen', 'Červenec', 'Srpen', 'Září', 'Říjen', 'Listopad', 'Prosinec'],
            'plural': ['Ledny', 'Únory', 'Březny', 'Dubny', 'Květny', 'Červny', 'Července', 'Srpny', 'Září', 'Říjny', 'Listopady', 'Prosince']
        }, {
            'singular': ['Ledne', 'Únore', 'Březne', 'Dubne', 'Květne', 'Červne', 'Červenci', 'Srpne', 'Září', 'Říjne', 'Listopade', 'Prosinci'],
            'plural': ['Ledny', 'Únory', 'Březny', 'Dubny', 'Květny', 'Červny', 'Července', 'Srpny', 'Září', 'Říjny', 'Listopady', 'Prosince']
        }, {
            'singular': ['Lednu', 'Únoru', 'Březnu', 'Dubnu', 'Květnu', 'Červnu', 'Červenci', 'Srpnu', 'Září', 'Říjnu', 'Listopadu', 'Prosinci'],
            'plural': ['Lednech', 'Únorech', 'Březnech', 'Dubnech', 'Květnech', 'Červnech', 'Červencích', 'Srpnech', 'Zářích', 'Říjnech', 'Listopadech', 'Prosincích']
        }, {
            'singular': ['Lednem', 'Únorem', 'Březnem', 'Dubnem', 'Květnem', 'Červnem', 'Červencem', 'Srpnem', 'Zářím', 'Říjnem', 'Listopadem', 'Prosincem'],
            'plural': ['Ledny', 'Únory', 'Březny', 'Dubny', 'Květny', 'Červny', 'Červenci', 'Srpny', 'Zářími', 'Říjny', 'Listopady', 'Prosinci']
        }
    ]
}


class TimeExtension(Extension):
    tags = set()

    def __init__(self, environment):
        super(TimeExtension, self).__init__(environment)
        environment.filters.update(self._get_filters())
        environment.globals.update(self._get_functions())
        self.formater = Formater("en_US.UTF8")

    def as_date(self, date_, format_str=None):
        if isinstance(date_, basestring):
            date_ = parse_dt(date_)

        text = date_.strftime(format_str) if format_str else date_.isoformat()
        if isinstance(text, str):
            text = unicode(text, "utf8")
        return text

    def date_format(self, source, format_str, locale=None):
        if isinstance(source, basestring):
            obj = (
                datetime.fromtimestamp(float(source))
                if source.isdigit()
                else parse_dt(source)
            )
        elif isinstance(source, (int, long)):
            obj = datetime.fromtimestamp(source)
        elif isinstance(source, DTS):
            obj = source
        else:
            return None

        return self._format_datetime(obj, format_str, locale)

    def date_now(self):
        return date.today()

    def datetime_now(self):
        return datetime.now()

    def minutes_from_seconds(self, seconds):
        return "%d:%d" % (seconds // 60, seconds % 60)

    def time_format(self, source, format_str, locale=None):
        if isinstance(source, basestring):
            obj = parse_dt(source).time()
        elif isinstance(source, DTS):
            obj = source.time()
        elif isinstance(source, DTT):
            obj = source
        else:
            return None

        return self._format_datetime(obj, format_str, locale)

    def time_from_seconds(self, seconds, locale=None):
        if locale:
            return self.formater.format(
                timedelta(seconds=seconds), locale=locale
            )
        else:
            return strftime("%H:%M:%S", gmtime(seconds))

    def month_name(self, case, locale, number, source_date):
        if locale not in months:
            return self.date_format(source_date, 'LLLL', locale)
        else:
            return months[locale][case - 1][number][source_date.month - 1]

    def _format_datetime(self, obj, format_str, locale):
        try:
            # will raise if obj.year < 1900
            formatted = (
                self.formater.format_date(obj, format_str, locale=locale)
                if locale
                else obj.strftime(format_str).decode('utf-8')
            )
        except ValueError:
            formatted = None

        return formatted

    def _get_filters(self):
        return {
            "as_date": self.as_date,
            "date_format": self.date_format,
            "mins_from_secs": self.minutes_from_seconds,
            "time_format": self.time_format,
            "time_from_secs": self.time_from_seconds
        }

    def _get_functions(self):
        return {
            "date_now": self.date_now,
            "datetime_now": self.datetime_now,
            "month_name": self.month_name
        }
