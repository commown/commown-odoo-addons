import logging
import urllib
from datetime import datetime

import pytz
import requests
from pprint import pformat

from odoo import models, fields, api

from .discount import partner_identifier


_logger = logging.getLogger(__file__)


def coop_ws_optout(base_url, campaign_ref, customer_key, date, tz, hour=9):
    "Query the cooperative web services to cancel a subscription"

    _logger.info(
        u"Setting optout on %s in coop campaign %s, identifier %s on %s...",
        date, campaign_ref, customer_key, base_url)

    dt = datetime(date.year, date.month, date.day, hour=hour)
    optout_ts = pytz.timezone(tz or 'GMT').localize(dt, is_dst=True).isoformat()

    url = base_url + "/campaign/%s/opt-out/" % urllib.quote_plus(campaign_ref)
    resp = requests.post(
        url, json={"customer_key": customer_key, "optout_ts": optout_ts})
    resp.raise_for_status()

    resp_data = resp.json()
    _logger.debug(u"Got web services response:\n %s", pformat(resp_data))


class Contract(models.Model):
    _inherit = "account.analytic.account"

    @api.onchange("date_end")
    def onchange_date_end(self):
        for contract in self:
            for contract_line in contract.recurring_invoice_line_ids:
                for discount_line in contract_line._applicable_discount_lines():
                    campaign = discount_line.coupon_campaign_id
                    if campaign.is_coop_campaign:
                        url = self.env['ir.config_parameter'].get_param(
                            'commown_cooperative_campaign.base_url')
                        partner = contract.partner_id
                        identifier = partner_identifier(partner)
                        date_end = fields.Date.from_string(contract.date_end)
                        coop_ws_optout(url, campaign.name, identifier,
                                       date_end, partner.tz)
