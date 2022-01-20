from odoo import models, fields, api

from .ws_utils import phone_to_coop_id


class Campaign(models.Model):
    _inherit = "coupon.campaign"

    is_coop_campaign = fields.Boolean(
        string="Cooperative campaign",
        help=("If true, the coupon-related discount condition will use the"
              " cooperative web services to check its validity."),
        index=True,
        default=False)

    @api.multi
    def coop_partner_identifier(self, partner):
        """ Returns given partner's identifier for current cooperative campaign

        ... or none if the campaign is not cooperative or the identifier cannot
        be computed.
        """
        self.ensure_one()

        if not self.is_coop_campaign:
            return None

        acc = self.env["keychain.account"].search([
            ("technical_name", "=", self.name + "-salt"),
        ]).ensure_one()

        return phone_to_coop_id(acc._get_password(), partner.country_id.code,
                                partner.mobile, partner.phone)
