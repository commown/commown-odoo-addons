# Copyright 2020-today Commown SCIC (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import http
from odoo.http import request
from odoo.tools.misc import get_lang

from odoo.addons.rating.controllers.main import Rating

from ..models.rating import _check_rate


class NetPromoterScoreRating(Rating):
    @http.route()
    def action_open_rating(self, token, rate, **kwargs):
        "Override to allow all NPS rates and set NPS rate names (no other change)."

        _check_rate(rate)
        rating_sudo, _record_sudo = self._get_rating_and_record(token)

        lang = rating_sudo.partner_id.lang or get_lang(request.env).code
        view_model = request.env["ir.ui.view"].with_context(lang=lang)

        return view_model._render_template(
            "project_rating_nps.rating_external_page_submit",
            {
                "rating": rating_sudo,
                "token": token,
                "rate_names": {rate: str(rate) for rate in range(11)},
                "rate": rate,
            },
        )

    @http.route()
    def action_submit_rating(self, token, rate=0, **kwargs):
        "Override to allow all NPS rates and set NPS rate names (no other change)."

        rating, record_sudo = self._get_rating_and_record(token)
        if request.httprequest.method == "POST":
            rate = int(rate)
            _check_rate(rate)
            record_sudo.rating_apply(
                rate,
                rating=rating,
                feedback=kwargs.get("feedback"),
                subtype_xmlid=None,  # force default subtype choice
            )

        lang = rating.partner_id.lang or get_lang(request.env).code
        view_model = request.env["ir.ui.view"].with_context(lang=lang)

        return view_model._render_template(
            "rating.rating_external_page_view",
            {
                "web_base_url": rating.get_base_url(),
                "rating": rating,
            },
        )
