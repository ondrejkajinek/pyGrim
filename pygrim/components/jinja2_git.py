# coding: utf8

from jinja2.ext import Extension


class GitExtension(Extension):

    tags = set()

    def __init__(self, environment):
        super(GitExtension, self).__init__(environment)

        environment.filters.update(self._get_filters())

    def protectEmail(self, email):
        """
        napíše emailovou adresu pozpátku
        """
        return email[-1::-1]

    def as_date(self, datum, strf=None):
        if isinstance(datum, basestring):
            datum = dt_parser(datum)
        return datum.strftime(strf)

    def _get_filters(self):
        return {
            "protectEmail": self.protectEmail,
            "as_date": self.as_date,
        }
