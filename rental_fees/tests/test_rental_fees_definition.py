import json
from datetime import date, timedelta

from odoo.exceptions import UserError, ValidationError

from .common import RentalFeesTC


class RentalFeesDefinitionTC(RentalFeesTC):
    def test_line_order_and_name_get(self):
        self.assertEquals(
            self.fees_def.line_ids.mapped("display_name"), ["1", "2", "100"]
        )

    def test_partner_coherency_1(self):
        "Check fees partner is coherent with its orders' - update fees def"
        with self.assertRaises(ValidationError) as err:
            self.fees_def.partner_id = self.env.ref("base.res_partner_4").id

        self.assertEqual(
            err.exception.name,
            (
                "Fees definition purchase orders partners must all be"
                " the same as the fees definition's partner"
            ),
        )

    def test_partner_coherency_2(self):
        "Check fees partner is coherent with its orders' - update order"
        with self.assertRaises(ValidationError) as err:
            self.po.partner_id = self.env.ref("base.res_partner_4").id

        self.assertEqual(
            err.exception.name,
            (
                "Purchase order's partner and its fees definition"
                " must have the same partner"
            ),
        )

    def test_purchase_order_no_override(self):
        "Check fees def cannot have partner & product & po in common"
        po2 = self.create_po_and_picking(
            {self.storable_product.product_variant_id: ("N/S 4", "N/S 5")}
        )
        fees_def2 = self.env["rental_fees.definition"].create(
            {
                "name": "fees_def 2",
                "partner_id": po2.partner_id.id,
                "product_template_id": self.storable_product.id,
                "order_ids": [(4, po2.id, 0)],
                "agreed_to_std_price_ratio": 0.5,
            }
        )
        with self.assertRaises(ValidationError) as err:
            fees_def2.order_ids |= self.po

        self.assertEqual(
            err.exception.name,
            (
                "At least one other fees def, %s (id %d), has the same partner,"
                " product & order" % (self.fees_def.name, self.fees_def.id)
            ),
        )

    def test_devices(self):
        fees_def = self.fees_def
        self.assertEqual(
            sorted(d.name for d in fees_def.devices_delivery()),
            ["N/S 1", "N/S 2", "N/S 3"],
        )

        fees_def.order_ids |= self.create_po_and_picking(
            {self.storable_product.product_variant_id: ("N/S 4", "N/S 5")}
        )

        self.assertEqual(
            sorted(d.name for d in fees_def.devices_delivery()),
            ["N/S 1", "N/S 2", "N/S 3", "N/S 4", "N/S 5"],
        )

        act = fees_def.button_open_devices()
        self.assertEqual(
            sorted(self.env[act["res_model"]].search(act["domain"]).mapped("name")),
            ["N/S 1", "N/S 2", "N/S 3", "N/S 4", "N/S 5"],
        )

    def test_prices(self):
        for device in self.fees_def.devices_delivery():
            if device.name == "N/S 1":
                break

        self.assertEqual(
            self.fees_def.prices(device),
            {"standard": 500.0, "purchase": 200.0},
        )

        # Also check the error case (no invoice found for device)
        self.po.invoice_ids.action_invoice_cancel()

        with self.assertRaises(UserError) as err:
            self.fees_def.prices(device)
        self.assertEqual(
            err.exception.name,
            "No price for device N/S 1: its PO line has no invoice, see %s"
            % self.po.name,
        )

    def test_scrapped_devices(self):
        for device in self.fees_def.devices_delivery():
            if device.name == "N/S 1":
                break
        self.scrap_device(device, date(2021, 3, 15))

        self.assertFalse(
            self.fees_def.scrapped_devices(date(2021, 3, 1)),
        )

        self.assertDictEqual(
            self.fees_def.scrapped_devices(date(2021, 8, 1)),
            {device: {"date": date(2021, 3, 15)}},
        )

    def get_notifications(self, msg_level):
        name = json.dumps(getattr(self.env.user, "notify_%s_channel_name" % msg_level))
        return self.env["bus.bus"].search([("channel", "=", name)], order="id")

    def assertNewNotifs(self, msg_level, prev_notifs, *messages):
        new_notifs = self.get_notifications(msg_level) - prev_notifs
        self.assertEqual(
            {json.loads(nf.message)["message"] for nf in new_notifs},
            set(messages),
        )

    def test_action_update_with_new_pos(self):
        one_day = timedelta(days=1)

        newer_draft_po = self.po.copy({"date_order": self.po.date_order + one_day})

        newer_partial_po = self.po.copy({"date_order": self.po.date_order + one_day})
        newer_partial_po.button_confirm()
        assert len(newer_partial_po.picking_ids.move_line_ids) > 1
        mol0 = newer_partial_po.picking_ids.move_line_ids[0]
        mol0.update({"lot_name": "test-serial", "qty_done": 1})
        newer_partial_po.picking_ids.action_done()

        self.get_notifications("info")
        prev_danger = self.get_notifications("danger")
        prev_success = self.get_notifications("success")

        older_po = self.po.copy({"date_order": self.fees_def.valid_from - one_day})
        old_fees_def = self.fees_def.copy(
            {"name": "Old def", "valid_from": date(1970, 1, 1)},
        )

        (old_fees_def | self.fees_def).action_update_with_new_pos()

        self.assertIn(newer_partial_po, self.fees_def.order_ids)
        self.assertIn(newer_draft_po, self.fees_def.order_ids)
        self.assertIn(older_po, old_fees_def.order_ids)

        self.assertNewNotifs(
            "danger",
            prev_danger,
            "%s is still in an early state." % older_po.name,
            "%s is still in an early state." % newer_draft_po.name,
            "%s is not fully delivered." % newer_partial_po.name,
        )

        self.assertNewNotifs(
            "success",
            prev_success,
            (
                "Adding new POs to fees def 'Test fees_def': %s, %s"
                % (newer_draft_po.name, newer_partial_po.name)
            ),
            "Adding new POs to fees def 'Old def': %s" % older_po.name,
        )
