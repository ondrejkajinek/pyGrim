# coding: utf8

from os import environ
from yaml import load as yaml_load, parser as yaml_parser


DEFAULT_CONFIG = {
    "grim": {
        "mode": "debug"
    },
    "jinja": {
        "debug": True,
        "dump_switch": "jkxd",
        "environment": {
            "autoescape": ("jinja",)
        },
        "i18n": {
            "enabled": False
        },
        "template_path": "templates"
    },
    "view": {
        "enabled": True
    }
}


class ConfigObject(object):

    def __init__(self, config):
        self.config = DEFAULT_CONFIG
        self.config.update(config)

    def get(self, key, default=None):
        try:
            target = self.config
            for part in key.split("."):
                target = target[part]

            return target
        except KeyError:
            if default is None:
                raise

            return default


def load_config(path):
    try:
        with open(path, "rb") as conf_in:
            yaml_string = conf_in.read()
            config = yaml_load(yaml_string)
    except yaml_parser.ParserError as exc:
        print("Error when parsing file %r:\n%s" % (path, exc))
        config = {}
    except IOError as exc:
        print("Error when loading file %r:\n%s" % (path, exc))
        config = {}

    return ConfigObject(config)

config = load_config(environ["CONF"])
