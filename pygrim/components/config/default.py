# coding: utf8

DEFAULT_CONFIG = {
    "pygrim": {
        "debug": True,
        "dump_switch": "jkxd",
    },
    "jinja": {
        "debug": True,
        "environment": {
            "autoescape": ("jinja",)
        },
        "extensions": [],
        "suppress_none": True,
        "template_path": "templates"
    },
    "logging": {
        "file": "/tmp/pygrim.log",
        "level": "DEBUG"
    },
    "session": {
        "enabled": True,
        "flash": True,
        "type": "file",
        "args": {
            "session_dir": "/tmp/pygrim_session/"
        }
    },
    "view": {
        "types": ("jinja",)
    }
}
