from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    property_rental_account_expense_categ_id = fields.Many2one(
        "account.account",
        company_dependent=True,
        string="Expense Account (rental)",
        domain=[("deprecated", "=", False)],
    )
