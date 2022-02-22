from odoo import api, models


class Contract(models.Model):
    _inherit = 'contract.contract'

    @api.multi
    def _prepare_invoice(self, *args):
        " Override contract invoice creation to add auto_merge=True "
        vals = super(Contract, self)._prepare_invoice(*args)
        vals['auto_merge'] = True
        return vals
