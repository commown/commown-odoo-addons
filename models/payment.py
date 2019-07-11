from odoo import models, api

from .utils import dump_all_mandates, restore_all_missing_mandates


class PaymentAcquirerSlimpayDumpRestore(models.Model):
    _inherit = 'payment.acquirer'

    @api.model
    def _slimpay_dump_all_mandates(self, refresh=True,
                                   mandates_fpath='/tmp/mandates.json'):
        slimpay = self.env.ref('payment.payment_acquirer_slimpay')
        dump_all_mandates(slimpay, refresh, mandates_fpath)

    @api.model
    def _slimpay_restore_mandates(self, acquirer,
                                  mandates_fpath='/tmp/mandates.json'):
        restore_all_missing_mandates(acquirer, mandates_fpath)
