# coding: utf8

from logging import getLogger

from jsonrpc.RPCClient import RPCClient

log = getLogger("connector")


class Connector(object):

    def _con_rpc(self, attr, section):
        if not hasattr(self, attr) or not getattr(self, attr):

            try:
                c = self.config
                section = "rpc:" + section + ":"
                construct_args = dict(
                    host=c.get(section + "host"),
                    port=c.getint(section + "port", 80),
                    path=c.get(section + "path", ""),
                    proto=c.get(section + "proto", "http"),
                    timeout=c.getint(section + "timeout", 10),
                    status_as_attr=True,
                    ssl_verify=True,
                    enable_bson=False,
                    cache_call_type=c.get(section + "cache_call_type", None),
                    proxy_exc=False
                )
                setattr(
                    self,
                    attr,
                    RPCClient(**construct_args)
                )
            except:
                log.exception("Nepodarilo se inicializovat rpc:%r", attr)
                log.critical("Nepodarilo se inicializovat rpc:%r", attr)
            # endtry
        # endif

    def postfork(self):
        self._con_rpc("be", "slagr-tv-backend")
        self._con_rpc("epg", "epg")
    # endde

    def stat(self):
        pass

# eof
