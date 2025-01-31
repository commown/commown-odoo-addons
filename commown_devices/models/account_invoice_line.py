from odoo import models


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    def get_invoice_line_account(self, type, product, fpos, company):
        "Return product's rental expense account if related to a for-rental purchase"

        po_line_id = self._context.get("purchase_line_id", False)
        if po_line_id:
            order = self.env["purchase.order.line"].browse(po_line_id).order_id
            if order.is_for_rental():
                pt = product.product_tmpl_id
                return (
                    pt.property_rental_account_expense_id
                    or pt.categ_id.property_rental_account_expense_categ_id
                )

        return super().get_invoice_line_account(type, product, fpos, company)
