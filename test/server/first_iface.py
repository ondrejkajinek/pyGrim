# coding: utf8

from logging import getLogger
from pygrim.decorators import method, uses_data, template_method
from icon import customized_icon
from dateutil.parser import parse as parse_dt
from datetime import datetime
import requests

log = getLogger(__file__)


class FirstIface(object):

    def postfork(self):
        self.captcha_js_url = self.config.get('captcha:js-url')
        self.captcha_site_key = self.config.get('captcha:site-key')
        self.captcha_secret_key = self.config.get('captcha:secret-key')
        self.captcha_api_url = self.config.get('captcha:api-url')

    @template_method('index.jinja', session=True)
    @uses_data('header')
    @uses_data('advertisment')
    @uses_data('feedback_form')
    def index(self, context):
        return {
            "data": {
            },
        }

    @method(session=True)
    def napiste(self, context, *args, **kwargs):
        name, email, message = map(context.POST, ["jmeno", "email", "zprava"])
        captcha = context.POST('g-recaptcha-response')
        ip = context.get_request_ip()
        page = context.POST("page")
        log.debug("captcha %s", captcha)
        is_human = self.verify_captcha(ip=ip, response=captcha)
        if is_human:
            res = self.be.write_us(
                name=name, email=email, message=message, ip=ip,
            )
            if res.status == 200:
                flash = (
                    "alert-success",
                    u"Děkujeme za Váš vzkaz! Vaše Šlágr TV"
                )
            else:
                flash = ("alert-danger", u"Nastala chyba odesílání.")
        else:
            flash = ("alert-danger", u"Nepovedlo se Vás ověřit.")
        context.session.flash(*flash)
        self.redirect(context, url=page)

    @template_method('snippets/forecast.jinja')
    def forecast(self, context):
        res = self.be.forecast_get()
        assert res.status == 200, res.status_message
        res["time"] = parse_dt(res["time"])
        return {"data": res}

    def teasers(self, section=None):
        return self.be.teasers_get(section=section)

    def get_adds(self):
        return self.be.teasers_get(section="reklama")

    def concerts_list(self, **kwargs):
        sorters = [{"column": "release_date", "ascending": True}]
        filters = {"release_date": [datetime.now(), None]}
        res = self.be.concert_list(sorters=sorters, filters=filters)
        assert res.status == 200, res.status_message
        return res['items']

    @method()
    def favicon(self, context):
        context.set_response_body(customized_icon())
        context.set_response_content_type("image/png")

    @method()
    def header(self, context):
        return {
            "data": {
            }
        }

    @method()
    def advertisment(self, context):
        return {
            "data": {
            }
        }

    @method()
    def feedback_form(self, context):
        context.add_js(
            self.captcha_js_url, "/js/captcha_callback.js",
            header=True, sync=False
        )
        return {
            "data": {
                "captcha_site_key": self.captcha_site_key,
            }
        }

    def verify_captcha(self, response=None, ip=None):
        url = self.captcha_api_url
        data = {
            "secret": self.captcha_secret_key,
            "response": response,
            "remoteip": ip
        }
        res = requests.post(url, data=data, verify=False)
        if res.status_code != 200:
            log.error(
                "aptcha error returned status %s, text %s; data %s",
                res.status, res.text, data)
            return False
        json = res.json()
        return json['success']
