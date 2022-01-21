# Copyright (C) 2021 - Commown (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

import requests

from odoo import models

from .ws_utils import coop_ws_query, coop_ws_optin, coop_ws_valid_subscriptions


_logger = logging.getLogger(__name__)


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
                    u"Couldn't build a partner identifier for a coop campaign."
                    u" Partner is %s (id: %d)" % (partner.name, partner.id))
                return False

            url = self.env['ir.config_parameter'].get_param(
                'commown_cooperative_campaign.base_url')

            # Each contract invoice starts by optin, to allow easy joining
            # of customers when they ask
            try:
                coop_ws_optin(url, campaign.name, identifier, date,
                              partner.tz)
            except requests.HTTPError as exc:
                # Try to handle double-optin nicely
                if exc.response.status_code == 422:
                    json = exc.response.json()
                    if json.get("detail", None) == 'Already opt-in':
                        _logger.info(u"Double opt-in for %s (%d)"
                                     % (partner.name, partner.id))
                    else:
                        _logger.error(u"Opt-in error json: %s" % json)
                        raise
                else:
                    raise

            subscriptions = coop_ws_query(url, campaign.name, identifier)
            result = coop_ws_valid_subscriptions(subscriptions, date)

        return result
