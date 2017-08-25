# coding: utf8
from logging import getLogger
from uuid import uuid4


log = getLogger("pygrim.session.session_storage")


class SessionStorage(object):

    def __init__(self, config):
        self._config = config
        self._cookie = {
            str(k): getattr(self._config, "get" + t)(
                "session:cookie:" + k, default)
            for k, default, t in (
                ("name", "SESS_ID", ""),
                ("lifetime", 3600 * 24 * 7, "int"),
                ("domain", "", ""),
                ("path", "/", ""),
                ("http_only", False, "bool"),
                ("secure", False, "bool")
            )
        }
        log.debug("Session cookie template:%r", self._cookie)

    def delete(self, session):
        raise NotImplementedError()

    def load(self, request):
        raise NotImplementedError()

    def save(self, session):
        raise NotImplementedError()

    def cookie_for(self, session):
        cookie = self._cookie.copy()
        cookie["value"] = session.get_id()
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
