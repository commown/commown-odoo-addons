from odoo.exceptions import UserError
from odoo.tests.common import SavepointCase

from ..models.common import internal_picking
from .common import create_lot_and_quant


class StockMoveTC(SavepointCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env.ref("base.partner_demo_portal")
        self.contract = self.env["contract.contract"].create(
            {"name": "Contract", "partner_id": self.partner.id}
        )
        self.stock_location = self.env.ref("stock.stock_location_stock")
        product = self.env["product.product"].create(
            {"name": "Test product", "type": "product", "tracking": "serial"}
        )
        self.lot1 = create_lot_and_quant(self.env, "lot1", product, self.stock_location)
        self.lot2 = create_lot_and_quant(self.env, "lot2", product, self.stock_location)

    def move_to(self, destination, orig_location=None, lots=None, contract=None):
        moves = internal_picking(
            lots or [self.lot1, self.lot2],
            {},
            None,
            orig_location or self.stock_location,
            destination,
            "origin",
        )
        moves.update({"contract_id": contract or self.contract.id})
        return moves

    def test_update_lot_contract_no_partner_loc(self):
        "Check error when partner doesn't have a location"
        moves = self.move_to(self.stock_location)

        expected_message = (
            "No contract location for contract (id: %s)" % self.contract.id
        )
        with self.assertRaises(UserError) as error:
            moves.update_lot_contract()
        self.assertEqual(
            error.exception.name,
            expected_message,
        )
        # Check same error is logged depending on context
        chan = "odoo.addons.commown_devices.models.stock_move"
        with self.assertLogs(chan, level="WARNING") as cm:
            moves.with_context(
                no_raise_in_update_lot_contract=True
            ).update_lot_contract()
        self.assertEqual("ERROR:%s:%s" % (chan, expected_message), cm.output[0])

    def test_update_lot_location_move_contract_consistency(self):
        self.partner.get_or_create_customer_location()
        moves = self.move_to(self.stock_location)

        # Check error when the move and contract location are inconsistent
        with self.assertRaises(UserError) as error2:
            moves.update_lot_contract()
        expected_message = (
            "Inconsistent locations between move (id: %s, picking"
            " id: %s) and contract (id: %s)"
        ) % (moves[0].id, moves[0].picking_id.id, moves[0].contract_id.id)
        self.assertEqual(
            error2.exception.name,
            expected_message,
        )

    def test_update_lot_contract_multiple_contract(self):
        "Test warning if move line's lots are linked to several contracts"
        partner_loc = self.partner.get_or_create_customer_location()

        contract2 = self.contract.copy({"name": "Contract 2"})

        p1 = self.move_to(partner_loc, lots=self.lot1).picking_id
        p2 = self.move_to(partner_loc, lots=self.lot2, contract=contract2).picking_id
        p1.button_validate()
        p2.button_validate()

        return_moves = self.move_to(self.stock_location, orig_location=partner_loc)
        return_moves[1].move_line_ids.move_id = return_moves[0].id

        with self.assertLogs(
            "odoo.addons.commown_devices.models.stock_move", level="WARNING"
        ) as cm2:
            with self.assertRaises(UserError) as error3:
                return_moves.update_lot_contract()

        expected_log = (
            "WARNING:odoo.addons.commown_devices.models.stock_move:More than one contract on move %s lots"
            % return_moves[0].id
        )
        expected_error = (
            "Inconsistent move (id: %s, picking id:"
            " %s) contract (id: %s) and lot"
            " contract (id: %s)"
        ) % (
            return_moves[0].id,
            return_moves[0].picking_id.id,
            return_moves[0].contract_id.id,
            return_moves.mapped("move_line_ids.lot_id.contract_id").ids,
        )

        self.assertEqual(
            error3.exception.name,
            expected_error,
        )
        self.assertEqual(expected_log, cm2.output[0])
