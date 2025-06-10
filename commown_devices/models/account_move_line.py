from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _compute_account_id(self):
        "Set product's rental expense account if related to a for-rental purchase"
        res = super()._compute_account_id()

        for line in self.filtered("purchase_order_id"):
            if line.purchase_order_id.is_for_rental():
                pt = line.product_id.product_tmpl_id
                line.account_id = (
                    pt.property_rental_account_expense_id
                    or pt.categ_id.property_rental_account_expense_categ_id
                )

        return res
