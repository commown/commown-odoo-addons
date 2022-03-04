from odoo import models, fields


class StockPicking(models.Model):
    _inherit = "stock.picking"

    contract_id = fields.Many2one('contract.contract', string='Contract')
