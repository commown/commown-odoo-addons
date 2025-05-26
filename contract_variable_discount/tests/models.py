from odoo import fields, models


class TestConditionDiscountLine(models.Model):
    _inherit = "contract.discount.line"

    condition = fields.Selection(selection_add=[("test", "Test")])

    def _compute_condition_test(self, line, date_invoice):
        "Overriden by a mock"
