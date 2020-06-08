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


def changelog():
    _fill_changelog()
    _edit_file("debian/changelog")


def check():
    _need_push_pull()
    _edit_file("debian/version")
    _check_repo()


def create_tag():
    tag = "%s-%s" % (name, get_version())
    _call_cmd("git reset HEAD")
    _call_cmd("git add debian/version debian/changelog")
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
    with open("debian/version") as version_in:
        version = version_in.read().strip()

    return version


def _call_cmd(cmd, shell=False, split=True):
    call(shlex_split(cmd) if split else cmd, shell=shell)


def _check_cmd(cmd, shell=False):
    return check_output(
        shlex_split(cmd),
        shell=shell
    ).strip().decode("utf8")


def _check_repo():
    version = get_version()
    cmd = """ssh debian.ats "aptly package search '%s (%s%s)'" """
    current = cmd % (name, "=", version)
    is_current = _check_cmd(current)
    if is_current:
        _error("This version is already in repository!")
        raise RuntimeError("This version is already in repo!")
    else:
        _success("This version is not in repository, proceeding.")

    newer = cmd % (name, ">", version)
    is_newer = _check_cmd(newer)
    if is_newer:
        r = _question(
            """There are newer version than %s in repository (%s),
            do you wish to proceed? [y]es, [n]o (default)""" % (
                version, is_newer
            )
        )
        if r.lower() not in ("y", "yes"):
            raise RuntimeError("Old verion upload was canceled by user.")
    else:
        _success("This would be the latest version in repo, proceeding.")


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


def _fill_changelog():
    write_version_to_changelog = (
        "%s dch -v %s --distribution testing COMMIT MESSASGES"
    ) % (_dch_base(), get_version())
    _call_cmd(write_version_to_changelog, shell=True, split=False)
    last_tag = _get_last_tag()
    _info("Last tag: %s" % last_tag)

    try:
        for message in _commit_messages():
            _write_message(message)
    except CalledProcessError as ex:
        res = _question(
            """[?]\tIt seems no commit happened since last tag.
            Continue anyway? [y]es, [n]o (default)"""
        )
        if res.lower() not in ("y", "yes"):
            raise ex


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


def _write_message(message):
    _info("Writing commit message '%s' to changelog" % message)
    dch = """%s dch -a "%s" """ % (_dch_base(), message)
    _call_cmd(dch, shell=True, split=False)


# # # start of specific part
# # # end of specific part
methods = {
    "check": (check, (), {}),
    "version": (get_version, (), {}),
    "author": (get_author, (), {}),
    "author_email": (get_author_email, (), {}),
    "name": (get_package_name, (), {}),
    "create_tag": (create_tag, (), {}),
    "changelog": (changelog, (), {}),
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
