# -*- coding: utf8 -*-


class ShortcutDict(dict):

    def __init__(self, *args, **kwargs):
        super(ShortcutDict, self).__init__(*args, **kwargs)
        self._shortcuts = {}

    def __contains__(self, item):
        return (
            item in self.iterkeys() or
            self._shortcuts.get(item) and self._shortcuts[item] in self
        )

    def __missing__(self, key):
        # let it raise KeyError
        return self.__getitem__(self._shortcuts[key])

    def add_shortcut(self, shortcut, target):
        self._shortcuts[shortcut] = target


if __name__ == "__main__":
    sd = ShortcutDict()
    sd["a"] = 10
    sd["b"] = 20
    sd.add_shortcut("c", "a")
    print("ShortcutDict: %r" % sd)
    print("sd['a']: %r" % sd["a"])
    print("sd['c']: %r" % sd["c"])
    try:
        print("sd['d']: %r" % sd["d"])
    except KeyError:
        print("'d' is not in sd, ok")
    except BaseException:
        raise

    print("'c' in sd: %r" % ("c" in sd,))
    print("'d' in sd: %r" % ("d" in sd,))
