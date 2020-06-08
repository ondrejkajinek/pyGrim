#!/usr/bin/env python3

from sys import argv

from .packagelib import create_tag, find_packages, setup
from .packagelib.setup import (
    check_notes, need_push_pull, has_commits, _edit_version
)

name = "pygrim2"
description = "lightweight python frontend framework"
url = 'https://github.com/ondrejkajinek/pyGrim/tree/pygrim23'


def test():
    from pprint import pprint
    pprint(find_packages())


def check(name):
    check_notes()
    need_push_pull()
    has_commits(name)
    _edit_version("VERSION")


methods = {
    "check": (check, (name,), {}),
    "tag": (create_tag, (name,), {}),
    "test": (test, (), {})
}
if __name__ == "__main__":
    if argv[1] in methods.keys():
        method, args, kwargs = methods[argv[1]]
        method(*args, **kwargs)
        exit(0)
    else:
        req = [
            i.strip() for i in
            open("./system-requirements.txt", "r").readlines()
            if i.strip()
        ] + [
            i.strip() for i in
            open("./grandit-requirements.txt", "r").readlines()
            if i.strip()
        ]
        setup(
            version=open("VERSION", "r").readline().strip(),
            description=description,
            name=name,
            packages=find_packages(),
            url=url,
            install_requires=req,
        )
