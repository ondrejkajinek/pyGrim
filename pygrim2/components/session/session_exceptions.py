class SessionBaseException(Exception):
    pass


class SessionInitializeError(SessionBaseException):
    pass


class SessionLoadError(SessionBaseException):
    pass


class SessionSaveError(SessionBaseException):
    pass
