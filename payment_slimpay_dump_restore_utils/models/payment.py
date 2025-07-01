from odoo import api, models

from .utils import dump_all_mandates, restore_all_missing_mandates


class PaymentProviderSlimpayDumpRestore(models.Model):
    _inherit = "payment.provider"

    @api.model
    def _slimpay_dump_all_mandates(
        self, refresh=True, provider=None, mandates_fpath="/tmp/mandates.json", **params
    ):
        if provider is None:
            provider = self.env.ref("account_payment_slimpay.payment_provider_slimpay")
        dump_all_mandates(provider, refresh, mandates_fpath, **params)

    @api.model
    def _slimpay_restore_mandates(
        self, provider=None, mandates_fpath="/tmp/mandates.json", **params
    ):
        if provider is None:
            provider = self.env.ref("account_payment_slimpay.payment_provider_slimpay")
        restore_all_missing_mandates(provider, mandates_fpath, **params)
