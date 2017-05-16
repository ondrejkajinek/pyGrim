# coding: utf8


class SessionBaseException(BaseException):
    pass


class SessionInitializeError(SessionBaseException):
    pass


class SessionLoadError(SessionBaseException):
    pass


class SessionSaveError(SessionBaseException):
    pass
