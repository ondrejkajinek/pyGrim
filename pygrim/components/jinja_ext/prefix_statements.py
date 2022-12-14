# coding: utf8

from jinja2 import nodes
from jinja2.compiler import CodeGenerator, CompilerExit
from jinja2.ext import Extension

from .new_nodes import PrefixExtends
from .utils import ensure_jinja_iterable


class PrefixStatements(Extension):

    tags = ("prefix_extends", "prefix_include")

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

    def _parse_prefix_extends(self, parser):
        return self._parse_prefix(parser, PrefixExtends)

    def _parse_prefix_include(self, parser):
        node = self._parse_prefix(parser, nodes.Include)
        self._parse_ignore_missing(parser, node)
        res = parser.parse_import_context(node, True)
        return res

    def _parse_prefix(self, parser, class_obj):
        lineno = next(parser.stream).lineno
        node = class_obj(lineno=lineno)
        templates = parser.parse_expression()
        parser.stream.expect("comma")
        prefixes = parser.parse_expression()
        node.template = self._selected_templates(
            ensure_jinja_iterable(templates),
            ensure_jinja_iterable(prefixes)
        )
        return node

    def _selected_templates(self, templates, prefixes):
        return nodes.List([
            nodes.Add(prefix, template)
            for template in templates.items
            for prefix in prefixes.items
        ])


def visit_prefix_extends(self, node, frame):
    """
    Calls the extender.
    This method is copied from jinja2.compiler
    """
    if not frame.toplevel:
        self.fail('cannot use extend from a non top-level scope', node.lineno)

    # if the number of extends statements in general is zero so
    # far, we don't have to add a check if something extended
    # the template before this one.
    if self.extends_so_far > 0:

        # if we have a known extends we just add a template runtime
        # error into the generated code.  We could catch that at compile
        # time too, but i welcome it not to confuse users by throwing the
        # same error at different times just "because we can".
        if not self.has_known_extends:
            self.writeline('if parent_template is not None:')
            self.indent()

        self.writeline('raise TemplateRuntimeError(%r)' % (
            'extended multiple times'
        ))

        # if we have a known extends already we don't need that code here
        # as we know that the template execution will end here.
        if self.has_known_extends:
            raise CompilerExit()
        else:
            self.outdent()

    func_name = 'get_or_select_template'
    if isinstance(node.template, nodes.Const):
        if isinstance(node.template.value, str):
            func_name = 'get_template'
        elif isinstance(node.template.value, (tuple, list)):
            func_name = 'select_template'
    elif isinstance(node.template, (nodes.Tuple, nodes.List)):
        func_name = 'select_template'

    self.writeline('parent_template = environment.%s(' % func_name, node)
    self.visit(node.template, frame)
    self.write(', %r)' % self.name)
    self.writeline('for name, parent_block in parent_template.blocks.%s():' % (
        "items"
    ))
    self.indent()
    self.writeline('context.blocks.setdefault(name, []).append(parent_block)')
    self.outdent()

    # if this extends statement was in the root level we can take
    # advantage of that information and simplify the generated code
    # in the top level from this point onwards
    if frame.rootlevel:
        self.has_known_extends = True

    # and now we have one more
    self.extends_so_far += 1


CodeGenerator.visit_PrefixExtends = visit_prefix_extends
