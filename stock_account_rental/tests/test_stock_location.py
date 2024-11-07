from odoo.tests.common import SavepointCase


class StockLocationTC(SavepointCase):
    "Test stock.location methods"

    def test(self):
        rental_loc = self.env.ref("stock_account_rental.stock_location_rental")
        self.assertTrue(rental_loc._is_rental_stock_location())
        self.assertFalse(rental_loc._should_be_valued())

        child_rental_loc = rental_loc.create(
            {"name": "New devices", "location_id": rental_loc.id, "usage": "internal"}
        )
        self.assertTrue(child_rental_loc._is_rental_stock_location())
        self.assertFalse(child_rental_loc._should_be_valued())

        sale_loc = self.env.ref("stock.stock_location_stock")
        self.assertFalse(sale_loc._is_rental_stock_location())
        self.assertTrue(sale_loc._should_be_valued())
