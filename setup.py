#!/usr/bin/env python
# coding: utf8

from setuptools import setup, find_packages
from shlex import split as shlex_split
from subprocess import call, check_output, CalledProcessError
from sys import argv, exit, stderr, stdout

ENDC = '\033[0m'
FAIL = '\033[91m'
INFO = "\033[34m"
SUCCESS = "\033[0m"


name = "pygrim2"
desc = "lightweight python frontend framework"


def check():
    _need_push_pull()
    _edit_file("VERSION")


def create_tag():
    tag = "%s-%s" % (name, get_version())
    _call_cmd("git reset HEAD")
    _call_cmd("git add VERSION")
    _call_cmd('git commit -m "version %s"' % tag)
    # This will put one commit message per annotation line
    annotate = """git tag "%s" --annotate -m "$( echo -e "%s" )" """ % (
        tag, "\n".join(_commit_messages())
    )
    _call_cmd(annotate, shell=True, split=False)
    _call_cmd("git push --follow-tags")
    _info("git tag created")


def get_author():
    return _check_cmd("git config user.name")


def get_author_email():
    return _check_cmd("git config user.email")


def get_package_name():
    return name


def get_version():
    with open("VERSION") as version_in:
        version = version_in.read().strip()

    return version


def _call_cmd(cmd, shell=False, split=True):
    call(shlex_split(cmd) if split else cmd, shell=shell)


def _check_cmd(cmd, shell=False):
    return check_output(
        shlex_split(cmd),
        shell=shell
    ).strip().decode("utf8")


def _commit_messages():
    messages_cmd = """git log {}..HEAD --format="%s" .""".format(
        _get_last_tag()
    )
    for message in _check_cmd(messages_cmd).split("\n"):
        if not (
            "Merge branch" in message or
            "version %s" % name in message
        ):
            yield message


def _current_branch():
    return _check_cmd('git name-rev --name-only HEAD')


def _dch_base():
    return """DEBFULLNAME="{author}" DEBEMAIL="{email}" """.format(
        author=get_author(), email=get_author_email()
    )


def _edit_file(filename):
    _call_cmd("${EDITOR} %s" % filename, shell=True, split=False)


def _error(msg):
    stderr.write("%s%s%s\n" % (FAIL, msg, ENDC))


def _get_last_tag():
    has_tag = bool(_check_cmd("git tag -l %s*" % name))
    if has_tag is False:
        _call_cmd("git tag %s__preinitial__" % name)

    return _check_cmd("git describe --tags --match '%s*' --abbrev=0" % name)


def _info(msg):
    stdout.write("%s%s%s\n" % (INFO, msg, ENDC))


def _need_push_pull():
    _call_cmd("git fetch")
    curr = _current_branch()
    behind = _check_cmd("git rev-list HEAD..origin/%s" % curr)
    ahead = _check_cmd("git rev-list origin/%s..HEAD" % curr)
    if ahead:
        _error("You haven't `git push`ed!")
        raise RuntimeError("`git push` required")
    if behind:
        _error("You haven't `git pull`ed!")
        raise RuntimeError("`git pull` required")


def _question(msg):
    _info("[?]\t" + msg)
    return raw_input()


def _success(msg):
    stdout.write("%s%s%s\n" % (SUCCESS, msg, ENDC))


# # # start of specific part
# # # end of specific part
methods = {
    "check": (check, (), {}),
    "version": (get_version, (), {}),
    "author": (get_author, (), {}),
    "author_email": (get_author_email, (), {}),
    "name": (get_package_name, (), {}),
    "create_tag": (create_tag, (), {}),
}
if __name__ == "__main__":
    if argv[1] in methods.keys():
        method, args, kwargs = methods[argv[1]]
        method(*args, **kwargs)
        exit(0)
    else:
        args = {
            "name": name,
            "version": get_version(),
            "description": desc,
            "author": get_author(),
            "author_email": get_author_email(),
            "url": "http://www.grandit.cz/",
            "packages": find_packages(),
            "install_requires": (
                "Python >= 2.7",
            )
        }

        setup(**args)
