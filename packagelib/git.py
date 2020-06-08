from __future__ import print_function
import os

from .common import call_cmd, check_cmd, get_version, has_notes, wait_for_yes
from .common import NOTES_FILE
from .output import error, info, success


def quote(unsafe_string):
    "TODO: need to implement function for escaping posibly bad values"
    # info("!!! SECURITY HOLE - Neni naimplementovana funkce pro escapovani")
    unsafe_string.replace('"', "'")
    return unsafe_string


def check_repo(name):
    return
    version = get_version()
    cmd = """ssh debian.ats "aptly package search '%s (%s%s)'" """
    current = cmd % (name, "=", version)
    is_current = check_cmd(current)
    if is_current:
        error("This version is already in repository!")
        raise RuntimeError("This version is already in repo!")
    else:
        success("This version is not in repository, proceeding.")

    newer = cmd % (name, ">>", version)
    is_newer = check_cmd(newer)
    if is_newer:
        wait_for_yes(
            """There are newer version than %s in repository (%s),
            do you wish to proceed? [y]es, [n]o (default)""" % (
                version, is_newer
            ),
            "Old verion upload was denied by user."
        )
    else:
        success("This would be the latest version in repo, proceeding.")


def new_commits(name):
    are_there = False
    for msg in commit_messages(name, include_merges=True):
        print(msg)
        are_there = True
    return are_there


def commit_messages(name, include_merges=False):
    messages_cmd = """git log {}..HEAD --format="%s" .""".format(
        get_last_tag(name)
    )
    for message in check_cmd(messages_cmd).split("\n"):
        if include_merges or not (
            "Merge branch" in message or
            "Merge remote-tracking" in message or
            "version %s" % name in message
        ):
            yield quote(message)


def create_tag(name):
    tag = "%s-%s" % (name, get_version())
    added_files = ["debian/version", "debian/changelog"]
    if has_notes():
        added_files.append(NOTES_FILE)

    if 0 != call_cmd("git reset HEAD"):
        error("git reset faild")
    if 0 != call_cmd("git add %s" % " ".join(added_files)):
        error("git add version info files failed")
    if 0 != call_cmd('git commit -m "version %s"' % tag):
        error("git version commit failed")
    # This will put one commit message per annotation line
    annotate = """git tag "%s" --annotate -m "$( echo -e "%s" )" """ % (
        tag, "\n".join(m.replace('"', '') for m in commit_messages(name))
    )
    if call_cmd(annotate, shell=True, split=False) != 0:
        error("ERRROR creating tag using command: %r" % (repr(annotate),))
        tag_cmd = 'git tag "%s"'
        call_cmd(tag_cmd, shell=True, split=False)
    # endif

    if 0 != call_cmd("git push --follow-tags"):
        error("git push tag failed")
    info("git tag created")


def get_author():
    author = os.environ.get("GIT_AUTHOR_NAME")
    if not author:
        author = check_cmd("git config user.name")
    return author


def get_author_email():
    email = os.environ.get("GIT_AUTHOR_EMAIL")
    if not email:
        email = check_cmd("git config user.email")
    return email


def get_last_tag(name):
    has_tag = bool(check_cmd("git tag -l %s*" % name))
    if has_tag is False:
        first_commit = check_cmd(
            "git log --pretty=format:%H ."
        ).split("\n")[-1]
        call_cmd("git tag %s__preinitial__ %s" % (name, first_commit))

    return check_cmd("git describe --tags --match '%s*' --abbrev=0" % name)


def need_push_pull():
    call_cmd("git fetch")
    behind = check_cmd("git rev-list HEAD..origin/%s" % _current_branch())
    ahead = check_cmd("git rev-list origin/%s..HEAD" % _current_branch())
    if ahead:
        error("You haven't `git push`ed!")
        raise RuntimeError("`git push` required")
    if behind:
        error("You haven't `git pull`ed!")
        raise RuntimeError("`git pull` required")


def submodules():
    submodules_cmd = """git submodule status -- ."""
    for submodule in check_cmd(submodules_cmd).split("\n"):
        submodule = submodule.strip()
        # deinitialized submodules start with "-"
        if submodule and not submodule.startswith("-"):
            try:
                submodule = submodule.strip().split(" ")
                if len(submodule) == 2:
                    commit, path = submodule
                    branch = "detached HEAD"
                else:
                    commit, path, branch = submodule
                yield " Submodule '%s' on branch '%s'" % (path, branch)
            except ValueError:
                error("Submodule '%s' malformed" % (submodule,))


def _current_branch():
    return check_cmd("git symbolic-ref --short HEAD")
