from datetime import datetime

from odoo.exceptions import UserError

from .test_stock_production_lot import StockProductionLotTC


class StockScrapTC(StockProductionLotTC):
    def test_force_scrap_date(self):
        date = datetime(1111, 11, 11, 11, 11, 11, 11)
        scrap_loc = self.env.ref("stock.stock_location_scrapped")
        scrap = self.env["stock.scrap"].create(
            {
                "product_id": self.product.id,
                "lot_id": self.lot.id,
                "location_id": self.location_internal_available.id,
                "scrap_location_id": scrap_loc.id,
                "product_uom_id": self.product.uom_id.id,
                "date_expected": date,
            }
        )

        # Check prerequisite
        self.assertNotEqual(scrap.move_id.date, date)
        self.assertNotEqual(scrap.move_id.move_line_ids.date, date)

        # Check fails if scrap isn't done
        with self.assertRaises(UserError) as err:
            scrap.action_set_date_done_to_expected()
        self.assertEqual(err.exception.name, "Scrap must be done to use this action")

        # Do scrap and set date done to expected
        scrap.action_validate()
        scrap.action_set_date_done_to_expected()

        # Check results
        quant = self.lot.quant_ids.filtered(lambda q: q.quantity > 0)

        self.assertEqual(scrap.move_id.date, date)
        self.assertEqual(scrap.move_id.move_line_ids.date, date)
        self.assertEqual(quant.in_date, date)
