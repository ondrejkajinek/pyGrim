# coding: utf8

from os import environ
# from jsonrpc.config import load_config


def load_config(path):
    try:
        with open(path, "rb") as conf_in:
            for line in conf_in:
                # TODO
                pass
    except IOError:
        pass

    return {
        "uwsgi.cwd": "/home/ondrak/public_html/pygrim_test/",
        "jinja.template_path": "templates"
    }

config = load_config(environ["CONF"])
