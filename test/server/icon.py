# coding: utf8

from StringIO import StringIO
from PIL import Image


def customized_icon(*args, **kwargs):
    url = "templates/favicon.png"
    background = Image.open(url)
    res = background

    img_io = StringIO()
    res.save(img_io, 'PNG')
    img_io.seek(0)

    return img_io.getvalue()
    # return img_io
# enddef
