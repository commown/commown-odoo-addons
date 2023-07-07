from odoo import _, models


class StockProductionLot(models.Model):
    _inherit = "stock.production.lot"

    def name_get(self):
        result = []
        for record in self:
            _id, name = super(StockProductionLot, record).name_get()[0]
            if record.product_id:
                name += " (%s)" % record.product_id.display_name
            result.append((record.id, name))
        return result

    def current_location(
        self,
        search_in,
        raise_if_not_found=False,
        raise_if_reserved=False,
    ):
        """Search if a lot if present in a stock location or its children and return the location"""

        searched_stock_locations = self.env["stock.location"].search(
            [
                (
                    "id",
                    "child_of",
                    search_in.id,
                )
            ]
        )

        quant = self.quant_ids.filtered(lambda q: q.quantity > 0)

        if quant.location_id not in searched_stock_locations:
            raise Warning(_("Lot %s not found in available stock") % self.name)
        if quant.quantity == quant.reserved_quantity:
            raise Warning(_("Lot %s is already reserved") % self.name)

        return quant.location_id
