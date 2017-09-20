# coding: utf8

from os import path

from jinja2 import nodes
from jinja2.ext import Extension

from utils import ensure_jinja_tuple


class PrefixStatements(Extension):

    tags = ("prefix_extend", "prefix_include")

    def __init__(self, environment):
        super(PrefixStatements, self).__init__(environment)

    def parse(self, parser):
        token = parser.stream.current
        lineno = token.lineno
        res = getattr(self, "_parse_%s" % token.value)(parser)
        res.set_lineno(lineno)
        return res

    def _parse_ignore_missing(self, parser, node):
        if (
            parser.stream.current.test("name:ignore") and
            parser.stream.look().test("name:missing")
        ):
            node.ignore_missing = True
            parser.stream.skip(2)
        else:
            node.ignore_missing = False

    def _parse_prefix_include(self, parser):
        node = nodes.Include(lineno=next(parser.stream).lineno)
        templates = parser.parse_expression()
        parser.stream.expect("comma")
        prefixes = parser.parse_expression()
        self._parse_ignore_missing(parser, node)
        template = self._selected_templates(
            tuple(i.value for i in ensure_jinja_tuple(templates)),
            tuple(i.value for i in ensure_jinja_tuple(prefixes))
        )
        node.template = template
        res = parser.parse_import_context(node, True)
        return res

    def _selected_templates(self, templates, prefixes):
        template_paths = (
            path.join(prefix, template)
            for template in templates
            for prefix in prefixes
        )
        return nodes.Tuple(map(nodes.Const, template_paths), "load")
