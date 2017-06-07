# coding: utf8

from config import AbstractConfig
from routing.router import AbstractRouter
from session.session_storage import SessionStorage
from view.abstract_view import AbstractView


class ComponentException(BaseException):

    def _full_class_name(self, cls):
        return ".".join((cls.__module__, cls.__name__))


class DuplicateContoller(ComponentException):

    def __init__(self, controller):
        super(DuplicateContoller, self).__init__(
            "Another instance of %r is already registered as controller" % (
                self._full_class_name(controller.__class__)
            )
        )


class UnknownController(ComponentException):

    def __init__(self, controller):
        super(UnknownController, self).__init__(
            "Requested controller %r was not registered" % controller
        )


class WrongComponentBase(ComponentException):

    _template = "%r has to be derived from %r."

    def __init__(self, instance, required_parent):
        super(WrongComponentBase, self).__init__(
            self._template % (
                self._full_class_name(instance.__class__),
                self._full_class_name(required_parent)
            )
        )


class WrongConfigBase(WrongComponentBase):

    def __init__(self, instance):
        super(WrongConfigBase, self).__init__(instance, AbstractConfig)


class WrongRouterBase(WrongComponentBase):

    def __init__(self, instance):
        super(WrongRouterBase, self).__init__(instance, AbstractRouter)


class WrongSessionHandlerBase(WrongComponentBase):

    def __init__(self, instance):
        super(WrongSessionHandlerBase, self).__init__(instance, SessionStorage)


class WrongViewBase(WrongComponentBase):

    def __init__(self, instance):
        super(WrongViewBase, self).__init__(instance, AbstractView)
