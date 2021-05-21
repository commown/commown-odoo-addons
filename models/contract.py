from odoo import models, fields


class Contract(models.Model):
    _inherit = "account.analytic.account"

    picking_ids = fields.One2many(
        'stock.picking',
        'contract_id',
        string=u'Pickings')
