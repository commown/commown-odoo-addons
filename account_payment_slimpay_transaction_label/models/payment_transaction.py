from odoo import models


class SlimpayTransaction(models.Model):
    _inherit = "payment.transaction"

    def _label(self):
        """
        If a `payment_transaction_label` value (assigned in contract_transaction_label)
        is present in the context, use it as the invoice label.
        Otherwise, use the default behavior declared in account_payment_slimpay.
        """
        context = self.env.context
        if "payment_transaction_label" in context:
            return context["payment_transaction_label"]
        else:
            return super()._label()
