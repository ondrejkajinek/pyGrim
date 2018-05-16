# coding: utf8

# std
from logging import getLogger
from string import strip as string_strip

log = getLogger("pygrim_start.components.connectors.redis")


def connect_redis(config, section="session:args:"):
    """
    helper function for connecting to redis storage
        Host        server where redis is running
        Port        port used for connection to redis
        Password    password, optional
        Database    db number
    """

    try:
        from redis import StrictRedis
    except ImportError:
        log.exception("Cannot import python pyckage: redis")
    else:
        return StrictRedis(
            host=config.get(section + "host"),
            port=config.getint(section + "port", 6379),
            db=config.getint(section + "database"),
            password=config.get(section + "password", None)
        )


def connect_redis_sentinel(config, section="session:args:"):
    try:
        from redis.sentinel import Sentinel
    except ImportError:
        log.exception("Cannot import python pyckage: redis")
        return

    class SentinelWrapper(object):

        def __init__(self, sentinel_conn, master_group_name):
            self.sentinel_conn = sentinel_conn
            self.master_group_name = master_group_name
            self._discover()

        def _discover(self):
            self.master = self.sentinel_conn.master_for(
                self.master_group_name
            )
            # slave nepotrebujeme ;-)
            # self.slave = self.sentinel_conn.slave_for(
            #     self.master_group_name
            # )

        def __getattr__(self, attr):
            return getattr(self.master, attr)

    sentinel_hosts = tuple(
        map(string_strip, i.split(":", 1))
        for i
        in config.get(section + "sentinels", "").split(",")
        if i.strip()
    )

    sh_len = len(sentinel_hosts)

    if sh_len == 0:
        raise RuntimeError("No sentinel configured")
    elif sh_len == 1:
        raise RuntimeError("Only one sentinel configured")
    elif sh_len == 2:
        log.warning(
            "Connecting to 2 sentinels"
            " -> DANGER –> "
            "for more informations read the docs"
        )

    sentinel_obj = Sentinel(
        sentinel_hosts,
        socket_timeout=config.getfloat(section + "socket_timeout", 0.1),
        db=config.getint(section + "database"),
        password=config.get(section + "password", None)
    )

    master_group_name = config.get(section + "master_group_name")
    return SentinelWrapper(sentinel_obj, master_group_name)
