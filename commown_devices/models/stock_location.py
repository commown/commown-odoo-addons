from odoo import models


class StockLocation(models.Model):
    _inherit = "stock.location"

    def name_get(self):
        if not self.env.context.get("short_location_name", False):
            return super().name_get()

        ret_list = []
        for location in self:
            ret_list.append((location.id, location.name))
        return ret_list
