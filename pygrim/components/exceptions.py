# coding: utf8

from .config import AbstractConfig
from .routing.router import AbstractRouter
from .session.session_storage import SessionStorage
from .utils import get_class_name, get_instance_name
from .view.abstract_view import AbstractView


class WrongComponentBase(BaseException):

    _template = "%r has to be derived from %r."

    def __init__(self, instance, required_parent):
        super(WrongComponentBase, self).__init__(
            self._template % (
                get_instance_name(instance),
                get_class_name(required_parent)
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
