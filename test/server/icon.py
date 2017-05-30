# coding: utf8

from StringIO import StringIO
from PIL import Image
from logging import getLogger

log = getLogger(__name__)


def customized_icon(company="default"):
    url = "static/img/icons/favicon.png"
    background = Image.open(url)
    res = background
    try:
        foreground = Image.open("/root/icon_mask.png")
    except:
        foreground = None
    if foreground:
        foreground = foreground.resize(background.size)
        res = Image.alpha_composite(
            background.convert('RGBA'),
            foreground.convert('RGBA')
        )

    img_io = StringIO()
    res.save(img_io, 'PNG')
    img_io.seek(0)

    return img_io.getvalue()
    # return img_io
# enddef
