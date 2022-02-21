from .common import DeviceAsAServiceTC


class ProjectTaskPickingTC(DeviceAsAServiceTC):

    def setUp(self):
        super().setUp()

        self.project = self.env["project.project"].create({"name": "Test"})

        self.partner2 = self.so.partner_id.copy({"name": "test partner2"})
        self.so2 = self.so.copy({"partner_id": self.partner2.id})
        self.so2.action_confirm()

        self.storable_product2 = self.storable_product.copy({"name": "Core-X4"})
        cc = self.storable_product2.product_variant_ids

        contract_model = self.env["contract.contract"]
        self.c1, self.c2, self.c3 = contract_model.of_sale(self.so)

        self._create_and_send_device("fp1", self.c1)
        self._create_and_send_device("fp2", self.c2)
        self._create_and_send_device("fp3", self.c3)
        self._create_and_send_device("fp4", None)
        self._create_and_send_device("cc1", self.c1, cc)
        self._create_and_send_device("cc2", None)
        self._create_and_send_device("cc3", self.c3, cc, do_transfer=False)

        # Create a unused product
        self.storable_product.copy({"name": "unused product"})


    def _create_and_send_device(self, serial, contract, product=None,
                                do_transfer=True):
        lot = self.adjust_stock(product, serial=serial)
        if contract is not None:
            quant = lot.quant_ids.filtered(lambda q: q.quantity > 0)
            contract.send_device(quant.ensure_one(), do_transfer=do_transfer)

    def get_ui(self, **user_choices):
        return self.prepare_ui("project.task", self.project, "project_id",
                               user_choices=user_choices)

    def test_ui_help_desk(self):
        self.project.update({"device_tracking": True, "require_contract": True})

        partner = self.so.partner_id
        product1 = self.storable_product.product_variant_ids[0]
        product2 = self.storable_product2.product_variant_ids[0]

        # Set partner only
        values, choices = self.get_ui(
            partner_id=partner.id,
            commercial_partner_id=partner.commercial_partner_id.id)

        # > check values
        self.assertEqual(values.get("project_id"), self.project.id)
        self.assertEqual(values.get("partner_id"), partner.id)
        self.assertFalse(values.get("storable_product_id"))
        self.assertFalse(values.get("contract_id"))
        self.assertFalse(values.get("lot_id"))

        # > check domains
        self.assertEqual(choices["contract_id"], self.c1 | self.c2 | self.c3)
        self.assertEqual(choices["storable_product_id"], product1 | product2)
        lot_names = set(choices["lot_id"].mapped("name"))
        self.assertEqual(lot_names, {"fp1", "fp2", "fp3", "cc1", "cc3"})

        # Set contract only (contract 1: two device choice)
        values, choices = self.get_ui(contract_id=self.c1.id)

        # > check values
        self.assertEqual(values.get("project_id"), self.project.id)
        self.assertEqual(values.get("partner_id"), partner.id)
        self.assertEqual(values.get("contract_id"), self.c1.id)
        self.assertFalse(values.get("storable_product_id"))
        self.assertFalse(values.get("lot_id"))

        # > check domains
        self.assertTrue(len(choices["partner_id"]) > 1)  # no contract filtering
        self.assertEqual(choices["contract_id"], self.c1 | self.c2 | self.c3)
        self.assertEqual(choices["storable_product_id"], product1 | product2)
        self.assertEqual(set(choices["lot_id"].mapped("name")), {"fp1", "cc1"})

        # Set contract only (contract 2: single device choice)
        values, choices = self.get_ui(contract_id=self.c2.id)

        # > check values
        self.assertEqual(values.get("storable_product_id"), product1.id)
        ui_lots = self.env["stock.production.lot"].browse(values["lot_id"])
        self.assertEqual(ui_lots.mapped("name"), ["fp2"])

        # Set lot_id only
        lot = self.env["stock.production.lot"].search([("name", "=", "cc1")])
        values, choices = self.get_ui(lot_id=lot.id)

        # > check values
        self.assertEqual(values.get("project_id"), self.project.id)
        self.assertEqual(values.get("partner_id"), partner.id)
        self.assertEqual(values.get("contract_id"), self.c1.id)
        self.assertEqual(values.get("storable_product_id"), product2.id)
        self.assertEqual(values.get("lot_id"), lot.id)

        # > check domains
        self.assertTrue(len(choices["partner_id"]) > 1)
        self.assertEqual(choices["contract_id"], self.c1 | self.c2 | self.c3)
        self.assertEqual(choices["storable_product_id"], product1 | product2)
        self.assertEqual(choices["lot_id"].mapped("name"), ["cc1"])

    def test_ui_repair(self):
        self.project.update({"device_tracking": True, "require_contract": False})

        product = self.storable_product.product_variant_ids[0]
        product2 = self.storable_product2.product_variant_ids[0]

        # Set product only
        values, choices = self.get_ui(storable_product_id=product.id)

        # > check values
        self.assertEqual(values.get("project_id"), self.project.id)
        self.assertFalse(values.get("partner_id"))
        self.assertEqual(values.get("storable_product_id"), product.id)
        self.assertFalse(values.get("contract_id"))
        self.assertFalse(values.get("lot_id"))

        # > check domains
        self.assertEqual(set(choices["storable_product_id"].mapped("name")),
                         {'Core-X4', 'Fairphone 3', 'unused product'})
        lot_names = set(choices["lot_id"].mapped("name"))
        self.assertEqual(lot_names, {"fp4", "cc2"})

        # Set lot_id only
        lot = self.env["stock.production.lot"].search([("name", "=", "cc2")])
        values, choices = self.get_ui(lot_id=lot.id)

        # > check values
        self.assertEqual(values.get("project_id"), self.project.id)
        self.assertFalse(values.get("partner_id"))
        self.assertFalse(values.get("contract_id"))
        self.assertEqual(values.get("storable_product_id"), lot.product_id.id)
        self.assertEqual(values.get("lot_id"), lot.id)

        # > check domains
        self.assertEqual(set(choices["storable_product_id"].mapped("name")),
                         {'Core-X4', 'Fairphone 3', 'unused product'})
        lot_names = set(choices["lot_id"].mapped("name"))
        self.assertEqual(lot_names, {"fp4", "cc2"})
