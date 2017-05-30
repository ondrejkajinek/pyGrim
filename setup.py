#!/usr/bin/env python

from setuptools import setup, find_packages
import subprocess
import os
from sys import argv


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


def edit_version():
    subprocess.call(('${EDITOR} debian/version'), shell=True)


def check_repo():
    cmd = """ssh debian.ats "aptly package search \\
            \'{pkg_name}, Version ({operator}{version})\'" """
    current = cmd.format(
        pkg_name=name, version=get_version(), operator="="
    )
    is_current = subprocess.check_output([current], shell=True)
    if is_current:
        print "[E]\ttato verze uz v repu je"
        raise Exception("tato verze uz v repu je")
    else:
        print "[OK]\ttato verze v repu neni, muzu pokracovat"

    newer = cmd.format(
        pkg_name=name, version=get_version(), operator=">"
    )
    is_newer = subprocess.check_output([newer], shell=True)
    if is_newer:
        text = """[?]\tv repu jsou uz novejsi verze {},
        pokracovat? [a]no, [n]e - vychozi """.format(is_newer)
        r = raw_input(text)
        if r != "a":
            raise Exception('odmitnuto pridani starsi verze')
    else:
        print "[OK]\tnovejsi verze v repu neni, pokracuju"


def fill_changelog():
    last_tag = subprocess.check_output(
        "git describe --tags --match '{pkg_name}*' --abbrev=0".format(
            pkg_name=name)
    )
    print "last tag" + last_tag
    commit_messages = subprocess.check_output(
        "git log ${LAST_TAG}..HEAD --format=' %s ;' . |grep -v 'Merge branch')"
    )
    print "commit_messages" + commit_messages

# LAST_TAG:=$(shell git describe --tags --match '${PACKAGE_NAME}*' --abbrev=0)
# COMMIT_MESSAGES:=`git log ${LAST_TAG}..HEAD --format=' %s ;' . | grep -v 'Merge branch')`
# # echo last tag: ${LAST_TAG}
# # echo "commit messges: ${COMMIT_MESSAGES}"
# dch -a "LIST OF COMMIT MESSAGES:"
# for i in "${COMMIT_MESSAGES}"; do dch -a $$i; done


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
    if argv[1] == "check":
        edit_version()
        check_repo()
        fill_changelog()
    else:
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
                "compatibility >= 0.0.2",
            )
        }

        setup(**args)
