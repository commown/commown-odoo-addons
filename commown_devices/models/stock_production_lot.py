from odoo import models


class StockProductionLot(models.Model):
    _inherit = "stock.production.lot"

    def name_get(self):
        result = []
        for record in self:
            _id, name = super(StockProductionLot, record).name_get()[0]
            if record.product_id:
                name += ' (%s)' % record.product_id.display_name
            result.append((record.id, name))
        return result
