import os.path
from shlex import split as shlex_split
from subprocess import call, check_output

from .output import info, question


NOTES_FILE = "package_notes"


def call_cmd(cmd, shell=False, split=True, stdout=None, stderr=None):
    return call(
        shlex_split(cmd) if split else cmd,
        stdout=stdout,
        stderr=stderr,
        shell=shell
    )


def check_cmd(cmd, shell=False):
    return check_output(shlex_split(cmd), shell=shell).strip().decode("utf8")


def check_notes():
    if get_notes():
        edit_file(NOTES_FILE)
        if get_notes():
            wait_for_yes(
                "You have unresolved notes. Do you wish to continue?",
                "Unresolved notes"
            )


def edit_file(name):
    call_cmd("${EDITOR} %s" % name, shell=True, split=False)


def get_notes():
    notes = ""
    try:
        with open(NOTES_FILE, "r") as note_file:
            notes = note_file.read().strip()
    except IOError:
        notes = ""

    return notes


def get_version(source=None):
    if not source:
        source = "debian/version"
        if os.path.exists("VERSION"):
            source = "VERSION"
    with open(source, "r") as version_cin:
        version = version_cin.read().strip()

    return version


def has_notes():
    try:
        note_file = open(NOTES_FILE, "r")
    except IOError:
        has = False
    else:
        note_file.close()
        has = True

    return has


def wait_for_yes(quest_message, stop_reason):
    question(quest_message)
    resp = ""
    while resp.lower() not in ("y", "yes"):
        info("If you want to continue, enter [Y]es")
        resp = input()
        if resp.lower() not in ("y", "yes"):
            raise RuntimeError(stop_reason)
