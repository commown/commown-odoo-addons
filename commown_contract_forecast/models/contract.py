# Copyright 2024 Commown SCIC
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.queue_job.job import identity_exact


class Contract(models.Model):

    _inherit = "contract.contract"

    @api.multi
    def action_show_contract_forecast(self):
        result = super().action_show_contract_forecast()
        result["view_mode"] = "pivot,tree,graph"
        return result

    @api.multi
    def _recurring_create_invoice(self, date_ref=False):
        "Regenerate forecasts in case conditional discounts changed since last invoice"
        invoices = super()._recurring_create_invoice(date_ref=date_ref)
        for contract in self:
            for cline in contract.contract_line_ids:
                for discount in cline._applicable_discount_lines():
                    if discount.condition:
                        cline.with_delay(
                            identity_key=identity_exact
                        ).regenerate_forecast_if_conditional_discounts_changed()
        return invoices
