#!/usr/bin/env python

from setuptools import setup, find_packages
import subprocess
import os


def find_files(where, suffixes=("py",)):
    return [
        os.path.join(where, f)
        for f in os.listdir(where)
        if (
            os.path.isfile(os.path.join(where, f)) and
            f.rsplit(".", 1)[-1] in suffixes
        )
    ]


def get_git_val(*val):
    return subprocess.check_output(["git"] + list(val)).strip()


def get_version():
    with open("debian/version") as version_in:
        version = version_in.read().strip()

    return version


name = "pygrim"
desc = "lightweight python frontend framework"

if __name__ == "__main__":
    args = {
        "name": name,
        "version": get_version(),
        "description": desc,
        "author": get_git_val("config", "user.name"),
        "author_email": get_git_val("config", "user.email"),
        "url": "http://www.grandit.cz/",
        "packages": find_packages(),
        "install_requires": (
            "Python >= 2.7",
        )
    }

    setup(**args)
