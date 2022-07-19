import logging
import urllib.parse
from datetime import datetime
from pprint import pformat

import pytz
import requests

from odoo import api, models

from odoo.addons.queue_job.job import job

_logger = logging.getLogger(__file__)


def coop_ws_optout(base_url, campaign_ref, customer_key, date, tz, hour=9):
    "Query the cooperative web services to cancel a subscription"

    dt = datetime(date.year, date.month, date.day, hour=hour)
    optout_ts = pytz.timezone(tz or "GMT").localize(dt, is_dst=True).isoformat()

    url = base_url + "/campaigns/%s/opt-out" % urllib.parse.quote_plus(campaign_ref)

    _logger.info(
        "Setting optout on %s in coop campaign %s, identifier %s using %s...",
        optout_ts,
        campaign_ref,
        customer_key,
        url,
    )

    resp = requests.post(
        url, json={"customer_key": customer_key, "optout_ts": optout_ts}
    )
    resp.raise_for_status()

    resp_data = resp.json()
    _logger.debug("Got web services response:\n %s", pformat(resp_data))


class Contract(models.Model):
    _inherit = "contract.contract"

    @api.multi
    @job(default_channel="root")
    def _coop_ws_optout(self, campaign, customer_key, date_end, tz):
        self.ensure_one()
        url = self.env["ir.config_parameter"].get_param(
            "commown_cooperative_campaign.base_url"
        )
        coop_ws_optout(url, campaign.name, customer_key, date_end, tz)

    @api.multi
    def write(self, values):
        "opt-out cooperative campaign(s) if any, when the contract ends"
        res = super(Contract, self).write(values)
        if not values.get("date_end"):
            return res

        for contract in self:
            for contract_line in contract.contract_line_ids:
                for discount_line in contract_line._applicable_discount_lines():
                    campaign = discount_line.coupon_campaign_id
                    if not campaign.is_coop_campaign:
                        continue
                    _dl = discount_line.with_context(no_check_coop_ws=True)
                    if _dl.is_valid(contract_line, contract.date_end):
                        partner_id = contract.partner_id
                        key = campaign.coop_partner_identifier(partner_id)
                        if key:
                            contract.with_delay()._coop_ws_optout(
                                campaign, key, contract.date_end, partner_id.tz
                            )
        return res
