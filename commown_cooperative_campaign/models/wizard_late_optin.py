from . import ws_utils

from odoo import models, fields, api


class LateOptinWizard(models.TransientModel):
    _name = "coupon.late.optin.wizard"

    coupon_id = fields.Many2one(
        "coupon.coupon",
        string=u"Coupon",
        required=True,
    )

    date = fields.Date(
        string=u"Optin date",
        help=u"Defaults to now",
    )

    @api.multi
    def late_optin(self):

        partner, key = self.coupon_id._action_coop_prerequisites()
        campaign = self.coupon_id.campaign_id

        base_url = ws_utils.coop_ws_base_url(self.env)

        date = fields.Date.from_string(self.date)
        ws_utils.coop_ws_optin(base_url, campaign.name, key, date, partner.tz)
