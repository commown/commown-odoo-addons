from odoo.tests.common import SavepointCase

from ..models.common import internal_picking


class StockMoveTC(SavepointCase):
    def setUp(self):
        super().setUp()
        partner = self.env.ref("base.partner_demo_portal")
        contract = self.env["contract.contract"].create(
            {"name": "Contract", "partner_id": partner.id}
        )
        partner_loc = partner.get_or_create_customer_location()
        self.stock_location = self.env.ref("stock.stock_location_stock")
        product = self.env["product.product"].create(
            {"name": "Test product", "type": "product", "tracking": "serial"}
        )
        lot = self.env["stock.production.lot"].create(
            {"name": "FP Lot", "product_id": product.id}
        )
        quants = self.env["stock.quant"].create(
            [
                {
                    "product_id": product.id,
                    "lot_id": lot.id,
                    "location_id": self.stock_location.id,
                    "quantity": 1,
                }
            ]
        )
        self.moves = internal_picking(
            [lot],
            {},
            None,
            self.stock_location,
            partner_loc,
            "origin",
        )
        self.moves.update({"contract_id": contract.id})

    def test_compute_is_contact_in(self):
        ml = self.moves.move_line_ids

        self.assertTrue(ml.is_contract_in)
        ml.location_dest_id = self.stock_location.id

        ml._compute_is_contract_in()
        self.assertFalse(ml.is_contract_in)

        ml.move_id.contract_id = False
        ml._compute_is_contract_in()
        self.assertFalse(ml.is_contract_in)
