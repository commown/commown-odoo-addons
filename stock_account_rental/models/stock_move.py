from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _is_in(self):
        """Override to avoid valuating a move from outside to a rental destination

        This is because we want to use the same product for rental or sale purposes
        so the valuation parameters are always set but must not be used when buying
        devices for rental.
        """

        for move_line in self.move_line_ids.filtered(lambda ml: not ml.owner_id):
            orig = move_line.location_id
            dest = move_line.location_dest_id
            if not orig._should_be_valued() and dest._should_be_valued():
                return not dest.is_rental()
        return False
