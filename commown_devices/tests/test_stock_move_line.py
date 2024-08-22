from odoo.tests.common import SavepointCase

from ..models.common import internal_picking
from .common import create_lot_and_quant


class StockMoveLineTC(SavepointCase):
    def setUp(self):
        super().setUp()
        partner = self.env.ref("base.partner_demo_portal")
        self.contract = self.env["contract.contract"].create(
            {"name": "Contract", "partner_id": partner.id}
        )
        partner_loc = partner.get_or_create_customer_location()
        self.stock_location = self.env.ref("stock.stock_location_stock")
        product = self.env["product.product"].create(
            {"name": "Test product", "type": "product", "tracking": "serial"}
        )
        lot1 = create_lot_and_quant(self.env, "lot1", product, self.stock_location)
        lot2 = create_lot_and_quant(self.env, "lot2", product, self.stock_location)

        def create_move_and_assign_contract(lot):
            move = internal_picking(
                [lot],
                {},
                None,
                self.stock_location,
                partner_loc,
                "origin",
            )
            move.update({"contract_id": self.contract.id})
            return move

        move1 = create_move_and_assign_contract(lot1)
        move2 = create_move_and_assign_contract(lot2)

        self.move_line1 = move1.move_line_ids
        self.picking1 = move1.picking_id

        self.move_line2 = move2.move_line_ids
        self.picking2 = move2.picking_id

    def test_compute_is_contact_in(self):
        self.assertTrue(self.move_line1.is_contract_in)
        self.move_line1.location_dest_id = self.stock_location.id

        self.move_line1._compute_is_contract_in()
        self.assertFalse(self.move_line1.is_contract_in)

        self.move_line1.move_id.contract_id = False
        self.move_line1._compute_is_contract_in()
        self.assertFalse(self.move_line1.is_contract_in)

    def test_compute_show_move_lines(self):
        self.assertTrue(self.move_line1.show_validate_picking)

        self.picking1.button_validate()

        self.env.cache.invalidate()
        self.assertFalse(self.move_line1.show_validate_picking)

    def test_action_validate_linked_picking(self):
        assigned_move_lines = self.contract.move_line_ids.filtered(
            lambda ml: ml.state == "assigned"
        )
        self.assertEqual(len(assigned_move_lines), 2)
        self.assertEqual(self.picking1.state, "assigned")

        # When there is more than one unvalidated move we expect a wizard
        expected_resp = {
            "type": "ir.actions.act_window",
            "name": "Message",
            "res_model": "move.line.validation.wizard",
            "view_type": "form",
            "view_mode": "form",
            "target": "new",
            "context": {"default_move_line_id": self.move_line1.id},
        }
        resp = self.move_line1.action_validate_linked_picking()
        self.assertEqual(resp, expected_resp)

        self.picking1.button_validate()

        assigned_move_lines = self.contract.move_line_ids.filtered(
            lambda ml: ml.state == "assigned"
        )
        self.assertEqual(len(assigned_move_lines), 1)
        # When only obe unvalidated move, the picking is validated directly
        self.move_line2.action_validate_linked_picking()
        self.assertEqual(self.picking2.state, "done")

    def test_action_open_parent(self):
        # Check result on picking move line
        expected_result = {
            "name": "Source",
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "stock.picking",
            "res_id": self.picking1.id,
            "target": "current",
        }
        self.assertEqual(self.move_line1.action_open_parent(), expected_result)

        # Create scrap
        self.picking2.button_validate()
        lot = self.move_line2.lot_id
        scrap_loc = self.env.ref("stock.stock_location_scrapped")
        scrap = self.env["stock.scrap"].create(
            {
                "product_id": lot.product_id.id,
                "lot_id": lot.id,
                "location_id": self.picking2.location_dest_id.id,
                "scrap_location_id": scrap_loc.id,
                "product_uom_id": lot.product_id.uom_id.id,
                "date_expected": self.picking2.date_done,
            }
        )
        scrap.action_validate()
        scrap_move_line = scrap.move_id.move_line_ids

        # Check result on a scrap
        expected_result = {
            "name": "Source",
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "stock.scrap",
            "res_id": scrap.id,
            "target": "current",
        }
        self.assertEqual(scrap_move_line.action_open_parent(), expected_result)

        self.move_line1.move_id.picking_id = False
        res = self.move_line1.action_open_parent()
        self.assertTrue(res is None)
