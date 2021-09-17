# coding: utf-8
# Copyright (C) 2021 - Commown (https://commown.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class ContractTemplateAbstractDiscountLine(models.AbstractModel):
    _inherit = "contract.template.abstract.discount.line"

    condition = fields.Selection(
        selection_add=[("no_issue_to_date", "No contractual issue to date")],
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
