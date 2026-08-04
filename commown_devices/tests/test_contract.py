from datetime import datetime

from odoo.exceptions import UserError

from .common import DeviceAsAServiceTC, add_attributes_to_product, create_config


class ContractTC(DeviceAsAServiceTC):
    def test_cant_send_ungraded_lot(self):
        contract = self.env["contract.contract"].of_sale(self.so)[0]
        lot = self.adjust_stock(grade_lot=False)
        with self.assertRaises(UserError) as err:
            contract.send_devices(lot, {})
        self.assertIn("Please set the grade on lots", err.exception.args[0])

    def test_compute_lot_number(self):
        contract = self.env["contract.contract"].of_sale(self.so)[0]
        init_lot_nb = contract.lot_nb

        lot = self.adjust_stock()
        contract.lot_ids |= lot
        self.assertEqual(contract.lot_nb, init_lot_nb + 1)

        contract.lot_ids = False
        self.assertEqual(contract.lot_nb, init_lot_nb)

    def test_partner_location_changed(self):
        contract = self.env["contract.contract"].of_sale(self.so)[0]
        partner = contract.partner_id
        lot = self.adjust_stock()
        scheduled_date = datetime.strptime("2003-03-03", "%Y-%m-%d")

        send_pick = contract.send_devices(lot, {}).picking_id
        send_pick.scheduled_date = scheduled_date
        send_pick.button_validate()

        receive_loc = self.env.ref("commown_devices.stock_location_devices_to_check")
        return_pick = contract.receive_devices(lot, {}, receive_loc).picking_id
        return_pick.scheduled_date = scheduled_date

        old_part_loc = partner.get_customer_locations(usage="internal")

        contract._partner_location_changed()
        self.assertEqual(send_pick.location_dest_id, old_part_loc)
        self.assertEqual(return_pick.location_id, old_part_loc)

        old_part_loc.partner_id = False
        new_part_loc = partner.get_or_create_customer_location(contract.stock_ownership)
        self.assertNotEqual(old_part_loc, new_part_loc)
        contract._partner_location_changed(old_part_loc)
        self.assertEqual(send_pick.location_dest_id, new_part_loc)
        self.assertEqual(return_pick.location_id, new_part_loc)

        self.assertEqual(send_pick.date_done, scheduled_date)
        self.assertNotEqual(return_pick.date_done, scheduled_date)


class ContractMainRentalProductTC(DeviceAsAServiceTC):
    "Test class checking the assignment of the contract.contract.main_rental_product field"

    confirm_sale = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.so2 = cls.so.copy()

        cls.ct = cls._create_rental_contract_tmpl(
            1, contract_line_ids=[cls._contract_line(1, "1 month ##PRODUCT##")]
        )

        cls.attribute_cpu = cls.env.ref("product_rental.attr_cpu")
        cls.cpu_i5 = cls.env.ref("product_rental.val_cpu_i5")
        cls.cpu_i7 = cls.env.ref("product_rental.val_cpu_i7")

        cls.pc_service_tmpl = cls._create_rental_product(
            "PC",
            list_price=130.0,
            recurrent_payment_amount=65.0,
            property_contract_template_id=cls.ct.id,
        ).product_tmpl_id

        add_attributes_to_product(
            cls.pc_service_tmpl,
            cls.attribute_cpu,
            cls.cpu_i5 + cls.cpu_i7,
        )

        cls.pc_service_i5 = cls.env["product.product"].search(
            [
                ("product_tmpl_id", "=", cls.pc_service_tmpl.id),
                (
                    "product_template_variant_value_ids.product_attribute_value_id",
                    "=",
                    cls.cpu_i5.id,
                ),
            ]
        )
        cls.pc_service_i7 = cls.env["product.product"].search(
            [
                ("product_tmpl_id", "=", cls.pc_service_tmpl.id),
                (
                    "product_template_variant_value_ids.product_attribute_value_id",
                    "=",
                    cls.cpu_i7.id,
                ),
            ]
        )

        cls.pc_storable_tmpl_i5 = cls.storable_product.copy({"name": "PC-i5"})
        cls.pc_storable_tmpl_i7 = cls.storable_product.copy({"name": "PC-i7"})
        cls.pc_storable_tmpl_generic = cls.storable_product.copy({"name": "PC-generic"})

        cls.pc_storable_i5 = cls.pc_storable_tmpl_i5.product_variant_id
        cls.pc_storable_i7 = cls.pc_storable_tmpl_i7.product_variant_id
        cls.pc_storable_generic = cls.pc_storable_tmpl_generic.product_variant_id

    def _set_order_product_and_confirm(self, so, product):
        "Returns the generated contract"
        so.order_line.write(
            {
                "product_id": product.id,
                "product_uom_qty": 1.0,
            }
        )
        so.action_confirm()

        contract = self.env["contract.contract"].of_sale(so)
        contract.ensure_one()
        return contract

    def test_main_rental_product_compute_ok_variant(self):
        "A configuration with the exact same attributes should be picked"
        create_config(
            self.pc_service_tmpl,
            "primary",
            self.pc_storable_tmpl_i5,
            self.pc_storable_i5,
            att_val_ids=self.cpu_i5,
        )

        create_config(
            self.pc_service_tmpl,
            "primary",
            self.pc_storable_tmpl_i7,
            self.pc_storable_i7,
            att_val_ids=self.cpu_i7,
        )

        contract_1 = self._set_order_product_and_confirm(self.so, self.pc_service_i5)
        self.assertEqual(contract_1.main_rental_product, self.pc_storable_i5)

        contract_2 = self._set_order_product_and_confirm(self.so2, self.pc_service_i7)
        self.assertEqual(contract_2.main_rental_product, self.pc_storable_i7)

    def test_main_rental_product_compute_ok_generic(self):
        create_config(
            self.pc_service_tmpl,
            "primary",
            self.pc_storable_tmpl_generic,
            self.pc_storable_generic,
        )

        contract_1 = self._set_order_product_and_confirm(self.so, self.pc_service_i5)
        self.assertEqual(contract_1.main_rental_product, self.pc_storable_generic)

        contract_2 = self._set_order_product_and_confirm(self.so2, self.pc_service_i7)
        self.assertEqual(contract_2.main_rental_product, self.pc_storable_generic)

    def test_main_rental_product_compute_missing_config(self):
        "If no storable product with the"
        contract = self._set_order_product_and_confirm(self.so, self.pc_service_i5)
        self.assertFalse(contract.main_rental_product)

    def test_main_rental_product_compute_no_product_line(self):
        "If no product line is designated (for legacy contracts), ensure the compute doesn't crash"
        self.ct.contract_line_ids.name = "1 month ##DUMMY##"
        create_config(
            self.pc_service_tmpl,
            "primary",
            self.pc_storable_tmpl_i5,
            self.pc_storable_i5,
            att_val_ids=self.cpu_i5,
        )

        contract = self._set_order_product_and_confirm(self.so, self.pc_service_i5)
        self.assertFalse(contract.main_rental_product)
