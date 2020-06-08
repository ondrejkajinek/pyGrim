from os import path

from .common import get_version
from .output import error
from .scripts import link_config, upgrade_pip_package


KNOWN_METHODS = {
    "link_config": link_config,
    "upgrade_pip_package": upgrade_pip_package
}


def finalize_debscripts(name):
    for script in ("preinst", "prerm", "postinst", "postrm"):
        full_path = path.join(
            "build", "%s-%s" % (name, get_version()), "debian", script
        )
        if path.isfile(full_path):
            _process_script(full_path)


def _add_methods(script_path, required_methods, has_shebang):
    try:
        original = ""
        with open(script_path, "r") as cin:
            if has_shebang:
                shebang = next(cin)

            for line in cin:
                original += line

        new = shebang if has_shebang else ""
        for method in required_methods:
            new += KNOWN_METHODS[method]

        new += original

        with open(script_path, "w") as cout:
            cout.write(new)
    except IOError:
        error("Can't write to file %r" % script_path)
        raise


def _file_iterator(file_path):
    try:
        with open(file_path, "r") as cin:
            for line in cin:
                yield line
    except IOError:
        error("Can't open file %r" % file_path)
        raise


def _process_script(script_path):
    required_methods, has_shebang = _search_file(script_path)
    if required_methods:
        _add_methods(script_path, required_methods, has_shebang)


def _search_file(script_path):
    first_line = True
    required_methods = set()
    has_shebang = False
    for line in _file_iterator(script_path):
        if first_line:
            has_shebang = line.startswith("#!")
            first_line = False

        if not line.startswith("#"):
            for method in KNOWN_METHODS:
                if method in line:
                    required_methods.add(method)

    return required_methods, has_shebang
