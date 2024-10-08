from datetime import datetime

from odoo.exceptions import UserError

from .common import BaseLotTC


class StockScrapTC(BaseLotTC):
    def setUp(self):
        super().setUp()
        self.scrap_date = datetime(1111, 11, 11, 11, 11, 11, 11)
        scrap_loc = self.env.ref("stock.stock_location_scrapped")
        self.scrap = self.env["stock.scrap"].create(
            {
                "product_id": self.product.id,
                "lot_id": self.lot.id,
                "location_id": self.location_internal_available.id,
                "scrap_location_id": scrap_loc.id,
                "product_uom_id": self.product.uom_id.id,
                "date_expected": self.scrap_date,
            }
        )

    def test_force_scrap_date(self):

        # Check prerequisite
        self.assertNotEqual(self.scrap.move_id.date, self.scrap_date)
        self.assertNotEqual(self.scrap.move_id.move_line_ids.date, self.scrap_date)

        # Check fails if scrap isn't done
        with self.assertRaises(UserError) as err:
            self.scrap.action_set_date_done_to_expected()
        self.assertEqual(err.exception.name, "Scrap must be done to use this action")

        # Do scrap and set date done to expected
        self.scrap.action_validate()
        self.scrap.action_set_date_done_to_expected()

        # Check results
        quant = self.lot.quant_ids.filtered(lambda q: q.quantity > 0)

        self.assertEqual(self.scrap.move_id.date, self.scrap_date)
        self.assertEqual(self.scrap.move_id.move_line_ids.date, self.scrap_date)
        self.assertEqual(quant.in_date, self.scrap_date)
