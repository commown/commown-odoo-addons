from odoo import api, models


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.model
    def _get_invoice_key_cols(self):
        """Do not consider user_id as a key to merge invoices as we don't use
        the user_id and it is not significant for the matter of auto payment.
        """
        key_cols = super(AccountInvoice, self)._get_invoice_key_cols()
        try:
            key_cols.remove("user_id")
        except ValueError:
            pass
        return key_cols
