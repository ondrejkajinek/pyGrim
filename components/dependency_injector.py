# coding: utf8

from logging import getLogger

log = getLogger("pygrim.dependency_injector")


class BaseDependencyException(Exception):
    pass


class UnknownComponent(BaseDependencyException):

    def __init__(self, key):
        super(UnknownComponent, self).__init__(
            "Component %r is not registered." % key
        )


class DependencyContainer(object):

    def __init__(self):
        super(DependencyContainer, self).__setattr__("_components", {})

    def __delattr__(self, key):
        self.unregister(key)

    def __getattr__(self, key):
        return self.resolve(key)

    def __setattr__(self, key, value):
        self.register(key, value)

    def get(self, key, *args, **kwargs):
        try:
            return self.resolve(key)
        except UnknownComponent:
            if len(args):
                return args[0]
            else:
                return kwargs.get("default")

    def register(self, key, value):
        log.debug("Registering component %r", key)
        self._components[key] = value

    def registered(self, key):
        return key in self

    def resolve(self, key):
        log.debug("Looking for component %r", key)
        try:
            data = self._components[key]
            return data(self) if hasattr(data, "__call__") else data
        except KeyError:
            raise UnknownComponent(key)

    def singleton(self, key, value):
        def singleton_closure(dic):
            singleton = value(self) if hasattr(value, "__call__") else value
            self.register(key, singleton)
            return singleton

        log.debug("Registering singleton %r", key)
        self.register(key, singleton_closure)

    def unregister(self, key):
        log.debug("Deleting component %r", key)
        del self._components[key]
