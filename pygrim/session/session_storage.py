# coding: utf8
from logging import getLogger
from uuid import uuid4


log = getLogger("pygrim.session.session_storage")


class SessionStorage(object):

    def __init__(self, config):
        self._config = config
        self._cookie = {
            k: self._config.get("session:cookie:" + k, default)
            for k, default in (
                ("name", "SESS_ID"),
                ("lifetime", 3600),
                ("domain", None),
                ("path", "/"),
                ("http_only", False),
                ("secure", False)
            )
        }
        log.debug("Session cookie template:%r", self._cookie)

    def delete(self, session):
        raise NotImplementedError()

    def load(self, request):
        raise NotImplementedError()

    def save(self, session):
        raise NotImplementedError()

    def cookie_for(self, request):
        cookie = self._cookie.copy()
        cookie["value"] = request.session.get_id()
        return cookie

    def _get_id(self, request):
        cookie = request.cookies.get(self._cookie["name"])
        if cookie:
            session_id = cookie
            session_new = False
            log.debug("will be loading session:%r", session_id)
        else:
            session_id = str(uuid4())
            log.debug("created new session:%r", session_id)
            session_new = True

        return session_id, session_new
