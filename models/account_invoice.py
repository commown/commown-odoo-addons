from odoo import models, api


class InvoiceMergeAutoPayInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.constrains('auto_merge')
    def _check_auto_merge(self):
        for inv in self:
            if not inv.payment_mode_id:
                raise models.ValidationError(
                    'Payment mode is needed to auto pay an invoice')
