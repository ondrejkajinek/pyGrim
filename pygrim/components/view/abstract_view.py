# coding: utf8


class AbstractView(object):

    def __init__(self, config, extra_functions):
        raise NotImplementedError(
            "Can't instantiate View interface, use its implementation"
        )

    def display(self, context):
        context.set_response_body(self.render(context))

    def get_template_directory(self):
        return ()

    def render(self, context):
        self._pre_render(context)
        result = self._render(context)
        self._post_render(context)
        return result

    def _initialize_assets(self, config):
        self._css = set(config.get("assets:css", ()))
        self._js = {
            "header": {
                "async": set(config.get("assets:js:header:async", ())),
                "sync": set(config.get("assets:js:header:sync", ()))
            },
            "footer": {
                "async": set(config.get("assets:js:footer:async", ())),
                "sync": set(config.get("assets:js:footer:sync", ()))
            }
        }

    def _initialize_view(self, config):
        self._debug = config.getbool("pygrim:debug", True)
        self._initialize_assets(config)

    def _pre_render(self, context):
        self._template_check(context)
        context.view_data["flashes"] = (
            context.get_flashes()
            if self._use_flash(context)
            else ()
        )

        context.view_data.update({
            "css": tuple(self._css | set(
                set(context.view_data.pop("extra_css", ()))
            )),
            "debug": self._debug,
            "js_header_sync": tuple(self._js["header"]["sync"] | set(
                context.view_data.pop("extra_js_header_sync", ())
            )),
            "js_header_async": tuple(self._js["header"]["async"] | set(
                context.view_data.pop("extra_js_header_async", ())
            )),
            "js_footer_sync": tuple(self._js["footer"]["sync"] | set(
                context.view_data.pop("extra_js_footer_sync", ())
            )),
            "js_footer_async": tuple(self._js["footer"]["async"] | set(
                context.view_data.pop("extra_js_footer_async", ())
            ))
        })

    def _post_render(self, context):
        if self._use_flash(context):
            context.delete_flashes()

    def _render(self, context):
        return ""

    def _template_check(self, context):
        if not context.template:
            raise RuntimeError(
                "Trying to render response but no template has been set."
            )

    def _use_flash(self, context):
        return context.session_loaded() and "_flash" in context.session
