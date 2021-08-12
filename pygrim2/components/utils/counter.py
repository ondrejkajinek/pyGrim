class Counter(object):

    def __init__(self, start=0):
        self._counter = start

    def __call__(self):
        value = self._counter
        self._counter += 1
        return value

    @property
    def value(self):
        return self._counter
