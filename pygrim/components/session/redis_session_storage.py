# coding: utf8

from .session import Session
from .session_storage import SessionStorage
from ..connectors import connect_redis, connect_redis_sentinel
from .session_exceptions import (
    # SessionInitializeError,
    SessionSaveError, SessionLoadError
)
from logging import getLogger

import cPickle as pickle

log = getLogger("pygrim.session.redis_session_storage")


class RedisSessionStorageBase(SessionStorage):

    PROTOCOL = pickle.HIGHEST_PROTOCOL

    def __init__(self, config):
        super(RedisSessionStorageBase, self).__init__(config)
        self.redis = None

    def delete(self, session):
        self.redis.delete(session.get_id())
        return True

    def load(self, request):
        session_id, session_new = self._get_id(request)
        try:
            data = self.redis.get(session_id)
            if data:
                session = pickle.loads(data)
            else:
                session = {}
        except IOError:
            log.exception("Loading session failed!")
            raise SessionLoadError()
        else:
            return Session(session_id, session, session_new)

    def save(self, session):
        try:
            ret = self.redis.setex(
                session.get_id(),
                self._cookie["lifetime"],
                pickle.dumps(session.get_content(), self.PROTOCOL)
            )
            if ret is not True:
                raise ValueError("Session not stored to redis")
        except:
            log.exception("Saving session failed!")
            raise SessionSaveError()


class RedisSessionStorage(RedisSessionStorageBase):

    def __init__(self, config):
        super(RedisSessionStorage, self).__init__(config)
        self.redis = connect_redis(config, section="session:args:")


class RedisSentinelSessionStorage(RedisSessionStorageBase):

    def __init__(self, config):
        super(RedisSentinelSessionStorage, self).__init__(config)
        self.redis = connect_redis_sentinel(config, section="session:args:")
