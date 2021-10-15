# Copyright (C) 2021 - Commown (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import hashlib
import urllib
import logging
from datetime import datetime

import pytz
import iso8601
import phonenumbers
import requests
from pprint import pformat

from odoo import models


MOBILE_TYPE = phonenumbers.PhoneNumberType.MOBILE

_logger = logging.getLogger(__name__)


def partner_identifier(partner, campaign):
    country_code = partner.country_id.code
    if not country_code:
        raise ValueError(u"Partner '%s' has no country set" % partner.name)

    for phone_num in (partner.mobile, partner.phone):
        if phone_num:
            phone_obj = phonenumbers.parse(phone_num, country_code)
            if phonenumbers.number_type(phone_obj) == MOBILE_TYPE:
                phone = phonenumbers.format_number(
                    phone_obj, phonenumbers.PhoneNumberFormat.NATIONAL
                ).replace(' ', '')
                acc = partner.env["keychain.account"].search([
                    ("technical_name", "=", campaign.name + "-salt"),
                ]).ensure_one()
                hash = hashlib.sha256()
                hash.update(phone + acc._get_password())
                return hash.hexdigest()


def parse_ws_date(str_date):
    "Return a timezone naive UTC date from given str_date"
    _date = iso8601.parse_date(str_date)
    return _date.replace(tzinfo=None) - _date.utcoffset()


def coop_ws_query(base_url, campaign_ref, customer_key, date):
    "Query the cooperative web services to see if a subscription is active"

    _logger.info(u"Querying %s, campaign %s, identifier %s (date %s)",
                 base_url, campaign_ref, customer_key, date.isoformat())

    url = (base_url + "/campaigns/%s/subscriptions/important-events"
           % urllib.quote_plus(campaign_ref))
    resp = requests.get(url, params={"customer_key": customer_key})
    resp.raise_for_status()

    subscriptions = resp.json()
    _logger.debug(u"Got web services response:\n %s", pformat(subscriptions))
    if not subscriptions:
        raise ValueError(u"No coop campaign '%s' subscription for key '%s'"
                         % (campaign_ref, customer_key))
    else:
        events = {e["type"]: parse_ws_date(e["ts"])
                  for e in subscriptions[0]["events"]}
        dt = datetime(date.year, date.month, date.day)
        if "optin" not in events or events["optin"] > dt:
            return False
        if "optout" in events and events["optout"] <= dt:
            return False
        return True


def coop_ws_optin(base_url, campaign_ref, customer_key, date, tz, hour=9):
    "Query the cooperative web services to insert a new subscription"

    _logger.info(u"Optin %s: %s on %s...", campaign_ref, customer_key, date)

    dt = datetime(date.year, date.month, date.day, hour=hour)
    optin_ts = pytz.timezone(tz or 'GMT').localize(dt, is_dst=True).isoformat()

    url = base_url + "/campaigns/%s/opt-in" % urllib.quote_plus(campaign_ref)
    resp = requests.post(
        url, json={"customer_key": customer_key, "optin_ts": optin_ts})
    resp.raise_for_status()

    resp_data = resp.json()
    _logger.debug(u"Got web services response:\n %s", pformat(resp_data))


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
            identifier = partner_identifier(partner, campaign)
            if not identifier:
                raise ValueError(
                    u"Couldn't build a partner identifier for a coop campaign."
                    u" Partner is %s (id: %d)" % (partner.name, partner.id))

            url = self.env['ir.config_parameter'].get_param(
                'commown_cooperative_campaign.base_url')

            emitted_invoices = self.env["account.invoice"].search([
                ("contract_id", "=", contract.id),
            ])
            if len(emitted_invoices) == 1:
                # Contract start invoice: optin to the cooperative campaign
                coop_ws_optin(url, campaign.name, identifier, date, partner.tz)

            result = coop_ws_query(url, campaign.name, identifier, date)

        return result
