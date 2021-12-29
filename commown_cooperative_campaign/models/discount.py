# Copyright (C) 2021 - Commown (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import urllib.parse
import logging
from datetime import datetime

import pytz
import iso8601
import requests
from pprint import pformat

from odoo import models

_logger = logging.getLogger(__name__)


def parse_ws_date(str_date):
    "Return a timezone naive UTC date from given str_date"
    _date = iso8601.parse_date(str_date)
    return _date.replace(tzinfo=None) - _date.utcoffset()


def coop_ws_query(base_url, campaign_ref, customer_key, date, hour=12):
    "Query the cooperative web services to see if a subscription is active"

    _logger.info("Querying %s, campaign %s, identifier %s (date %s)",
                 base_url, campaign_ref, customer_key, date.isoformat())

    url = (base_url + "/campaigns/%s/subscriptions/important-events"
           % urllib.parse.quote_plus(campaign_ref))
    resp = requests.get(url, params={"customer_key": customer_key})
    resp.raise_for_status()

    subscriptions = resp.json()
    _logger.debug("Got web services response:\n %s", pformat(subscriptions))
    if subscriptions:
        events = {e["type"]: parse_ws_date(e["ts"])
                  for e in subscriptions[0]["events"]}
        dt = datetime(date.year, date.month, date.day, hour=hour)
        if "optin" not in events or events["optin"] >= dt:
            return False
        if "optout" in events and events["optout"] < dt:
            return False
        return True


def coop_ws_optin(base_url, campaign_ref, customer_key, date, tz, hour=9):
    "Query the cooperative web services to insert a new subscription"

    _logger.info("Optin %s: %s on %s...", campaign_ref, customer_key, date)

    dt = datetime(date.year, date.month, date.day, hour=hour)
    optin_ts = pytz.timezone(tz or 'GMT').localize(dt, is_dst=True).isoformat()

    url = base_url + "/campaigns/%s/opt-in" % urllib.parse.quote_plus(campaign_ref)
    resp = requests.post(
        url, json={"customer_key": customer_key, "optin_ts": optin_ts})
    resp.raise_for_status()

    resp_data = resp.json()
    _logger.debug("Got web services response:\n %s", pformat(resp_data))


class ContractTemplateAbstractDiscountLine(models.AbstractModel):
    _inherit = "contract.template.abstract.discount.line"

    def _compute_condition_coupon_from_campaign(self, contract_line, date):

        result = super(
                ContractTemplateAbstractDiscountLine, self
        )._compute_condition_coupon_from_campaign(contract_line, date)

        campaign = self.coupon_campaign_id
        if result and campaign.is_coop_campaign:

            contract = contract_line.analytic_account_id
            partner = contract.partner_id
            identifier = campaign.coop_partner_identifier(partner)
            if not identifier:
                _logger.warning(
                    "Couldn't build a partner identifier for a coop campaign."
                    " Partner is %s (id: %d)" % (partner.name, partner.id))
                return False

            url = self.env['ir.config_parameter'].get_param(
                'commown_cooperative_campaign.base_url')

            emitted_invoices = self.env["account.invoice"].search([
                ("contract_id", "=", contract.id),
            ])
            if len(emitted_invoices) == 1:
                # Contract start invoice: optin to the cooperative campaign
                try:
                    coop_ws_optin(url, campaign.name, identifier, date,
                                  partner.tz)
                except requests.HTTPError as exc:
                    # Try to handle double-optin nicely
                    if exc.response.status_code == 422:
                        json = exc.response.json()
                        if json.get("detail", None) == 'Already opt-in':
                            _logger.info("Double opt-in for %s (%d)"
                                         % (partner.name, partner.id))
                        else:
                            _logger.error("Opt-in error json: %s" % json)
                            raise
                    else:
                        raise

            result = coop_ws_query(url, campaign.name, identifier, date)

        return result
