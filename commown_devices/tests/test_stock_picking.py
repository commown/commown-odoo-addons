import datetime

from odoo.tests.common import SavepointCase


def create_lot_and_quant(env, lot_name, product, location):
    lot = env["stock.production.lot"].create(
        {"name": lot_name, "product_id": product.id}
    )

    quant = env["stock.quant"].create(
        {
            "product_id": product.id,
            "lot_id": lot.id,
            "location_id": location.id,
            "quantity": 1,
        }
    )
    return lot


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
        partner = self.env.ref("base.res_partner_2")
        base_move_line = {"product_uom_qty": 1}
        picking = self.env["stock.picking"].create(
            {
                "move_type": "direct",
                "partner_id": partner.id,
                "picking_type_id": 5,
                "location_id": self.orig_location.id,
                "location_dest_id": self.dest_location.id,
                "date": date,
                "scheduled_date": date,
                "date_done": date,
                "move_lines": [
                    (
                        0,
                        0,
                        {
                            "product_uom_qty": 1,
                            "product_id": lot.product_id.id,
                            "name": lot.product_id.name,
                            "product_uom": lot.product_id.uom_id.id,
                            "lot_id": lot.id,
                        },
                    )
                ],
            }
        )
        return picking

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
