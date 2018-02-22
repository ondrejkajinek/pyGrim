# coding: utf8

from .abstract_view import AbstractView


class BaseView(AbstractView):

    def _add_assets(self, context):
        context.view_data.update({
            "css": self._css + context.view_data.pop("extra_css", []),
            "debug": self._debug,
            "js_header_sync": (
                self._js_header_sync +
                context.view_data.pop("extra_js_header_sync", [])
            ),
            "js_header_async": (
                self._js_header_async +
                context.view_data.pop("extra_js_header_async", [])
            ),
            "js_footer_sync": (
                self._js_footer_sync +
                context.view_data.pop("extra_js_footer_sync", [])
            ),
            "js_footer_async": (
                self._js_footer_async +
                context.view_data.pop("extra_js_footer_async", [])
            )
        })

    def _initialize_assets(self, config):
        self._css = config.get("assets:css", [])
        self._js_header_async = config.get("assets:js:header:async", [])
        self._js_header_sync = config.get("assets:js:header:sync", [])
        self._js_footer_async = config.get("assets:js:footer:async", [])
        self._js_footer_sync = config.get("assets:js:footer:sync", [])

    def _initialize_view(self, config):
        self._debug = config.getbool("pygrim:debug", True)
        self._initialize_assets(config)

    def _pre_render(self, context):
        self._template_check(context)
        self._add_assets(context)

    def _post_render(self, context):
        pass

    def _render(self, context):
        self._pre_render(context)
        result = self._render_template(context)
        self._post_render(context)
        return result

    def _render_template(self, context):
        raise NotImplementedError()

    def _template_check(self, context):
        if not context.template:
            raise RuntimeError(
                "Trying to render response but no template has been set."
            )
