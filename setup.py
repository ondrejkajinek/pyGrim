#!/usr/bin/env python
# coding: utf8

from setuptools import setup, find_packages
import subprocess
import os
from sys import argv, stderr, exit


name = "pygrim"
desc = "lightweight python frontend framework"
FAIL = '\033[91m'
ENDC = '\033[0m'


def find_files(where, suffixes=("py",), links=True):
    files = []
    try:
        for f in os.listdir(where):
            full_path = os.path.join(where, f)

            if not os.path.isfile(full_path):
                stderr.write("not file %r\n" % (f,))
                continue
            # endif
            if not links and os.path.islink(full_path):
                stderr.write("link %r\n" % (f,))
                continue
            # endif
            if f.rsplit(".", 1)[-1] not in suffixes:
                stderr.write("not suffix %r\n" % (f,))
                continue
            # endif
            stderr.write("!add %r\n" % (f,))
            files.append(full_path)
        # endif
    except OSError:
        stderr.write(
            FAIL + "Err on dir %s/%s" % (os.getcwd(), where) + ENDC + "\n")
        raise
    return files


def get_git_val(*val):
    return subprocess.check_output(["git"] + list(val)).strip()


def get_version():
    with open("debian/version") as version_in:
        version = version_in.read().strip()

    return version


def get_package_name():
    return name


def call_cmd(cmd):
    subprocess.call([cmd], shell=True)


def check_cmd(cmd):
    return subprocess.check_output([cmd], shell=True).strip()


def current_branch():
    return check_cmd('git name-rev --name-only HEAD')


def need_push_pull():
    call_cmd("git fetch")
    behind = check_cmd("git rev-list HEAD..origin/{}".format(current_branch()))
    ahead = check_cmd("git rev-list origin/{}..HEAD".format(current_branch()))
    if ahead:
        print "[E]\t nemas pushnuto"
        raise Exception('je treba pushnout')
    if behind:
        print "[E]\t nemas pulnuto"
        raise Exception('je treba pullnout')


def edit_version():
    call_cmd('${EDITOR} debian/version')


def check_repo():
    version = get_version()
    cmd = """ssh debian.ats "aptly package search \\
            \'{pkg_name}, \$Version ({operator}{version})\'" """
    current = cmd.format(
        pkg_name=name, version=version, operator="="
    )
    is_current = check_cmd(current)
    if is_current:
        print "[E]\ttato verze uz v repu je"
        raise Exception("tato verze uz v repu je")
    else:
        print "[OK]\ttato verze v repu neni, muzu pokracovat"

    newer = cmd.format(
        pkg_name=name, version=version, operator=">"
    )
    is_newer = check_cmd(newer)
    if is_newer:
        text = """[?]\tv repu jsou uz novejsi verze nez {version}\n {newer},
        pokracovat? [a]no, [n]e - vychozi """.format(
            version=version, newer=is_newer)
        r = raw_input(text)
        if r != "a":
            raise Exception('odmitnuto pridani starsi verze')
    else:
        print "[OK]\tnovejsi verze v repu neni, pokracuju"


def fill_changelog():
    write_version_to_changelog = \
        "DEBFULLNAME='{author}' dch -v {version} --distribution testing COMMIT MESSASGES".format(
            author=get_git_val('config', 'user.name'), version=get_version()
        )
    call_cmd(write_version_to_changelog)
    tag_cmd = "git describe --tags --match '{pkg_name}*' --abbrev=0".format(
        pkg_name=name)
    last_tag = check_cmd(tag_cmd)
    last_tag = last_tag.strip()
    print "[I]\tlast tag " + last_tag

    try:
        messages_cmd = "git log {last_tag}..HEAD --format='%s' . |\
            grep -v 'Merge branch' | \
            grep -v 'version {pkg}'".format(last_tag=last_tag, pkg=name)
        commit_messages = check_cmd(messages_cmd)
        commit_messages = commit_messages.strip()
        messages_list = commit_messages.split('\n')
        for message in messages_list:
            print "[I]\t zapisuju commit message {} do changelogu".format(
                message)
            call_cmd("DEBFULLNAME='{author}' dch -a '{message}'".format(
                message=message, author=get_git_val('config', 'user.name')
                )
            )
    except subprocess.CalledProcessError as ex:
        res = raw_input("""[?]\tzda se, ze od posledniho tagu nejsou zandne commity
            presto pokracovat [a]no, [n]e default
        """)
        if res != "a":
            raise ex
        return


def create_tag():
    tag = "{}-{}".format(name, get_version())
    call_cmd("git reset HEAD")
    call_cmd("git add debian/version debian/changelog")
    call_cmd('git commit -m "version {tag}"'.format(tag=tag))
    call_cmd('git tag "{tag}"'.format(tag=tag))
    call_cmd("git push --follow-tags")
    call_cmd("git push --tags")
    print "tag done"


# # # start of specific part
# # # end of specific part
methods = {
    "version": (get_version, (), {}),
    "author": (get_git_val, ('config', 'user.name'), {}),
    "author_email": (get_git_val, ('config', 'user.email'), {}),
    "name": (get_package_name, (), {}),
    "create_tag": (create_tag, (), {}),
    "fill_changelog": (fill_changelog, (), {}),
}
if __name__ == "__main__":
    if argv[1] in methods.keys():
        method, args, kwargs = methods[argv[1]]
        print method(*args, **kwargs)
        exit(0)
    elif argv[1] == "check":
        need_push_pull()
        edit_version()
        check_repo()
        fill_changelog()
        create_tag()
        exit(0)
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
