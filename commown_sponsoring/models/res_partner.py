import random

from odoo import _, fields, models

MAX_SPONSOR_CODE_REROLLS = 3


class SponsoringResPartner(models.Model):
    _inherit = "res.partner"

    sponsor_campaign_id = fields.Many2one(comodel_name="coupon.campaign", readonly=True)
    sponsor_code = fields.Char(
        string="Sponsor code", related="sponsor_campaign_id.name"
    )

    def is_sponsor_code_active(self):
        "Returns whether the sponsor code is active (ie. the customer has contracts currently ongoing)"
        self.ensure_one()
        active_contracts = self.env["contract.contract"].search_count(
            [
                ("commercial_partner_id", "=", self.commercial_partner_id.id),
                ("contract_type", "=", "sale"),
                ("date_start", "<=", fields.Date.today()),
                "|",
                ("date_end", ">=", fields.Date.today()),
                "&",
                ("date_end", "=", False),
                ("recurring_next_date", "!=", False),
            ]
        )
        return active_contracts > 0

    def _create_sponsor_campaign(self):
        Campaign = self.env["coupon.campaign"]
        Coupon = self.env["coupon.coupon"]

        for partner in self:
            partner = partner.commercial_partner_id

            # We wish to only have one sponsor campaign per customer/company
            if not partner.sponsor_campaign_id:
                for _i in range(MAX_SPONSOR_CODE_REROLLS):
                    code = "P-" + "".join(
                        random.choice(Coupon._coupon_allowed_chars)
                        for _char in range(Coupon._coupon_code_size)
                    )
                    if not Campaign.search([("name", "=", code)]):  # pragma: no cover
                        break
                else:  # pragma: no cover
                    raise RuntimeError("Unable to generate a unique sponsor code!")

                desc = _(
                    "Congratulations! you will benefit from a free monthly installment, "
                    "thanks to a sponsorship from %s! This discount will be applied on "
                    "the second monthly installment (not applicable on the initial deposit).",
                    partner.display_name,
                )

                Campaign = Campaign.with_context(lang=partner.lang)
                partner.sponsor_campaign_id = Campaign.create(
                    {
                        "name": code,
                        "description": desc,
                        "seller_id": partner.id,
                        "is_without_coupons": True,
                    }
                )
