from odoo import api, models
from odoo.addons.queue_job.job import job

QUEUE_CHANNEL = "root.CONTRACT_INVOICE"


class AccountAnalyticAccount(models.Model):

    _inherit = 'account.analytic.account'

    @api.multi
    @job(default_channel=QUEUE_CHANNEL)
    def recurring_create_invoice(self, limit=None):
        res = self.env["account.invoice"]
        if len(self) > 1:
            for rec in self:
                rec.with_delay().recurring_create_invoice(limit=limit)
            return res
        return super(AccountAnalyticAccount,
                     self).recurring_create_invoice(limit=limit)
