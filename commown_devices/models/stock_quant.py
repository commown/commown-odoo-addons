from odoo import fields, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    contract_id = fields.Many2one("contract.contract", string="Contract")
