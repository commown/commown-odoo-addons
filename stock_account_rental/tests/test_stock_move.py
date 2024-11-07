from odoo.tests.common import SavepointCase


class StockMoveTC(SavepointCase):
    "Test stock.move methods"

    @classmethod
    def setUpClass(cls):
        super(StockMoveTC, cls).setUpClass()

        cls.product = cls.env.ref("product.product_delivery_01")
        cls.supplier_loc = cls.env.ref("stock.stock_location_suppliers")
        cls.stock_sale_loc = cls.env.ref("stock.stock_location_stock")
        cls.stock_rental_loc = cls.env.ref("stock_account_rental.stock_location_rental")

        cust_loc = cls.env.ref("stock.stock_location_customers")
        cls.cust_sale_loc = cls.env["stock.location"].create(
            {"name": "cust sale loc", "location_id": cust_loc.id, "usage": "customer"}
        )
        cls.cust_rental_loc = cls.env["stock.location"].create(
            {"name": "cust rental loc", "location_id": cust_loc.id, "usage": "internal"}
        )

    def create_move(self, orig_loc, dest_loc):
        move = self.env["stock.move"].create(
            {
                "name": "Test move",
                "location_id": orig_loc.id,
                "location_dest_id": dest_loc.id,
                "product_id": self.product.id,
                "product_uom": self.product.uom_id.id,
                "product_uom_qty": 2.0,
            }
        )
        move._action_confirm()
        move._action_assign()
        return move

    def test_is_in(self):
        _move = self.create_move

        # For sale in our stock
        self.assertTrue(_move(self.supplier_loc, self.stock_sale_loc)._is_in())

        # For rent in our stock
        self.assertFalse(_move(self.supplier_loc, self.stock_rental_loc)._is_in())

        # Dropshipping for sale
        self.assertFalse(_move(self.supplier_loc, self.cust_sale_loc)._is_in())

        # Dropshipping for rent
        self.assertFalse(_move(self.supplier_loc, self.cust_rental_loc)._is_in())
