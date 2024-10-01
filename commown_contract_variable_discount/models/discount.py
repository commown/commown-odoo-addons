# Copyright (C) 2021 - Commown (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import fields, models

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
        selection_add=[("contract:commitment_end_date", "Commitment end date")]
    )

    end_reference = fields.Selection(
        selection_add=[("contract:commitment_end_date", "Commitment end date")]
    )

    def is_valid(self, contract_line, date):
        if self.coupon_campaign_id.date_end and self.coupon_campaign_id.date_end < date:
            return False
        else:
            return super().is_valid(contract_line, date)

    def _compute_condition_no_issue_to_date(self, line, date):
        return not [
            t
            for t in line.contract_id.issue_ids
            if (
                t.contractual_issue_type
                and not t.penalty_exemption
                and t.contractual_issue_date < date
            )
        ]

    def _compute_condition_coupon_from_campaign(self, line, date):
        order = line.sale_order_line_id.order_id
        if not order:
            _logger.warning(
                "Contract line id {line.id} (contract {line.contract_id.name}) has no related order line.".format(
                    line=line
                )
            )
            return False

        try:
            return self.coupon_campaign_id in order.used_coupons().mapped("campaign_id")
        except:
            import traceback as tb

            _logger.exception(tb.format_exc())
            return False
