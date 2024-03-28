from odoo import fields, models


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    applied_discount_template_line_ids = fields.Many2many(
        comodel_name="contract.template.discount.line",
        string="Applied contract template discounts",
        readonly=True,
    )

    applied_discount_line_ids = fields.Many2many(
        comodel_name="contract.discount.line",
        string="Applied contract discounts",
        readonly=True,
    )

    def applied_discounts(self):
        self.ensure_one()
        for discount in self.applied_discount_template_line_ids:
            yield discount
        for discount in self.applied_discount_line_ids:
            yield discount
