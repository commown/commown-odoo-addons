from odoo import models


class Contract(models.Model):
    _inherit = "contract.contract"

    def _pay_invoice(self, invoice):
        result = super()._pay_invoice(invoice)

        if result:
            invoice.transaction_ids._finalize_post_processing()

        return result
