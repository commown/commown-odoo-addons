from odoo.tests.common import SavepointCase

from ..models.common import internal_picking


class StockMoveLineTC(SavepointCase):
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
        move = internal_picking(
            [lot],
            {},
            None,
            self.stock_location,
            partner_loc,
            "origin",
        )
        move.update({"contract_id": contract.id})
        self.move_line = move.move_line_ids
        self.picking = move.picking_id

    def test_compute_is_contact_in(self):
        self.assertTrue(self.move_line.is_contract_in)
        self.move_line.location_dest_id = self.stock_location.id

        self.move_line._compute_is_contract_in()
        self.assertFalse(self.move_line.is_contract_in)

        self.move_line.move_id.contract_id = False
        self.move_line._compute_is_contract_in()
        self.assertFalse(self.move_line.is_contract_in)

    def test_compute_show_move_lines(self):
        self.assertTrue(self.move_line.show_validate_picking)

        self.picking.button_validate()

        self.env.cache.invalidate()
        self.assertFalse(self.move_line.show_validate_picking)

    def test_action_validate_linked_picking(self):
        self.assertEqual(self.picking.state, "assigned")

        self.move_line.action_validate_linked_picking()

        self.assertEqual(self.picking.state, "done")
