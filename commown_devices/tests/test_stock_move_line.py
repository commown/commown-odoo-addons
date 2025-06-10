from odoo.tests.common import TransactionCase

from ..models.common import internal_picking
from ..models.stock_move_line import get_origin_record
from .common import create_lot_and_quant


class StockMoveLineTC(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        partner = cls.env.ref("base.partner_demo_portal")
        cls.contract = cls.env["contract.contract"].create(
            {"name": "Contract", "partner_id": partner.id}
        )
        partner_loc = partner.get_or_create_customer_location(
            cls.contract.stock_ownership
        )
        cls.stock_location = cls.env.ref("stock.stock_location_stock")
        product = cls.env["product.product"].create(
            {"name": "Test product", "type": "product", "tracking": "serial"}
        )
        lot1 = create_lot_and_quant(cls.env, "lot1", product, cls.stock_location)
        lot2 = create_lot_and_quant(cls.env, "lot2", product, cls.stock_location)

        def create_move_and_assign_contract(lot):
            move = internal_picking(
                [lot],
                {},
                None,
                cls.stock_location,
                partner_loc,
                "origin",
            )
            move.update({"contract_id": cls.contract.id})
            return move

        move1 = create_move_and_assign_contract(lot1)
        move2 = create_move_and_assign_contract(lot2)

        cls.move_line1 = move1.move_line_ids
        cls.picking1 = move1.picking_id

        cls.move_line2 = move2.move_line_ids
        cls.picking2 = move2.picking_id

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

        self.env.flush_all()
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

    def test_compute_origin(self):
        orig = "TestOrig"
        self.picking1.origin = orig
        self.move_line1._compute_origin()
        self.assertEqual(self.move_line1.origin, orig)

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
        scrap = self.env["stock.scrap"].create(
            {
                "product_id": lot.product_id.id,
                "lot_id": lot.id,
                "location_id": self.picking2.location_dest_id.id,
                "product_uom_id": lot.product_id.uom_id.id,
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

    def test_get_origin_record(self):
        po = self.env.ref("purchase.purchase_order_1")
        res = get_origin_record(self.env, po.name)
        self.assertEqual(res, po)

        task = self.env.ref("project.project_1_task_1")
        res = get_origin_record(self.env, task.get_name_for_origin())
        self.assertEqual(res, task)

        self.contract.name = "SO0001-23"
        res = get_origin_record(self.env, "SO0001-23")
        self.assertEqual(res, self.contract)

        res = get_origin_record(self.env, "Retour de %s" % self.picking1.name)
        self.assertEqual(res, self.picking1)

    def test_action_open_parent_origin(self):
        po = self.env.ref("purchase.purchase_order_1")
        self.move_line1.picking_id.origin = po.name

        expected_result = {
            "name": "Source",
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": po._name,
            "res_id": po.id,
            "target": "current",
        }
        self.assertEqual(self.move_line1.action_open_parent_origin(), expected_result)

        self.move_line1.picking_id.origin = "Unknown orig"
        self.assertFalse(self.move_line1.action_open_parent_origin())

        self.move_line1.move_id.picking_id = False
        res = self.move_line1.action_open_parent_origin()
        self.assertTrue(res is None)
