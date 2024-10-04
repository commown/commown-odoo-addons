import datetime

from odoo.exceptions import UserError
from odoo.tests.common import SavepointCase

from ..models.common import internal_picking
from .common import create_lot_and_quant


class StockPickingTC(SavepointCase):
    def setUp(self):
        super().setUp()
        self.product_tmpl = self.env["product.template"].create(
            {
                "name": "Fairphone 3",
                "type": "product",
                "tracking": "serial",
            }
        )
        self.product = self.product_tmpl.product_variant_id
        self.orig_location = self.env["stock.location"].create(
            {
                "name": "Origin location",
                "usage": "internal",
                "partner_id": 1,
            }
        )
        self.dest_location = self.env["stock.location"].create(
            {
                "name": "Destination location",
                "usage": "internal",
                "partner_id": 1,
            }
        )

    def create_picking(self, lot, date):
        moves = internal_picking(
            lot,
            {},
            None,
            self.orig_location,
            self.dest_location,
            False,
            date,
        )
        return moves.mapped("picking_id")

    def test_compute_contract_ids(self):
        lot = create_lot_and_quant(self.env, "lot", self.product, self.orig_location)
        date = datetime.datetime.now()
        picking = self.create_picking(lot, date)

        self.assertFalse(picking.contract_ids)

        contract = self.env["contract.contract"].create(
            {"name": "contract", "partner_id": 1}
        )
        picking.move_lines.update({"contract_id": contract.id})

        self.assertEqual(picking.contract_ids, contract)

    def test_error_case_action_set_date_done_to_scheduled(self):
        lot = create_lot_and_quant(self.env, "lot", self.product, self.orig_location)
        date = datetime.datetime.now()
        picking = self.create_picking(lot, date)

        with self.assertRaises(UserError) as err:
            picking.action_set_date_done_to_scheduled()
        self.assertEqual("Transfer must be done to use this action", err.exception.name)

    def test_cron_late_pickings(self):
        lot1 = create_lot_and_quant(self.env, "lot1", self.product, self.orig_location)
        lot2 = create_lot_and_quant(self.env, "lot2", self.product, self.orig_location)

        date1 = datetime.datetime.now()
        date2 = datetime.datetime.now() - datetime.timedelta(days=25)
        picking1 = self.create_picking(lot1, date1)
        picking2 = self.create_picking(lot2, date1)
        picking1.action_assign()
        picking2.action_assign()
        channel = self.env.ref("commown_devices.late_pickings_with_lots_channel")
        self.env["stock.picking"]._cron_count_late_lot_pickings()
        self.assertFalse(channel.message_ids)

        picking2.scheduled_date = date2
        self.env["stock.picking"]._cron_count_late_lot_pickings()

        expected_message = "<p>%s late pickings</p>" % 1
        self.assertEqual(len(channel.message_ids), 1)
        self.assertEqual(channel.message_ids.body, expected_message)
