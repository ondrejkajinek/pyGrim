# coding: utf8

# local
from .config import AbstractConfig
from .routing.router import AbstractRouter
from .session.session_storage import SessionStorage
from .utils import get_class_name, get_instance_name
from .view.abstract_view import AbstractView


class ComponentException(BaseException):
    pass


class ComponentTypeAlreadyRegistered(ComponentException):

    def __init__(self, type_, type_name, conflict_class):
        super(ComponentTypeAlreadyRegistered, self).__init__(
            "%s type %r is already registered as class %r" % (
                type_, type_name, get_class_name(conflict_class)
            )
        )


class ControllerAttributeCollision(ComponentException):

    def __init__(self, controller, attr_name, attribute):
        super(ControllerAttributeCollision, self).__init__(
            "Controller %r already has attribute %r: %r" % (
                get_instance_name(controller), attr_name, attribute
            )
        )


class DuplicateContoller(ComponentException):

    def __init__(self, controller):
        super(DuplicateContoller, self).__init__(
            "Another instance of %r is already registered as controller" % (
                get_instance_name(controller)
            )
        )


class UnknownView(ComponentException):

    def __init__(self, view):
        super(UnknownView, self).__init__(
            "Requested view %r was not registered" % view
        )


class WrongComponentBase(ComponentException):

    _template = "%r has to be derived from %r."

    def __init__(self, instance, required_parent):
        super(WrongComponentBase, self).__init__(
            self._template % (
                get_instance_name(instance), get_class_name(required_parent)
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
