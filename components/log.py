# coding: utf8

from logging import handlers as logging_handlers
from multiprocessing import Lock

import logging
import sys


def initialize_loggers(config):
    level = config.get("logging.level", "NOTSET")
    try:
        level = getattr(logging, level)
    except AttributeError:
        level = logging.NOTSET

    logger = logging.getLogger()
    logger.setLevel(level)
    while logger.handlers:
        logger.removeHandler(logger.handlers[0])

    logger_type = config.get("logging.type", "file").lower()
    log_format = (
        config.get(
            "logging.format", _default_log_format(logger_type)
        )
    )

    if "$(serviceName)s" in log_format:
        log_format = log_format.replace(
            "$(serviceName)s", config.get(
                "logging.serviceName", "UNKNOWN_SERVICE"
            )
        )

    log_format = log_format.replace("$", "%")
    log_formatter = logging.Formatter(log_format)
    handler = None

    if logger_type == "file":
        log_file = config.get("logging.file", "/dev/null")
        if log_file and log_file != "/dev/null":
            handler = LockingFileHandler(log_file)
    elif logger_type == "syslog":
        host = config.get("logging.host", "localhost")
        port = config.get("logging.port", 514)
        socket = config.get("logging.socket", "")
        if socket:
            handler = logging.handlers.SysLogHandler(address=socket)
        else:
            handler = logging.handlers.SysLogHandler(address=(host, port))
    elif logger_type in ("stdout", "stderr"):
        handler = logging.handlers.StreamHandler(
            stream=getattr(sys, logger_type)
        )

    if handler:
        handler.setFormatter(log_formatter)
        logger.addHandler(handler)

    logger.propagate = False

    try:
        for logger in (config.get("logging.loggers") or {}).iterkeys():
            l = logging.getLogger(logger)
            l.setLevel(config.get("logging.loggers.%s" % logger))
    except KeyError:
        logging.error(
            "Chybí sekce na detailní nastavení loggerů ([logging.loggers])")
    except:
        logging.exception("Chyba načítání detailních loglevelů")


def _default_log_format(logger_type):
    if logger_type == "syslog":
        log_format = (
            "{$(serviceName)s} $(processName)s/$(threadName)s "
            "[$(process)d/$(thread)d] $(levelname)s: $(message)s "
            "($(filename)s: $(funcName)s: $(lineno)d)"
        )
    else:
        log_format = (
            "$(asctime)s [pid: $(process)d] $(levelname)s $(name)s "
            "$(filename)s $(funcName)s: $(message)s"
        )

    return log_format


class LockingFileHandler(logging_handlers.WatchedFileHandler):

    def __init__(self, *args, **kwargs):
        logging_handlers.WatchedFileHandler.__init__(self, *args, **kwargs)
        self._lock = Lock()

    def emit(self, *args, **kwargs):
        self._lock.acquire()
        logging_handlers.WatchedFileHandler.emit(self, *args, **kwargs)
        self._lock.release()
