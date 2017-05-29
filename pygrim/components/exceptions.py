# coding: utf8

from routing.router import AbstractRouter
from session.session_storage import SessionStorage
from view.abstract_view import AbstractView


class WrongComponentBase(BaseException):

    _template = "%r has to be derived from %r."

    def __init__(self, instance, required_parent):
        super(WrongComponentBase, self).__init__(
            self._template % (
                self._full_class_name(instance.__class__),
                self._full_class_name(required_parent)
            )
        )

    def _full_class_name(self, cls):
        return ".".join((cls.__module__, cls.__name__))


class WrongRouterBase(WrongComponentBase):

    def __init__(self, instance):
        super(WrongRouterBase, self).__init__(instance, AbstractRouter)


class WrongSessionHandlerBase(WrongComponentBase):

    def __init__(self, instance):
        super(WrongSessionHandlerBase, self).__init__(instance, SessionStorage)


class WrongViewBase(WrongComponentBase):

    def __init__(self, instance):
        super(WrongViewBase, self).__init__(instance, AbstractView)
