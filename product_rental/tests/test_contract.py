from datetime import timedelta

from odoo.exceptions import ValidationError

from odoo.addons.contract.tests.test_contract import TestContractBase

from .common import RentalSaleOrderTC


class ContractTC(TestContractBase):
    def test_inverse_date_start(self):
        assert self.contract.contract_line_ids
        new_date = self.contract.date_start - timedelta(days=1)
        self.contract.date_start = new_date
        self.assertEqual(self.contract.recurring_next_date, new_date)
        clines = self.contract.contract_line_ids
        self.assertEqual(set(clines.mapped("date_start")), {new_date})
        self.assertEqual(set(clines.mapped("recurring_next_date")), {new_date})

    def test_inverse_recurring_next_date_error(self):
        self.contract.is_auto_pay = False
        init_recurring_next_date = self.contract.recurring_next_date
        self.contract.recurring_create_invoice()

        with self.assertRaises(ValidationError) as err:
            self.contract.recurring_next_date = init_recurring_next_date

        self.assertIn(
            "There are invoices past the new next recurring date", str(err.exception)
        )

    def test_inverse_recurring_next_date_ok(self):
        self.contract.is_auto_pay = False
        init_recurring_next_date = self.contract.recurring_next_date
        inv = self.contract.recurring_create_invoice()

        inv.unlink()
        self.contract.recurring_next_date = init_recurring_next_date

        self.assertEqual(
            set(self.contract.mapped("contract_line_ids.recurring_next_date")),
            {init_recurring_next_date},
        )


class ContractFromSale(RentalSaleOrderTC):
    "Test for contract methods that needs a contract from a sale order"

    def setUp(self):
        super().setUp()
        self.so = self.create_sale_order()
        self.so.action_confirm()
        self.contract = self.env["contract.contract"].of_sale(self.so)[1]
        self.assertIn(
            "##PRODUCT##",
            self.contract.contract_template_id.contract_line_ids[0].name,
            "Test prerequisite failed: Contract template must have a ##PRODUCT## line",
        )

    def test_main_rental_service_standard(self):
        service = self.contract.get_main_rental_service()
        self.assertEqual(
            service.property_contract_template_id,
            self.contract.contract_template_id,
        )

    def test_main_rental_service_product_changed(self):
        service = self.contract.get_main_rental_service()

        new_contract_tmpl = service.property_contract_template_id.copy()
        service.property_contract_template_id = new_contract_tmpl.id

        self.assertEqual(service, self.contract.get_main_rental_service(_raise=False))

        with self.assertRaises(ValidationError) as err:
            self.contract.get_main_rental_service()
        self.assertEqual(
            err.exception.name,
            "Contract %s (id %d) has a main rental service"
            " with an incoherent contract model %s"
            % (self.contract.name, self.contract.id, new_contract_tmpl.name),
        )

    def test_main_rental_service_contract_two_services(self):
        service = self.contract.get_main_rental_service()
        clines = self.contract.contract_line_ids
        product2 = clines[1].sale_order_line_id.product_id.product_tmpl_id
        product2.property_contract_template_id = service.property_contract_template_id

        services = self.contract.get_main_rental_service(_raise=False)
        self.assertEqual(service, services)
