import requests_mock

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests.common import TransactionCase

from odoo.addons.commown_shipping.tests.common import mock_colissimo_ok

from .common import BaseWizardToEmployeeMixin, create_lot_and_quant


class WizardToEmployeeTC(BaseWizardToEmployeeMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.package_type = cls.env["stock.package.type"].create(
            {
                "name": "Medium parcel",
                "weight_uom_name": "kg",
                "base_weight": 1,
                "package_carrier_type": "laposte_fr",
            }
        )

        cls.task.project_id.update(
            {
                "delivery_tracking": True,
                "carrier_account_id": cls.carrier_account.id,
            }
        )

        new_dev_loc = cls.env.ref("commown_devices.stock_location_new_devices")
        cls.loc = cls.env["stock.location"].create(
            {"name": "new_fp", "usage": "internal", "location_id": new_dev_loc.id}
        )
        pt = cls.env["product.template"].create(
            {"name": "FP3", "type": "product", "tracking": "serial"}
        )
        cls.lot = create_lot_and_quant(cls.env, "fp3_1", pt.product_variant_id, cls.loc)

        # Add a line to the employee contract template, to more closely ressemble the production's template
        ct = cls.env.ref("commown_devices.contract_template_to_employee")
        ct.contract_line_ids = [Command.create({"name": "Dummy employee line"})]

    def get_wizard(self, **kwargs):
        kwargs.setdefault("lot_id", self.lot.id)
        return super().get_wizard(**kwargs)

    def test_delivered_by_hand_ok(self):
        contract = self.get_wizard(delivered_by_hand=True).execute()

        self.assertEqual(contract.lot_ids, self.lot)
        self.assertEqual(contract.partner_id, self.task.partner_id)
        self.assertEqual(self.task.lot_id, self.lot)
        self.assertEqual(self.task.contract_id, contract)
        quant = (
            self.env["stock.quant"]
            .search([("lot_id", "=", self.lot.id)])
            .filtered(lambda q: q.quantity > q.reserved_quantity)
        )
        self.assertEqual(quant.location_id.partner_id, self.task.partner_id)
        self.assertEqual(
            quant.location_id.location_id,
            self.env.ref("stock.stock_location_customers"),
        )

    def test_post_shipping_ok(self):
        self.env.ref("stock.picking_type_internal").print_label = True
        self.lot.product_id.weight = 0.8
        self.env.company.country_id = self.env.ref("base.fr").id

        self.get_wizard().execute()

        self.assertTrue(self.task.move_line_ids)
        picking = self.task.move_line_ids.picking_id
        self.assertEqual(picking.message_attachment_count, 0)  # prerequisite
        self.assertTrue(picking.carrier_required)
        self.assertFalse(picking.carrier_id)
        self.assertEqual(picking.partner_id, self.task.partner_id)
        self.assertEqual(
            picking.carrier_domain,
            '[["carrier_account_id", "=", %d]]' % self.carrier_account.id,
        )

        picking.carrier_id = self.carrier.id
        picking._put_in_pack(self.task.move_line_ids)

        with requests_mock.Mocker() as mocker:
            mock_colissimo_ok(mocker)
            picking.button_validate()

        picking._compute_message_attachment_count()
        self.assertEqual(picking.message_attachment_count, 1)

        atts = self.env["ir.attachment"].search(
            [("res_id", "=", picking.id), ("res_model", "=", picking._name)]
        )
        self.assertEqual(atts.mapped("mimetype"), ["application/pdf"])
        self.assertEqual(picking.carrier_tracking_ref, "6X0000000000")

    def test_lot_domain(self):
        wizard = self.get_wizard()
        self.assertEqual(self.lot.search(wizard._domain_lot_id()), self.lot)

        lot2 = create_lot_and_quant(self.env, "fp3_2", self.lot.product_id, self.loc)
        self.assertEqual(self.lot.search(wizard._domain_lot_id()), self.lot | lot2)

    def test_error_device_not_available(self):
        quant = self.env["stock.quant"].search([("lot_id", "=", self.lot.id)])
        self.assertEqual(len(quant), 1)  # Test pre-requisite

        quant.reserved_quantity = 1
        with self.assertRaises(UserError) as err:
            self.get_wizard().execute()
        self.assertEqual(
            err.exception.args[0], "Cannot find given device. Is it really available?"
        )

    def test_error_no_partner(self):
        self.task.partner_id = False
        with self.assertRaises(UserError):
            self.get_wizard().execute()

    def test_error_not_an_employee(self):
        self.task.partner_id = self.env.ref("base.partner_demo_portal").id
        with self.assertRaises(UserError):
            self.get_wizard().execute()
