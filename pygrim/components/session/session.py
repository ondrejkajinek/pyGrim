# coding: utf8
from logging import getLogger

log = getLogger("pygrim.session.session")


class Session(dict):

    def __init__(self, session_id, *args, **kwargs):
        self._id = session_id
        super(Session, self).__init__(*args, **kwargs)
        if "_flashes" not in self:
            self["_flashes"] = []

        log.debug("loaded: %r", self)

    def get_content(self):
        log.debug("saving: %r", self)
        return super(Session, self).copy()

    def get_id(self):
        return self._id

    def flash(self, _type, value):
        self['_flashes'].append((_type, value))

    def get_flashes(self):
        return self['_flashes']

    def del_flashes(self):
        self['_flashes'] = []
