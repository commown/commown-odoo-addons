from datetime import date

from odoo.models import ValidationError

from .common import RentalFeesTC


class RentalFeesDefinitionTC(RentalFeesTC):
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
        po2 = self.create_po_and_picking(("N/S 4", "N/S 5"))
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
            sorted(fees_def.devices().mapped("name")),
            ["N/S 1", "N/S 2", "N/S 3"],
        )

        fees_def.order_ids |= self.create_po_and_picking(("N/S 4", "N/S 5"))
        self.assertEqual(
            sorted(fees_def.devices().mapped("name")),
            ["N/S 1", "N/S 2", "N/S 3", "N/S 4", "N/S 5"],
        )

        act = fees_def.button_open_devices()
        self.assertEqual(
            sorted(self.env[act["res_model"]].search(act["domain"]).mapped("name")),
            ["N/S 1", "N/S 2", "N/S 3", "N/S 4", "N/S 5"],
        )

    def test_compensation_price(self):
        device = self.fees_def.devices().filtered(lambda d: d.name == "N/S 1")

        self.assertEqual(self.fees_def.compensation_price(device), 400.0)

        po2 = self.create_po_and_picking(("N/S 4", "N/S 5"), price_unit=150.0)
        fees_def2 = self.env["rental_fees.definition"].create(
            {
                "name": "fees_def 2",
                "partner_id": po2.partner_id.id,
                "product_template_id": self.storable_product.id,
                "order_ids": [(4, po2.id, 0)],
                "agreed_to_std_price_ratio": 0.4,
            }
        )
        device2 = fees_def2.devices().filtered(lambda d: d.name == "N/S 4")

        self.assertEqual(fees_def2.compensation_price(device2), 375.0)

    def test_to_be_compensated_device(self):
        device = self.fees_def.devices().filtered(lambda d: d.name == "N/S 1")
        task = self.env["project.task"].create(
            {
                "name": "test breakage",
                "contractual_issue_type": "breakage",
                "contractual_issue_date": date(2021, 3, 15),
                "lot_id": device.id,
            }
        )

        self.assertFalse(
            self.fees_def.to_be_compensated_devices(date(2021, 3, 1)),
        )

        self.assertDictEqual(
            self.fees_def.to_be_compensated_devices(date(2021, 8, 1)),
            {device: task},
        )
