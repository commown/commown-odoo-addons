from odoo import models, fields


class StockQuant(models.Model):
    _inherit = "stock.quant"

    contract_id = fields.Many2one("contract.contract", string="Contract")
