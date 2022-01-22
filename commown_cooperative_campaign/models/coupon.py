import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError

from . import ws_utils


class Coupon(models.Model):
    _inherit = "coupon.coupon"

    def _action_coop_prerequisites(self):
        self.ensure_one()

        campaign = self.campaign_id
        if not campaign.is_coop_campaign:
            raise UserError(_("Not a cooperative campaign!"))

        partner = self.used_for_sale_id.partner_id
        key = campaign.coop_partner_identifier(partner)

        if not key:
            raise UserError(_("Partner (%s) has no valid key.") % partner.name)
        return partner, key

    @api.multi
    def action_coop_campaign_optin_status(self):
        partner, key = self._action_coop_prerequisites()
        campaign = self.campaign_id
        base_url = ws_utils.coop_ws_base_url(self.env)

        response = [_("Subscription status for %(partner)s is: %(result)s")]
        ctx = {"partner": partner.name}

        subscriptions = ws_utils.coop_ws_query(base_url, campaign.name, key)
        is_valid = ws_utils.coop_ws_valid_subscriptions(
            subscriptions, datetime.datetime.today())

        if is_valid:
            response.append(u"%(details)s")
            lang = self.env["res.lang"].search([("code", "=", self.env.lang)])
            ctx.update({
                "details": ws_utils.coop_human_readable_subscriptions(
                    subscriptions, lang.date_format + " " + lang.time_format),
                "result": _("subscribed"),
            })

        else:
            response.append(_("Key: %(key)s"))
            ctx.update({
                "key": key,
                "result": _("subscribed"),
            })

        raise UserError(u"\n--\n".join(response) % ctx)

    @api.multi
    def action_coop_campaign_optin_now(self):
        partner, key = self._action_coop_prerequisites()
        campaign = self.campaign_id
        base_url = ws_utils.coop_ws_base_url(self.env)

        date = datetime.datetime.today()
        ws_utils.coop_ws_optin(base_url, campaign.name, key, date, partner.tz)
        raise UserError(_("Single-side manual optin ok"))


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
