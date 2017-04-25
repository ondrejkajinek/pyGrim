# coding: utf8

from uuid import uuid4


class SessionStorage(object):

    def __init__(self, config):
        self._config = config
        self._cookie_key = self._config.get("session:cookie_key", "SESS_ID")

    def delete(self, session):
        raise NotImplementedError()

    def load(self, request):
        raise NotImplementedError()

    def save(self, session):
        raise NotImplementedError()

    def cookie_for(self, session):
        return {
            "name": self._cookie_key,
            "value": session.get_id(),
            "lifetime": None,
            "domain": None,
            "path": None,
            "http_only": None,
            "secure": None
        }

    def _get_id(self, request):
        if self._cookie_key in request.cookies:
            session_id = request.cookies[self._cookie_key]
            session_new = False
        else:
            session_id = str(uuid4())
            session_new = True

        return session_id, session_new
