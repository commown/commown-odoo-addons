from datetime import date

from odoo import api, fields, models

from .discount import coop_ws_optin


class LateOptinWizard(models.TransientModel):
    _name = "coupon.late.optin.wizard"
    _description = "Helper to manually register a coupon"

    coupon_id = fields.Many2one(
        "coupon.coupon",
        string="Coupon",
        required=True,
    )

    date = fields.Date(
        string="Optin date",
        default=date.today(),
        required=True,
    )

    @api.multi
    def late_optin(self):

        partner, key = self.coupon_id._action_coop_prerequisites()
        campaign = self.coupon_id.campaign_id

        base_url = self.env["ir.config_parameter"].get_param(
            "commown_cooperative_campaign.base_url"
        )

        coop_ws_optin(
            base_url,
            campaign.name,
            key,
            self.date,
            partner.tz,
            silent_double_optin=False,
        )
