#!/usr/bin/python
# -*- coding: utf-8 -*-
from logging import getLogger
log = getLogger("jsonrpc.connectors.redis")


def connect_redis(config, section="session:args:"):
    """
    helper funkce pro napojeni mongo databaze
        Host=       #server na kterem to bezi
        Port=       #port kde to bezi
        Password=   #heslo - optional pokud je neuvedene jede se bez hesla
        Database=   #cislo databaze
    """
    try:
        import redis
    except ImportError:
        log.exception("Nemohu naimportovat python pyckage: redis")
        return
    # endtry

    host = config.get(section + "host")
    port = config.getint(section + "port", 6379)
    db_num = config.getint(section + "database")
    password = config.get(section + "password", None)

    client = redis.StrictRedis(
        host=host,
        port=port,
        db=db_num,
        password=password
    )
    return client
# enddef connect_redis


def connect_redis_sentinel(config, section="session:args:"):
    try:
        from redis.sentinel import Sentinel
    except ImportError:
        log.exception("Nemohu naimportovat python pyckage: redis")
        return
    # endtry

    class SentinelWrapper(object):

        def __init__(self, sentinel_conn, master_group_name):
            self.sentinel_conn = sentinel_conn
            self.master_group_name = master_group_name
            self._discover()
        # enddef

        def _discover(self):
            self.master = self.sentinel_conn.master_for(
                self.master_group_name)
            # slave nepotrebujeme ;-)
            # self.slave = self.sentinel_conn.slave_for(
            #     self.master_group_name)
        # enddef

        def __getattr__(self, attr):
            return getattr(self.master, attr)
        # enddef

    sentinel_hosts = config.get(section + "sentinels")
    sentinel_hosts = [
        i.strip().split(":", 1)
        for i in sentinel_hosts.split(",")
        if i.strip()
    ]

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
    # endif

    timeout = float(config.get(section + "socket_timeout", 0.1))
    master_group_name = config.get(section + "master_group_name")
    db_num = config.getint(section + "database")
    password = config.get(section + "password", None)

    sentinel_obj = Sentinel(
        sentinel_hosts,
        socket_timeout=timeout,
        db=db_num,
        password=password
    )

    return SentinelWrapper(sentinel_obj, master_group_name)
# enddef


# eof
