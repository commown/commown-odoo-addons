# Copyright 2020-today Commown SCIC (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import datetime
import logging

import markupsafe

from odoo import _, api, fields, models, tools
from odoo.modules.module import get_resource_path

_logger = logging.getLogger(__name__)


def _check_rate(rate):
    possible_values = set(range(11))
    if rate not in possible_values:
        raise ValueError(
            _("Incorrect rating: should be in %(rates)s (received %(rate)d)"),
            (", ".join(str(value) for value in possible_values), rate),
        )


class Rating(models.Model):
    _inherit = "rating.rating"

    _sql_constraints = [
        (
            "rating_range",
            "check(rating >= 0 and rating <= 10)",
            "Rating should be between 0 and 10",
        ),
    ]

    net_promoter_score = fields.Integer(
        compute="_compute_net_promoter_score",
        string="NPS",
        store=True,
        group_operator="avg",
    )

    rating_text = fields.Selection(
        # We can no longer replace the selection values entirely since 15.0,
        # so we only add new values, old ones should no longer be used anyway.
        selection_add=[
            ("detractor", "Detractor"),
            ("neutral", "Neutral"),
            ("promoter", "Promoter"),
        ],
        string="Rating",
        store=True,
        compute="_compute_rating_text",
        readonly=True,
    )

    @api.depends("rating")
    def _compute_rating_text(self):
        for rating in self:
            if rating.rating >= 9:
                value = "promoter"
            elif rating.rating <= 6:
                value = "detractor"
            else:
                value = "neutral"
            rating.rating_text = value

    @api.depends("rating")
    def _compute_net_promoter_score(self):
        for record in self:
            record.net_promoter_score = (
                (record.rating >= 9 and 100) or (record.rating <= 6 and -100) or 0
            )

    def _get_rating_image_filename(self):
        self.ensure_one()
        return "rate_%s.png" % int(self.rating)

    @api.depends("rating")
    def _compute_rating_image(self):
        self.rating_image_url = False
        self.rating_image = False
        for rating in self:
            try:
                image_path = get_resource_path(
                    "project_rating_nps",
                    "static/src/img",
                    rating._get_rating_image_filename(),
                )
                rating.rating_image_url = (
                    "/project_rating_nps/static/src/img/%s"
                    % rating._get_rating_image_filename()
                )
                if image_path:
                    with open(image_path, "rb") as fobj:
                        rating.rating_image = base64.b64encode(fobj.read())
            except OSError as exc:
                _logger.error(
                    "Could not load rating image for rating id %d: got '%s'",
                    rating.id,
                    exc,
                )


class RatingMixin(models.AbstractModel):
    _inherit = "rating.mixin"

    def rating_apply(
        self,
        rate,
        token=None,
        rating=None,
        feedback=None,
        subtype_xmlid=None,
        notify_delay_send=False,
    ):
        """Overloading of the `rating` module's method to avoid the
        hard-coded rate value errors.
        """
        _check_rate(rate)
        if token:
            rating = self.env["rating.rating"].search(
                [("access_token", "=", token)], limit=1
            )
        if not rating:
            raise ValueError(_("Invalid token or rating."))

        rating.write({"rating": rate, "feedback": feedback, "consumed": True})
        if isinstance(self, self.env.registry["mail.thread"]):
            if subtype_xmlid is None:
                subtype_id = self._rating_apply_get_default_subtype_id()
            else:
                subtype_id = self.env["ir.model.data"]._xmlid_to_res_id(subtype_xmlid)
            feedback = tools.plaintext2html(feedback or "")

            scheduled_datetime = (
                fields.Datetime.now() + datetime.timedelta(hours=2)
                if notify_delay_send
                else None
            )
            rating_body = markupsafe.Markup(
                "<img src='%s' alt=':%s/5' style='width:18px;height:18px;float:left;margin-right: 5px;'/>%s"
            ) % (rating.rating_image_url, rate, feedback)

            if rating.message_id:
                self._message_update_content(
                    rating.message_id,
                    rating_body,
                    scheduled_date=scheduled_datetime,
                    strict=False,
                )
            else:
                self.message_post(
                    author_id=rating.partner_id.id
                    or None,  # None will set the default author in mail_thread.py
                    body=rating_body,
                    rating_id=rating.id,
                    scheduled_date=scheduled_datetime,
                    subtype_id=subtype_id,
                )
        return rating
