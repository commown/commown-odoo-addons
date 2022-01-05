import logging
import urllib
from datetime import datetime

import pytz
import requests
from pprint import pformat

from odoo import models, fields, api
from odoo.addons.queue_job.job import job


_logger = logging.getLogger(__file__)


def coop_ws_optout(base_url, campaign_ref, customer_key, date, tz, hour=9):
    "Query the cooperative web services to cancel a subscription"

    dt = datetime(date.year, date.month, date.day, hour=hour)
    optout_ts = pytz.timezone(tz or 'GMT').localize(dt, is_dst=True).isoformat()

    url = base_url + "/campaigns/%s/opt-out" % urllib.quote_plus(campaign_ref)

    _logger.info(
        u"Setting optout on %s in coop campaign %s, identifier %s using %s...",
        optout_ts, campaign_ref, customer_key, url)

    resp = requests.post(
        url, json={"customer_key": customer_key, "optout_ts": optout_ts})
    resp.raise_for_status()

    resp_data = resp.json()
    _logger.debug(u"Got web services response:\n %s", pformat(resp_data))


class Contract(models.Model):
    _inherit = "account.analytic.account"

    @api.multi
    @job(default_channel="root")
    def _coop_ws_optout(self, campaign, customer_key, date_end, tz):
        self.ensure_one()
        url = self.env['ir.config_parameter'].sudo().get_param(
            'commown_cooperative_campaign.base_url')
        coop_ws_optout(url, campaign.name, customer_key, date_end, tz)

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
