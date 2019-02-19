# std
from logging import getLogger

log = getLogger("pygrim.components.session.session")


class Session(dict):

    def __init__(self, session_id, *args, **kwargs):
        self._id = session_id
        super(Session, self).__init__(*args, **kwargs)
        log.debug("loaded: %r", self)

    def get_content(self):
        log.debug("saving: %r", self)
        return self.copy()

    def get_id(self):
        return self._id
