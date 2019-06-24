from odoo import models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def _prepare_invoice(self):
        """We do not want the sale order note to be copied to the invoice
        comment (pre-sale notes do generally not apply to invoices).
        We want to be able to add an invoice note (the "comment"
        attribute) however, so we do not remove it from the report but
        rather suppress the sale > invoice copy.
        """
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.pop('comment', None)
        return invoice_vals
