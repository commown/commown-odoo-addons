# Copyright (C) 2021 - Commown (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models, api

from . import ws_utils


_logger = logging.getLogger(__name__)


class ContractTemplateAbstractDiscountLine(models.AbstractModel):
    _inherit = "contract.template.abstract.discount.line"

    @api.multi
    def compute(self, contract_line, date_invoice):
        """Optin if valid and not simulating before computing the actual value

        This is because we optin at first contract invoice generation,
        i.e. when the customer receives is device. The sale could
        indeed be canceled before this date.
        """

        # Use no_check_coop_ws context to disable optin check in the
        # `is_valid` method here as the aim is... to optin!
        if (not self._context.get("is_simulation")
                and self.with_context(no_check_coop_ws=True).is_valid(
                    contract_line, date_invoice)):
            campaign = self.coupon_campaign_id
            if campaign.is_coop_campaign:
                contract = contract_line.analytic_account_id
                partner = contract.partner_id
                key = campaign.coop_partner_identifier(partner)
                if key:
                    url = ws_utils.coop_ws_base_url(self.env)
                    ws_utils.coop_ws_optin(
                        url, campaign.name, key, date_invoice, partner.tz)
                else:
                    _logger.warning(
                        u"Couldn't build a partner id for a coop campaign."
                        u" Partner is %s (id: %d)" % (partner.name, partner.id))

        return super(ContractTemplateAbstractDiscountLine, self).compute(
            contract_line, date_invoice)

    def _compute_condition_coupon_from_campaign(self, contract_line, date):

        result = super(
                ContractTemplateAbstractDiscountLine, self
        )._compute_condition_coupon_from_campaign(contract_line, date)

        if (result
                and not self._context.get("no_check_coop_ws")
                and self.coupon_campaign_id.is_coop_campaign):

            campaign = self.coupon_campaign_id
            contract = contract_line.analytic_account_id
            partner = contract.partner_id
            key = campaign.coop_partner_identifier(partner)
            if not key:
                return False

            url = ws_utils.coop_ws_base_url(self.env)

            subscriptions = ws_utils.coop_ws_important_events(
                url, campaign.name, key)
            result = subscriptions and ws_utils.coop_ws_valid_events(
                subscriptions[0]["events"], date)

        return result
