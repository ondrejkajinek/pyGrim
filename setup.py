#!/usr/bin/env python

from setuptools import setup, find_packages
import subprocess
import os

version = '0.1.4'
name = 'pygrim'
desc = 'lightweight python frontend framework'


def find_files(where, suffixes=("py",)):
    return [
        os.path.join(where, f)
        for f in os.listdir(where)
        if (
            os.path.isfile(os.path.join(where, f)) and
            f.rsplit(".", 1)[-1] in suffixes
        )
    ]
# enddef


def get_git_val(*val):
    return subprocess.check_output(['git'] + list(val)).strip()
# enddef

if __name__ == "__main__":
    args = dict(
        name=name,
        version=version,
        description=desc,
        author=get_git_val('config', 'user.name'),
        author_email=get_git_val('config', 'user.email'),
        url='http://www.grandit.cz/',
        packages=find_packages(),
        install_requires=(
            'Python >= 2.7',
            'compatibility >= 0.0.2',
        )
    )

    setup(**args)
# endif __main__

# eof
