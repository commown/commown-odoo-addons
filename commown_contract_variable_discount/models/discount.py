# coding: utf-8
# Copyright (C) 2021 - Commown (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models, fields


_logger = logging.getLogger(__name__)


class ContractTemplateAbstractDiscountLine(models.AbstractModel):
    _inherit = "contract.template.abstract.discount.line"

    condition = fields.Selection(
        selection_add=[
            ("no_issue_to_date", "No contractual issue to date"),
            ("coupon_from_campaign", "Coupon from supplied campaign"),
        ],
    )

    coupon_campaign_id = fields.Many2one(
        comodel_name="coupon.campaign",
        string="Campaign",
    )

    start_reference = fields.Selection(
        selection_add=[("min_contract_end_date", "Min contract end date")]
    )

    end_reference = fields.Selection(
        selection_add=[("min_contract_end_date", "Min contract end date")]
    )

    def _compute_condition_no_issue_to_date(self, line, date):
        return not [
            t for t in line.analytic_account_id.contractual_issue_ids
            if (not t.penalty_exemption
                and fields.Date.from_string(t.contractual_issue_date) < date)
        ]

    def _compute_condition_coupon_from_campaign(self, line, date):
        try:
            coupons = line.sale_order_line_id.order_id.used_coupons()
            return self.coupon_campaign_id in coupons.mapped("campaign_id")
        except Exception as exc:
            import traceback as tb
            _logger.exception(tb.format_exc(exc))
            return False
