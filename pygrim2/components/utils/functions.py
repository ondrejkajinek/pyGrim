# std
from collections import Mapping
import logging
import re
from unicodedata import normalize as unicodedata_normalize


log = logging.getLogger("pygrim2.components.utils.functions")


REGEXP_TYPE = type(re.compile(r""))
TRAILING_SLASH_REGEXP = re.compile(r"/\??\$?$|\$?$")

# OPTIONAL_PARAM_REGEXP = re.compile(r"\(([^)]*?)(%\(([^)]+)\)s)([^)]*?)\)\?")
# PARAM_REGEXP = re.compile(r"\(\?P<([^>]+)>[^)]+\)")
URL_OPTIONAL_REGEXP = re.compile(r"\(([^)]*?)(%\(([^)]+)\)s)([^)]*?)\)\?")
URL_PARAM_REGEXP = re.compile(r"\(\?P<([^>]+)>[^)]+\)")


def deep_update(original, override):
    for key, value in override.items():
        if isinstance(value, Mapping):
            new_value = deep_update(original.get(key, {}), value)
            original[key] = new_value
        else:
            original[key] = override[key]

    return original


def ensure_bool(val):
    # Václav Pokluda: is ~25% quicker than isinstance(val, bool)
    if val is True or val is False:
        res = val
    elif val is None:
        res = False
    elif isinstance(val, str):
        res = (
            bool(int(val))
            if val.isdigit()
            else val.lower().strip() == "true"
        )
    else:
        res = bool(val)

    return res


def ensure_tuple(variable):
    if isinstance(variable, tuple):
        res = variable
    elif isinstance(variable, (list, set, memoryview)):
        res = tuple(variable)
    else:
        res = (variable,)

    return res


def fix_trailing_slash(pattern):
    if pattern is None:
        return None
    return (
        re.compile(TRAILING_SLASH_REGEXP.sub("/?$", pattern.pattern))
        if is_regex(pattern)
        else pattern.rstrip("/") or "/"
    )


def get_instance_name(instance):
    return get_class_name(instance.__class__)


def get_class_name(cls):
    return "%s.%s" % (cls.__module__, cls.__name__)


def get_method_name(method):
    if method is None:
        return None
    return "%s.%s" % (method.__self__.__class__.__name__, method.__name__)


def is_regex(pattern):
    return isinstance(pattern, REGEXP_TYPE)


def _handle_regex_part(pattern):
    state = {
        "pattern": "",
        "mandatories": set(),
        "optionals": {}
    }
    while pattern:
        char = pattern[0]
        pattern = pattern[1:]
        if char == "\\":
            char = pattern[:1]
            pattern = pattern[1:]
            if not char:
                continue
            # endif
        elif char == ")":
            # elif protože pokud je závorka v escape nechci
            #   ji považovat za závorku
            # jdu o kousek výš, protože mám konec skupiny
            return state, pattern
        elif char == "(":
            # elif protože pokud je závorka v escape nechci
            #   ji považovat za závorku
            group_name = None
            if pattern.startswith("?P<"):
                pattern = pattern[3:]
                idx = pattern.find(">")
                if idx == -1:
                    # not found
                    raise ValueError(
                        "Invalid regular group name starting %r" % (
                            pattern[:10],
                        )
                    )
                group_name = pattern[:idx]
                pattern = pattern[idx + 1:]
            new_state, pattern = _handle_regex_part(pattern)
            optional = False
            if pattern and pattern[0] == "?":
                pattern = pattern[1:]
                optional = True
            # endif
            if group_name:
                if new_state["mandatories"] or new_state["optionals"]:
                    raise ValueError(
                        "Parenthised named groups is forbidden in routing"
                    )
                if optional:
                    state["optionals"][group_name] = "%s"
                else:
                    state["mandatories"].add(group_name)
                state["pattern"] += "%(" + group_name + ")s"
            else:
                if optional:
                    sm = len(new_state["mandatories"])
                    so = len(new_state["optionals"])
                    if (sm + so) > 1:
                        raise ValueError(
                            "Combination of 2 groups in optional part is "
                            "forbidden in routing"
                        )
                    elif (sm + so) == 0:
                        # skip and do not add optional part withot variable
                        pass
                    elif sm:
                        _mandatory = list(new_state["mandatories"])[0]
                        k = "%(" + _mandatory + ")s"
                        state["pattern"] += k
                        state["optionals"][_mandatory] = (
                            new_state["pattern"].replace(k, "%s"))
                    else:
                        ("/((?P<a>.*)b)?", ("/%(a)s", set(), {"a": "%sb"}))
                        _optional = list(new_state["optionals"].keys())[0]
                        k = "%(" + _optional + ")s"
                        state["pattern"] += k
                        state["optionals"][_optional] = (
                            new_state["pattern"].replace(
                                k,
                                new_state["optionals"][_optional]
                            )
                        )
                else:
                    state["mandatories"] = new_state["mandatories"]
                    state["optionals"] = new_state["optionals"]
                    state["pattern"] += new_state["pattern"]
                # endif
            # endif - named group?
            continue
        elif char == "?":
            # pokud mám ? a předtím není skupina dávám pryč předchozí
            #   znak protože je optional
            state["pattern"] = state["pattern"][:-1]
            continue
        # endif

        state["pattern"] += char
    return state, None


def regex_to_readable(pattern):
    # please refer tests on the page end
    # remove start char
    if pattern[:1] == "^":
        pattern = pattern[1:]
    state, pattern = _handle_regex_part(pattern)
    if pattern is not None:
        raise ValueError("Invalid regex pattern")
    # remove trailing /?$ or subpart
    state["pattern"] = remove_trailing_slash(state["pattern"])
    return state["pattern"], state["mandatories"], state["optionals"]


def regex_to_readable_old(pattern):
    # removed! only for referenci of foundy any bug
    param_names = URL_PARAM_REGEXP.findall(pattern)
    readable = URL_PARAM_REGEXP.sub("%(\\1)s", pattern)
    optional_names = {
        optional[2]: "%s%%s%s" % (optional[0], optional[3])
        for optional
        in URL_OPTIONAL_REGEXP.findall(readable)
    }

    readable = URL_OPTIONAL_REGEXP.sub("\\2", readable)
    readable = remove_trailing_slash(readable).lstrip("^")
    readable = readable.replace("\\.", ".")
    mandatory_names = set(param_names) - set(optional_names)
    if len(mandatory_names) + len(optional_names) < len(param_names):
        raise RuntimeError(f"Some keys are duplicate in route {pattern}")
    return readable, mandatory_names, optional_names


def remove_trailing_slash(pattern):
    return (
        re.compile(TRAILING_SLASH_REGEXP.sub("", pattern.pattern))
        if is_regex(pattern)
        else TRAILING_SLASH_REGEXP.sub("", pattern)
    )


def split_to_iterable(value, separator=","):
    return (
        [part.strip() for part in value.split(separator)]
        if isinstance(value, str)
        else value
    )


def strip_accent(text):
    return "".join(
        c for c in unicodedata_normalize("NFKD", text) if ord(c) < 127
    )


if __name__ == "__main__":
    import traceback
    for a, b in (
        # ("", ("", set(), {})),
        ("/(?P<a>.*)", ("/%(a)s", set(("a",)), {})),
        ("/(?P<a>.*)?", ("/%(a)s", set(), {"a": "%s"})),
        ("/((?P<a>.*))?", ("/%(a)s", set(), {"a": "%s"})),
        ("/((?P<a>.*)-b)?", ("/%(a)s", set(), {"a": "%s-b"})),
        ("/((?P<a>.*)?-b)?", ("/%(a)s", set(), {"a": "%s-b"})),
        ("/((?P<a>.*)-b)", ("/%(a)s-b", set("a",), {})),
        ("/(b-(?P<a>.*))?", ("/%(a)s", set(), {"a": "b-%s"})),
        ("/(b-(?P<a>.*)?)?", ("/%(a)s", set(), {"a": "b-%s"})),
        ("/(b-(?P<a>.*))", ("/b-%(a)s", set("a",), {})),
        ("/(?P<a>(cd|ef))", ("/%(a)s", set(("a",)), {})),
        (
            '/(?P<veletrh>((praha2020)|(plzen2020)))/fotogalerie-detail',
            ("/%(veletrh)s/fotogalerie-detail", set(("veletrh",)), {}),
        ),
        (
            '/(?P<veletrh>(praha|plzen)2[0-9]{3})/fotogalerie-detail',
            ("/%(veletrh)s/fotogalerie-detail", set(("veletrh",)), {}),
        ),
    ):
        print(f"\nCheck {a}")
        try:
            v = regex_to_readable(a)
            assert v[0] == b[0], (
                f"unexpected result {v[0]} for {a} - expected {b[0]}"
            )
            assert v[1] == b[1], (
                f"unexpected mandatory params {v[1]} for {a} - expected {b[1]}"
            )
            assert v[2] == b[2], (
                f"unexpected optional params {v[2]} for {a} - expected {b[2]}"
            )
        except BaseException:
            raise
            print(f"ERROR on {a}")
            traceback.print_exc()
            print(regex_to_readable_old(a))
        else:
            print(f"Succes {a}\n\t{v}")

# eof
