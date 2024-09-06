import requests_mock

from odoo.exceptions import UserError

from odoo.addons.commown_shipping.tests.common import BaseShippingTC

from .common import create_lot_and_quant


class WizardProjectTaskToEmployeeTC(BaseShippingTC):
    def setUp(self):
        super().setUp()
        project = self.env["project.project"].create(
            {
                "name": "Test",
                "delivery_tracking": True,
                "shipping_account_id": self.shipping_account.id,
            }
        )
        partner = self.env["res.partner"].create(
            {
                "firstname": "Firsttest",
                "lastname": "Lasttest",
                "street": "8A rue Schertz",
                "zip": "67200",
                "city": "Strasbourg",
                "country_id": self.env.ref("base.fr").id,
                "email": "contact@commown.coop",
                "mobile": "0601020304",
                "parent_id": 1,
            }
        )

        self.task = self.env["project.task"].create(
            {"name": "test", "project_id": project.id, "partner_id": partner.id}
        )

        new_dev_loc = self.env.ref("commown_devices.stock_location_new_devices")
        self.loc = self.env["stock.location"].create(
            {"name": "new_fp", "usage": "internal", "location_id": new_dev_loc.id}
        )
        pt = self.env["product.template"].create(
            {"name": "FP3", "type": "product", "tracking": "serial"}
        )
        self.lot = create_lot_and_quant(
            self.env, "fp3_1", pt.product_variant_id, self.loc
        )

    def get_wizard(self, **kwargs):
        kwargs.setdefault("task_id", self.task.id)
        kwargs.setdefault("lot_id", self.lot.id)
        kwargs.setdefault("delivered_by_hand", False)
        kwargs.setdefault("shipping_account_id", self.shipping_account.id)
        kwargs.setdefault("parcel_type", self.parcel_type.id)
        wizard = self.env["project.task.to.employee.wizard"].create(kwargs)
        wizard.onchange_reset_shipping_data_if_delivered_by_hand()
        return wizard

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
        self.assertEqual(self.task.message_attachment_count, 0)  # pre-requisite

        with requests_mock.Mocker() as mocker:
            self.mock_colissimo_ok(mocker)
            self.get_wizard().execute()

        atts = self.env["ir.attachment"].search(
            [("res_id", "=", self.task.id), ("res_model", "=", self.task._name)]
        )
        self.assertEqual(atts.mapped("mimetype"), ["application/pdf"])
        self.assertEqual(self.task.expedition_ref, "6X0000000000")

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
            err.exception.name, "Cannot find given device. Is it really available?"
        )

    def test_error_no_partner(self):
        self.task.partner_id = False
        with self.assertRaises(UserError) as err:
            self.get_wizard().execute()

    def test_error_not_an_employee(self):
        self.task.partner_id = self.env.ref("base.partner_demo_portal").id
        with self.assertRaises(UserError) as err:
            self.get_wizard().execute()
