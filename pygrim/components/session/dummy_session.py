# coding: utf8

from .session import Session
from .session_storage import SessionStorage


class DummySession(SessionStorage):

    def delete(self, session):
        pass

    def load(self, request):
        return Session("__empty__")

    def save(self, session):
        pass
