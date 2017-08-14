# coding: utf8

# std
import cPickle as pickle
from logging import getLogger
from os import mkdir as os_mkdir, path as os_path, remove as os_remove

# local
from .session import Session
from .session_storage import SessionStorage
from .session_exceptions import (
    SessionInitializeError, SessionSaveError, SessionLoadError
)

log = getLogger("pygrim.components.session.file_session_storage")


class FileSessionStorage(SessionStorage):

    PROTOCOL = pickle.HIGHEST_PROTOCOL

    def __init__(self, config):
        super(FileSessionStorage, self).__init__(config)
        self._session_dir = config.get("session:args:session_dir")
        self._create_session_dir()

    def delete(self, session):
        full_path = self._get_path(session.get_id())
        if os_path.isfile(full_path):
            try:
                os_remove(full_path)
                successful = True
            except OSError:
                log.exception("Can't delete session %r", session.get_id())
                successful = False
        else:
            log.error(
                "Deleted session %r does not exist or is not a file",
                session.get_id()
            )
            successful = False

        return successful

    def load(self, request):
        session_id = self._get_id(request)
        try:
            if os_path.isfile(self._get_path(session_id)):
                with open(self._get_path(session_id), "r") as cin:
                    session = pickle.load(cin)
            else:
                session = {}
        except IOError:
            log.exception("Loading session failed!")
            raise SessionLoadError()
        else:
            return Session(session_id, session)

    def save(self, session):
        try:
            with open(self._get_path(session.get_id()), "w") as cout:
                pickle.dump(session.get_content(), cout, self.PROTOCOL)
        except IOError:
            log.exception("Saving session failed!")
            raise SessionSaveError()

    def _create_session_dir(self):
        try:
            os_mkdir(self._session_dir, 0755)
        except OSError as exc:
            # already exists
            if exc.errno != 17:
                raise SessionInitializeError

    def _get_path(self, session_id):
        return os_path.join(self._session_dir, session_id)
