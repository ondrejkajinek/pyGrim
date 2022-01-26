# std
from logging import getLogger
from uuid import uuid4

start_log = getLogger("pygrim_start.components.session.session_storage")
log = getLogger("pygrim.components.session.session_storage")


class SessionStorage(object):

    def __init__(self, config):
        self._config = config
        self._cookie = {
            str(key): getattr(self._config, "get" + cast)(
                "session:cookie:" + key, default
            )
            for key, default, cast
            in (
                ("name", "SESS_ID", ""),
                ("lifetime", 92 * 24 * 3600, "int"),  # 92 = 3 měsíce
                ("domain", "", ""),
                ("path", "/", ""),
                ("http_only", False, "bool"),
                ("secure", False, "bool")
            )
        }
        start_log.debug("Session cookie template:%r", self._cookie)

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
        if isinstance(cookie, (tuple, list, set)):
            cookie = cookie[-1]

        if cookie:
            session_id = cookie
            log.debug("Session to be loaded: %r", session_id)
        else:
            session_id = str(uuid4())
            log.debug("Session to be created: %r", session_id)

        return session_id
