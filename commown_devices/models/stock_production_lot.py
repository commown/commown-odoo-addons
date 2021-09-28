from odoo import models


class StockProductionLot(models.Model):
    _inherit = "stock.production.lot"

    def name_get(self):
        result = []
        for record in self:
            _id, name = super(StockProductionLot, record).name_get()[0]
            if record.product_id:
                name += u' (%s)' % record.product_id.name
            result.append((record.id, name))
        return result
