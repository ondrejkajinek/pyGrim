# coding: utf8


class WrongArgument(Exception):

    def __init__(self, arg_name, value_type, expected_type):
        super(WrongArgument, self).__init__(
            "Wrong value for argument %r, expected %s, received %s" % (
                arg_name, expected_type, value_type
            )
        )


class Checker(object):

    def __init__(self, *args, **kwargs):
        self.optional = kwargs.pop("optional", False)
        self.args = args
        self.kwargs = kwargs

    def __call__(self, val, arg_name, history):
        raise NotImplementedError()


class IntChkr(Checker):

    def __call__(self, val, arg_name, unused_):
        if self.optional and val is None:
            return None

        try:
            val = int(val)
        except (ValueError, TypeError):
            raise WrongArgument(arg_name, repr(type(val)), int)

        if not isinstance(val, int):
            raise WrongArgument(arg_name, repr(type(val)), int)

        return val


class StrChkr(Checker):

    def __call__(self, val, arg_name, unused_):
        if self.optional and val is None:
            return None

        if not isinstance(val, str):
            raise WrongArgument(arg_name, repr(type(val)), str)

        return val
