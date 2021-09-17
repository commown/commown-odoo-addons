from odoo import api, models


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    @api.multi
    def _prepare_invoice(self):
        " Override contract invoice creation to add auto_merge=True "
        vals = super(AccountAnalyticAccount, self)._prepare_invoice()
        vals['auto_merge'] = True
        return vals
