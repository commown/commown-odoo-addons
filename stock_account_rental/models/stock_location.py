from odoo import models


class StockLocation(models.Model):
    _inherit = "stock.location"

    def _is_rental_stock_location(self):
        """Return True when the location is inside our warehouse in location dedicated to
        the rental activity. This exludes customer rental locations."""
        root = self.env.ref("stock_account_rental.stock_location_rental")
        return bool(self.search([("id", "=", self.id), ("id", "child_of", root.id)]))

    def _should_be_valued(self):
        return (not self._is_rental_stock_location()) and super()._should_be_valued()
