from odoo import fields, models


class StockProductionLot(models.Model):
    _inherit = "stock.lot"

    device_assignment_ids = fields.One2many(
        "customer_device_manager.device_assignment",
        "device_id",
        string="Devices",
    )
