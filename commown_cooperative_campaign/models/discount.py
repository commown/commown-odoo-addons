# Copyright (C) 2021 - Commown (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models

from . import ws_utils


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
            key = campaign.coop_partner_identifier(partner)
            if not key:
                _logger.warning(
                    u"Couldn't build a partner identifier for a coop campaign."
                    u" Partner is %s (id: %d)" % (partner.name, partner.id))
                return False

            # Do not call the cooperative WS if we are simulating
            # future invoices...
            if self._context.get("is_simulation"):
                return True

            url = ws_utils.coop_ws_base_url(self.env)

            # Each contract invoice starts by optin, to allow easy joining
            # of customers when they ask
            ws_utils.coop_ws_optin(
                url, campaign.name, key, date, partner.tz)
            subscriptions = ws_utils.coop_ws_important_events(
                url, campaign.name, key)
            result = subscriptions and ws_utils.coop_ws_valid_events(
                subscriptions[0]["events"], date)

        return result
