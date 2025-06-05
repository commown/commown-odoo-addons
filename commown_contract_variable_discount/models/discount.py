# Copyright (C) 2021 - Commown (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ContractAbstractDiscountLine(models.AbstractModel):
    _inherit = "contract.abstract.discount.line"

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
        selection_add=[("contract:commitment_end_date", "Commitment end date")],
        ondelete={"contract:commitment_end_date": "cascade"},
    )

    end_reference = fields.Selection(
        selection_add=[("contract:commitment_end_date", "Commitment end date")],
        ondelete={"contract:commitment_end_date": "cascade"},
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

        # Defensive code: this is not supposed to happen
        if not order:  # pragma no cover
            _logger.warning(
                f"Contract line id {line.id} (contract {line.contract_id.name})"
                f" has no related order line."
            )
            return False

        try:
            return self.coupon_campaign_id in order.used_coupons().mapped("campaign_id")
        except Exception:
            import traceback as tb

            _logger.exception(tb.format_exc())
            return False
