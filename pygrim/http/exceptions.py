# coding: utf8


class HeadersAlreadySent(RuntimeError):

    def __init__(self, reason):
        super(HeadersAlreadySent, self).__init__(
            "Headers have already been sent, %s!" % reason
        )
