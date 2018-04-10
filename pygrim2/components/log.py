# coding: utf8

# std
from logging import error as log_error, exception as log_exception
from logging import Formatter, getLogger, handlers
from logging import NOTSET
from multiprocessing import Lock

import logging
import sys


def initialize_loggers(config):
    level_name = config.get("logging:level", "NOTSET")
    level = getattr(logging, level_name, NOTSET)

    main_logger = getLogger()
    main_logger.setLevel(level)
    while main_logger.handlers:
        main_logger.removeHandler(main_logger.handlers[0])

    logger_type = config.get("logging:type", "file").lower()
    log_format = config.get("logging:format", _default_log_format(logger_type))

    if "$(serviceName)s" in log_format:
        log_format = log_format.replace(
            "$(serviceName)s", config.get(
                "logging.serviceName", "UNKNOWN_SERVICE"
            )
        )

    log_format = log_format.replace("$", "%")
    log_formatter = Formatter(log_format)
    handler = None

    if logger_type == "file":
        log_file = config.get("logging:file", "/dev/null")
        if log_file and log_file != "/dev/null":
            handler = LockingFileHandler(log_file)
    elif logger_type == "syslog":
        socket = config.get("logging:socket", "")
        if socket:
            handler = handlers.SysLogHandler(address=socket)
        else:
            host = config.get("logging:host", "localhost")
            port = config.getint("logging:port", 514)
            handler = handlers.SysLogHandler(address=(host, port))
    elif logger_type in ("stdout", "stderr"):
        handler = handlers.StreamHandler(
            stream=getattr(sys, logger_type)
        )

    if handler:
        handler.setFormatter(log_formatter)
        main_logger.addHandler(handler)

    main_logger.propagate = False

    try:
        for logger_name in (config.get("logging:loggers") or {}).iterkeys():
            logger = getLogger(logger_name)
            logger.setLevel(config.get("logging:loggers:%s" % logger_name))
    except KeyError:
        log_error(
            "Missing section for detailed logger settings ([logging.loggers])"
        )
    except:
        log_exception("Error loading logging levels")


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


class LockingFileHandler(handlers.WatchedFileHandler):

    def __init__(self, *args, **kwargs):
        handlers.WatchedFileHandler.__init__(self, *args, **kwargs)
        self._lock = Lock()

    def emit(self, *args, **kwargs):
        self._lock.acquire()
        handlers.WatchedFileHandler.emit(self, *args, **kwargs)
        self._lock.release()
