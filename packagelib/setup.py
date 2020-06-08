from os import chdir, getcwd, listdir, path
from setuptools import setup as do_setup
from subprocess import CalledProcessError

from .common import (
    call_cmd, check_cmd, check_notes, edit_file, get_version, wait_for_yes
)
from .git import (
    check_repo, commit_messages,
    get_author, get_author_email, get_last_tag, need_push_pull, submodules,
    _current_branch
)
from .output import error, info


COPY_CONFIG_CMD = "scp \"{server}:{path}\" \"{config_path}\""
NO_COMMITS_TEXT = """[?]\tIt seems no commit happened since last tag.
Continue anyway? [y]es, [n]o (default)"""


def empty_directory(directory):
    return (directory, ())


def find_files(root, directory, suffixes=("py",), links=True):
    try:
        generator = (
            f
            for f
            in _dir_walker(directory)
            if _file_usable(f, suffixes, links)
        )
        return (root, tuple(generator))
    except OSError:
        error("Error on directory %s" % (path.join(getcwd(), directory)))
        raise


def find_files_recursively(
    root, directory, suffixes=("py",), links=True, exclude_dirs=()
):
    if isinstance(directory, (list, tuple)):
        error("You seem to be using old API of find_files_recursively!")
        error("Please read README or look into backend skeleton.")
        raise RuntimeError("old packagelib is used")

    found_files = []
    dirs = [directory]
    while dirs:
        current_dir = dirs.pop()
        rel_dir = path.relpath(current_dir, directory)
        found_files.append(
            find_files(
                path.normpath(path.join(root, rel_dir)),
                current_dir,
                suffixes,
                links
            )
        )
        dirs.extend(
            f
            for f
            in _dir_walker(current_dir)
            if _dir_usable(f, links, exclude_dirs)
        )

    return found_files


def check(name):
    check_notes()
    need_push_pull()
    has_commits(name)
    _edit_version()
    check_repo(name)


def check_packagelib_update():
    current_dir = getcwd()
    chdir(path.dirname(__file__))
    # just check if packagelib is a git repo
    result = call_cmd("git status --porcelain")
    if result == 0:
        call_cmd("git fetch")
        behind = check_cmd("git rev-list HEAD..origin/%s" % _current_branch())
        if behind:
            wait_for_yes(
                (
                    "Your packagelib is not updated. "
                    "Continue with outdated packagelib?"
                ),
                "Update your packagelib, please"
            )

    chdir(current_dir)


def download_prod_conf(project_root, server):
    _download_config(project_root, server, "prod")


def download_test_conf(project_root, server):
    _download_config(project_root, server, "test")


def has_commits(name):
    if not any(commit_messages(name)):
        wait_for_yes(NO_COMMITS_TEXT, "No commits")


def changelog(name):
    _fill_changelog(name)
    _edit_changelog()


def setup(name, description, **kwargs):
    params = {
        "name": name,
        "version": get_version(),
        "description": description,
        "author": get_author(),
        "author_email": get_author_email()
    }
    params.update(kwargs)
    do_setup(**params)


def _dch_base():
    return """DEBFULLNAME="{author}" DEBEMAIL="{email}" """.format(
        author=get_author(), email=get_author_email()
    )


def _dir_usable(directory, links, exclude_dirs):
    return (
        path.isdir(directory) and
        path.basename(directory) not in exclude_dirs and
        (not path.islink(directory) or links)
    )


def _dir_walker(directory):
    return (
        (path.join(directory, f) for f in listdir(directory) if f[0] != ".")
        if path.isdir(directory)
        else ()
    )


def _download_config(project_root, server, conf_type):
    if not server:
        raise RuntimeError("No production server defined")

    prod_configs = []
    with open(path.join(getcwd(), "debian/conffiles"), "r") as conffiles:
        for line in conffiles:
            if ".{}.".format(conf_type) in line:
                prod_configs.append(line.strip())

    if not prod_configs:
        error("No production config found :(")
        raise RuntimeError("No production config found")

    for prod_config in prod_configs:
        config_dir, config_file = path.split(
            path.relpath(prod_config, project_root)
        )
        cmd = COPY_CONFIG_CMD.format(
            server=server,
            path=prod_config,
            config_path=path.join(getcwd(), config_dir, "real_" + config_file)
        )
        call_cmd(cmd)


def _edit_changelog():
    edit_file("debian/changelog")


def _edit_version(path="debian/version"):
    edit_file(path)


def _file_usable(file_, suffixes, links):
    return (
        path.isfile(file_) and
        (not path.islink(file_) or links) and
        _get_extension(file_) in suffixes
    )


def is_usefull_message(message, name, **kwargs):
    return not(
        "Merge branch" in message or
        "Merge remote-tracking" in message or
        "version %s" % name in message
    )


def _fill_changelog(name):
    write_version_to_changelog = (
        "{base} dch -v {version} --distribution testing COMMIT MESSASGES"
    ).format(base=_dch_base(), version=get_version())
    call_cmd(write_version_to_changelog, shell=True, split=False)
    info("Last tag: %s" % get_last_tag(name))

    try:
        for message in commit_messages(name):
            if message.lower().startswith("version "):
                break
            if is_usefull_message(message, name):
                _write_message(message)
    except CalledProcessError as ex:
        wait_for_yes(NO_COMMITS_TEXT, str(ex))

    used_submodules = list(submodules())
    if used_submodules:
        _write_message(" ")
        _write_message("SUBMODULES")
        submodule = None
        for submodule in used_submodules:
            _write_message(submodule)

        return


def _get_extension(filename):
    return path.splitext(filename)[1][1:]


def _write_message(message):
    info("Writing commit message '%s' to changelog" % message)
    dch = """{base} dch -a -- "{message}" """.format(
        base=_dch_base(), message=message.replace("\"", r"\"")
    )
    call_cmd(dch, shell=True, split=False)
