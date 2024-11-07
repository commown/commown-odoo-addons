from odoo import api, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    @api.multi
    def is_rental(self):
        """Return True if current location is either:

        - inside our stock and dedicated to the rental activity; in this case it is a
          child of "stock_account_rental.stock_location_rental"

        - a rental customer location; in this case it has the "internal" usage and is a
          child of stock_account_rental.stock_location_rental
        """
        self.ensure_one()

        rental_loc = self.env.ref("stock_account_rental.stock_location_rental")
        customer_loc = self.env.ref("stock.stock_location_customers")
        return bool(
            self.search(
                [
                    ("id", "=", self.id),
                    "|",
                    ("id", "child_of", rental_loc.id),
                    ("id", "child_of", customer_loc.id),
                    ("usage", "=", "internal"),
                ],
            )
        )
