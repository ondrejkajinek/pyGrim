# coding: utf8


class Session(dict):

    def __init__(self, session_id, content, new_session):
        self._id = session_id
        self._new = new_session
        super(Session, self).__init__(content)

    def get_content(self):
        return super(Session, self).copy()

    def get_id(self):
        return self._id

    def need_cookie(self):
        return self._new
