# coding: utf8

from logging import getLogger
from pygrim.decorators import method, uses_data, template_method

log = getLogger(__file__)


class VoteIface(object):

    poll_types = {
        1: "klasik",
        2: "stafle",
        3: "duel",
    }

    def postfork(self):
        cfg = self.config.get
        self.vote_resp_ok = cfg("texts:polls:voting:correct")
        self.vote_resp_wrong = cfg("texts:polls:voting:wrong")
        self.vote_resp_error = cfg("texts:polls:voting:error")
        self.txt_form_shown = cfg("texts:polls:form_shown")

    def translate_poll_type(self, type_id):
        return VoteIface.poll_types.get(type_id, "unknown")

    @template_method("polls.jinja", session=True)
    @uses_data('header')
    @uses_data('advertisment')
    @uses_data('feedback_form')
    def polls_list(self, context, category_id=None, **kwargs):
        if category_id is None:
            category_id = context.GET('category_id')
        polls = []
        if category_id is None:
            category_id = self.be.default_poll_category()
        r_polls = self.be.vote_polls_with_options(
            category_id=category_id,
            ip=context.get_request_ip(),
        )
        for poll in r_polls:
            poll['poll_type'] = self.translate_poll_type(poll['poll_type_id'])
            polls.append(poll)
        context.add_js("/js/poll.js", header=True, sync=True)
        r_categories = self.be.poll_categories()
        return {
            "data": {
                "polls": polls,
                "poll_categories": r_categories,
                "poll_category_current": int(category_id),
            }
        }

    @method(session=True)
    def send_votes(self, context):
        POST = context.POST().copy()
        poll_id = POST.pop("poll_id")
        kind = POST.pop("kind", None)
        category = POST.pop("category", None)
        votes = POST.items()
        if kind == "radio":
            votes = [(one[1], one[0], ) for one in votes]
        ip = context.get_request_ip()

        res = self.be.vote_poll_vote_many(
            poll_id=poll_id, votes=votes, ip=ip
        )
        responses = {
            500: self.vote_resp_error,
            403: self.vote_resp_wrong,
            400: self.vote_resp_wrong,
            200: self.vote_resp_ok,
        }
        if res.status != 200:
            flash = responses.get(res.get(res.status, 500))
            context.session.flash("alert-danger", flash)
            self.redirect(
                context, route_name="hitparady",
                params={"category_id": category}
                )
        res.sort(key=lambda tupl: tupl[0], reverse=True)
        highest = res[0]
        alert_class = "alert-danger"
        flash = highest[1]
        if highest[0] in responses.keys():
            flash = responses[highest[0]]
            alert_class = ("alert-success"
                           if highest[0] == 200
                           else "alert-danger")
        context.session.flash(alert_class, flash)
        poll_detail = self.be.poll_detail(poll_id=poll_id)
        assert poll_detail.status == 200, poll_detail.status_message

        if highest == 200 and poll_detail.get('show_contact_form'):
            context.session.flash(
                "alert-success", self.txt_form_shown.format(
                    poll_detail.get('title')
                )
            )
        self.redirect(
            context, route_name="hitparady",
            params={"category_id": category}
        )

    @method(session=True)
    def poll_mail(self, context, *args, **kwargs):
        poll_id = context.POST("poll_id")
        text = context.POST("text")
        category = context.POST("category")

        res = self.be.mail_poll(text=text, poll_id=poll_id)
        if res.status == 200:
            flash = ("alert-success", u"Děkujeme, odesláno.")
        else:
            flash = ("alert-danger", u"Nastala chyba odeslání.")
        context.session.flash(*flash)
        self.redirect(
            context, route_name="hitparady", params={"category_id": category})
