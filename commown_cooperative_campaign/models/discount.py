# Copyright (C) 2021 - Commown (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import urllib.parse
from datetime import datetime
from pprint import pformat

import iso8601
import pytz
import requests

from odoo import _, api, models
from odoo.exceptions import UserError

from .coupon import coop_ws_subscribed

_logger = logging.getLogger(__name__)


def parse_ws_date(str_date):
    "Return a timezone naive UTC date from given str_date"
    _date = iso8601.parse_date(str_date)
    return _date.replace(tzinfo=None) - _date.utcoffset()


def coop_ws_optin(
    base_url, campaign_ref, customer_key, date, tz, hour=9, silent_double_optin=True
):
    "Query the cooperative web services to insert a new subscription"

    _logger.info("Optin %s: %s on %s...", campaign_ref, customer_key, date)

    dt = datetime(date.year, date.month, date.day, hour=hour)
    optin_ts = pytz.timezone(tz or "GMT").localize(dt, is_dst=True).isoformat()

    url = base_url + "/campaigns/%s/opt-in" % urllib.parse.quote_plus(campaign_ref)
    resp = requests.post(url, json={"customer_key": customer_key, "optin_ts": optin_ts})

    if resp.status_code == 422:
        json = resp.json()
        if json.get("detail", None) == "Already opt-in":
            _logger.info("Double opt-in for %s", customer_key)
            if silent_double_optin:
                return
            else:
                raise UserError(
                    _(
                        "Already opt-in (may not be visible"
                        " if before the campaign start)"
                    )
                )
        else:
            _logger.error("Opt-in error json: %s" % json)

    resp.raise_for_status()

    _logger.debug("Got web services response:\n %s", pformat(resp.json()))


class ContractTemplateAbstractDiscountLine(models.AbstractModel):
    _inherit = "contract.template.abstract.discount.line"

    @api.multi
    def compute(self, contract_line, date):
        """Optin if valid and not simulating before computing the actual value

        This is because we optin at first contract invoice generation,
        i.e. when the customer receives its device. The sale could
        indeed be canceled before this date.
        """

        # Use no_check_coop_ws context to disable optin check in the
        # `is_valid` method here as the aim is... to optin!
        if not self._context.get("bypass_coop_campaigns") and self.with_context(
            no_check_coop_ws=True
        ).is_valid(contract_line, date):
            campaign = self.coupon_campaign_id

            if campaign.is_coop_campaign:
                contract = contract_line.contract_id
                partner = contract.partner_id
                identifier = campaign.coop_partner_identifier(partner)

                if identifier:
                    emitted_invoices = self.env["account.invoice"].search(
                        [
                            (
                                "invoice_line_ids.contract_line_id.contract_id",
                                "=",
                                contract.id,
                            ),
                        ]
                    )
                    if len(emitted_invoices) == 0:
                        # Contract start invoice: optin to the campaign
                        url = self.env["ir.config_parameter"].get_param(
                            "commown_cooperative_campaign.base_url"
                        )
                        try:
                            coop_ws_optin(
                                url, campaign.name, identifier, date, partner.tz
                            )
                        except requests.HTTPError as exc:
                            # Try to handle double-optin nicely
                            if exc.response.status_code == 422:
                                json = exc.response.json()
                                if json.get("detail", None) == "Already opt-in":
                                    _logger.info(
                                        "Double opt-in for %s (%d)"
                                        % (partner.name, partner.id)
                                    )
                                else:
                                    _logger.error("Opt-in error json: %s" % json)
                                    raise
                            else:
                                raise

                else:
                    _logger.warning(
                        "Couldn't build a partner id for a coop campaign."
                        " Partner is %s (id: %d)" % (partner.name, partner.id)
                    )

        return super().compute(contract_line, date)

    def _compute_condition_coupon_from_campaign(self, contract_line, date):

        result = super()._compute_condition_coupon_from_campaign(contract_line, date)

        if (
            result
            and not self._context.get("no_check_coop_ws")
            and self.coupon_campaign_id.is_coop_campaign
        ):

            # Do not call the cooperative WS if we are simulating
            # future invoices...
            if not self._context.get("bypass_coop_campaigns"):
                contract = contract_line.contract_id
                partner = contract.partner_id
                campaign = self.coupon_campaign_id
                identifier = campaign.coop_partner_identifier(partner)

                if not identifier:
                    return False

                url = self.env["ir.config_parameter"].get_param(
                    "commown_cooperative_campaign.base_url"
                )

                date_time = pytz.UTC.localize(
                    datetime(date.year, date.month, date.day, 12)
                )
                result = coop_ws_subscribed(
                    url,
                    campaign.name,
                    identifier,
                    date_time=date_time,
                )[identifier]

        return result
