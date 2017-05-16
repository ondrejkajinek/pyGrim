# coding: utf8
from logging import getLogger

log = getLogger("pygrim.session.session")


class Session(dict):

    def __init__(self, session_id, content, new_session):
        self._id = session_id
        self._new = new_session
        content['_flashes'] = content.get('_flashes', [])
        log.debug("loaded:%r", content)
        super(Session, self).__init__(content)

    def get_content(self):
        log.debug("saving:%r", self)
        return super(Session, self).copy()

    def get_id(self):
        return self._id

    def flash(self, _type, value):
        self['_flashes'].append((_type, value))

    def get_flashes(self):
        return self['_flashes']

    def del_flashes(self):
        self['_flashes'] = []

    def need_cookie(self):
        return self._new
