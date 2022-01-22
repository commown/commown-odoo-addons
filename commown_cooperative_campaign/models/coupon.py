import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError

from . import ws_utils


class Coupon(models.Model):
    _inherit = "coupon.coupon"

    @api.multi
    def action_coop_campaign_optin_status(self):
        self.ensure_one()

        campaign = self.campaign_id
        if not campaign.is_coop_campaign:
            raise UserError(_("Not a cooperative campaign!"))

        partner = self.used_for_sale_id.partner_id
        key = campaign.coop_partner_identifier(partner)

        if not key:
            raise UserError(_("Partner (%s) has no valid key.") % partner.name)

        base_url = self.env['ir.config_parameter'].get_param(
            'commown_cooperative_campaign.base_url')

        subscriptions = ws_utils.coop_ws_query(base_url, campaign.name, key)
        is_valid = ws_utils.coop_ws_valid_subscriptions(
            subscriptions, datetime.datetime.today())

        response = _("Subscription status for %(partner)s is:"
                     " %(result)s\n\n%(details)s")
        raise UserError(response % {
            "partner": partner.name,
            "result": _("subscribed") if is_valid else _("not subscribed"),
            "details": subscriptions,
        })


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

        return ws_utils.phone_to_coop_id(
            acc._get_password(), partner.country_id.code,
            partner.mobile, partner.phone)
