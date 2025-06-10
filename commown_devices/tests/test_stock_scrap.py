from datetime import datetime

from odoo.exceptions import UserError

from .common import BaseLotTC


class StockScrapTC(BaseLotTC):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.scrap_date = datetime(1111, 11, 11, 11, 11, 11, 11)
        cls.scrap = cls.env["stock.scrap"].create(
            {
                "product_id": cls.product.id,
                "lot_id": cls.lot.id,
                "location_id": cls.location_internal_available.id,
                "product_uom_id": cls.product.uom_id.id,
            }
        )

    def test_force_scrap_date(self):

        # Check prerequisite
        self.assertNotEqual(self.scrap.move_id.date, self.scrap_date)
        self.assertNotEqual(self.scrap.move_id.move_line_ids.date, self.scrap_date)

        # Check fails if scrap isn't done
        with self.assertRaises(UserError) as err:
            self.scrap.action_set_date_done_to_move_line_date()
        self.assertEqual(err.exception.args[0], "Scrap must be done to use this action")

        # Do scrap and set date done to expected
        self.scrap.action_validate()
        self.scrap.move_id.move_line_ids.date = self.scrap_date
        self.scrap.action_set_date_done_to_move_line_date()

        # Check results
        quant = self.lot.quant_ids.filtered(lambda q: q.quantity > 0)

        self.assertEqual(self.scrap.move_id.date, self.scrap_date)
        self.assertEqual(self.scrap.move_id.move_line_ids.date, self.scrap_date)
        self.assertEqual(quant.in_date, self.scrap_date)

    def test_scrap_moves_contract_association(self):
        partner = self.env.ref("base.partner_demo_portal")
        partner_loc = partner.get_or_create_customer_location("internal")

        # Change quant and scrap location to scrap lot from partner's location
        self.quant.location_id = partner_loc
        self.scrap.location_id = partner_loc

        # Associate a contract to the lot and to the scrap
        contract = self.env["contract.contract"].create(
            {"name": "TESST", "partner_id": partner.id}
        )
        self.scrap.contract_id = contract
        self.lot.contract_id = contract

        # Check association
        self.scrap.action_validate()
        self.assertEqual(self.scrap.move_id.contract_id, contract)
