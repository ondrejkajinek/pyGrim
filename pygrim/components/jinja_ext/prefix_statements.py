# coding: utf8

from logging import getLogger
from os import path

from jinja2 import nodes
from jinja2.exceptions import TemplateNotFound, TemplateSyntaxError
from jinja2.ext import Extension

from utils import ensure_jinja_tuple

log = getLogger("pygrim.components.jinja_ext.prefix_structures")


class PrefixStatements(Extension):

    tags = ("prefix_extend", "prefix_include")

    def __init__(self, environment):
        super(PrefixStatements, self).__init__(environment)

    def parse(self, parser):
        token = parser.stream.current
        lineno = token.lineno
        res = getattr(self, "_parse_%s" % token.value)(parser)
        res.set_lineno(lineno)
        log.critical("PARSE RES: %r", res)
        return res

    def _choose_template(self, templates, prefixes):
        template_paths = (
            path.join(prefix, template)
            for template in templates
            for prefix in prefixes
            for search_path in self.environment.loader.searchpath
            if path.exists(path.join(search_path, prefix, template))
        )
        try:
            return nodes.Const(next(template_paths))
        except StopIteration:
            raise TemplateNotFound(
                "Templates: %r, prefixes: %r" % (templates, prefixes)
            )

    def _fail(self, msg, lineno=None, exc=TemplateSyntaxError):
        lineno = lineno or self.stream.current.lineno
        raise exc(msg, lineno, self.name, self.filename)

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
        template = self._choose_template(
            tuple(i.value for i in ensure_jinja_tuple(templates)),
            tuple(i.value for i in ensure_jinja_tuple(prefixes))
        )
        log.critical("SELECTED TEMPLATE: %r", template)
        node.template = template
        res = parser.parse_import_context(node, True)
        log.critical("RES: %r", res)
        return res
