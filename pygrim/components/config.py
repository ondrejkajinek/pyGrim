# coding: utf8

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
    "logging": {
        "file": "/tmp/pygrim.log",
        "level": "DEBUG"
    },
    "view": {
        "enabled": True
    }
}


class ConfigObject(object):

    SEPARATOR = ":"

    def __init__(self, path):
        config = DEFAULT_CONFIG
        config.update(self._load_config(path))
        self.config = config

    def get(self, key, *args, **kwargs):
        try:
            target = self.config
            for part in key.split(self.SEPARATOR):
                target = target[part]

            return target
        except KeyError:
            if len(args):
                return args[0]
            elif "default" in kwargs:
                return kwargs["default"]
            else:
                raise

    def _load_config(self, path):
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

        return config

    def getint(self, key, *args, **kwargs):
        v = self.get(key, *args, **kwargs)
        if not isinstance(v, (int, long)):
            if len(args):
                return args[0]
            elif "default" in kwargs:
                return kwargs["default"]
            else:
                raise TypeError("Wrong value for key:%r" % (key,))
            # endif
        # endif
        return v
    # enddef
