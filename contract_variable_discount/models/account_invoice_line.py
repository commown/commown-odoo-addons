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

    def discount_relname(self, discount):
        "Helper to get the model relation name corresponding to given discount type"

        relnames = {
            "contract.template.discount.line": "applied_discount_template_line_ids",
            "contract.discount.line": "applied_discount_line_ids",
        }
        return relnames[discount._name]

    def is_discount_applied(self, discount):
        "Return whether given `discount` is one of the applied discounts of this line"

        self.ensure_one()
        relname = self.discount_relname(discount)
        return discount in getattr(self, relname)
