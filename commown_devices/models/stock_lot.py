from odoo import _, fields, models


class StockLot(models.Model):
    _inherit = "stock.lot"

    contract_id = fields.Many2one("contract.contract", string="Contract")

    def name_get(self):
        result = []
        for record in self:
            _id, name = super(StockLot, record).name_get()[0]
            if record.product_id:
                name += " (%s)" % record.product_id.display_name
            result.append((record.id, name))
        return result

    def current_location(
        self,
        search_in=None,
        raise_if_not_found=False,
        raise_if_reserved=False,
    ):
        """Search if a lot if present in a stock location or its children and return the
        location"""

        quant = self.quant_ids.filtered(lambda q: q.quantity > 0)

        if search_in:
            searched_stock_locations = self.env["stock.location"].search(
                [("id", "child_of", search_in.ids)]
            )
            quant = quant.filtered(lambda q: q.location_id in searched_stock_locations)

        if raise_if_not_found and not quant:
            raise Warning(_("Lot %s not found in available stock") % self.name)

        if quant and raise_if_reserved and quant.quantity == quant.reserved_quantity:
            raise Warning(_("Lot %s is already reserved") % self.name)

        return quant.location_id
