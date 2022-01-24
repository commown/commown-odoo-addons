import logging

from odoo import models, fields, api
from odoo.addons.queue_job.job import job

from . import ws_utils


_logger = logging.getLogger(__file__)


class Contract(models.Model):
    _inherit = "account.analytic.account"

    @api.multi
    @job(default_channel="root")
    def _coop_ws_optout(self, campaign, customer_key, date_end, tz):
        self.ensure_one()
        url = ws_utils.coop_ws_base_url(self.env)
        ws_utils.coop_ws_optout(url, campaign.name, customer_key, date_end, tz)

    @api.multi
    def write(self, values):
        "opt-out cooperative campaign(s) if any, when the contract ends"
        res = super(Contract, self).write(values)
        if "date_end" not in values:
            return res
        for contract in self:
            for contract_line in contract.recurring_invoice_line_ids:
                for discount_line in contract_line._applicable_discount_lines():
                    campaign = discount_line.coupon_campaign_id
                    if campaign.is_coop_campaign:
                        partner_id = contract.partner_id
                        key = campaign.coop_partner_identifier(partner_id)
                        if key:
                            date_end = fields.Date.from_string(
                                contract.date_end or "2100-01-01")
                            contract.with_delay()._coop_ws_optout(
                                campaign, key, date_end, partner_id.tz)
        return res
