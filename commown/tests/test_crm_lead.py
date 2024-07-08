from datetime import date

from odoo.tests.common import at_install, post_install

from odoo.addons.product_rental.models.contract import NO_DATE
from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


@at_install(False)
@post_install(True)
class CrmLeadTC(RentalSaleOrderTC):
    def setUp(self):
        super(CrmLeadTC, self).setUp()
        self.so = self.create_sale_order()
        self.so.team_id.default_perform_actions_on_delivery = True
        self.so.mapped("order_line.product_id").update(
            {"followup_sales_team_id": self.so.team_id.id}
        )

    def test_default_action_on_delivery_with_contract(self):
        self.so.team_id.default_perform_actions_on_delivery = True
        lead = self._create_ra_leads().filtered("contract_id")[0]

        self.assertTrue(lead.send_email_on_delivery)

    def test_default_action_on_delivery_without_contract(self):
        "Even when team perform actions on delivery"
        # Remove all contract products from sale order to get leads without a contract
        self.so.order_line.filtered("product_id.is_contract").unlink()

        self.so.team_id.default_perform_actions_on_delivery = True
        lead = self._create_ra_leads().filtered(lambda l: not l.contract_id)[0]

        self.assertFalse(lead.contract_id)  # Check pre-requisite
        self.assertFalse(lead.send_email_on_delivery)

    def test_default_no_action_on_delivery(self):
        self.so.team_id.default_perform_actions_on_delivery = False
        lead = self._create_ra_leads()[0]

        self.assertFalse(lead.send_email_on_delivery)

    def _create_ra_leads(self):
        "Confirm the sale and return all its just-created risk-analysis leads"
        self.so.action_confirm()
        return self.env["crm.lead"].search([("so_line_id.order_id", "=", self.so.id)])

    def test_actions_on_delivery_set_contract_start_date(self):
        lead = self._create_ra_leads().filtered("contract_id")[0]
        contract = lead.contract_id
        lead.send_email_on_delivery = False  # avoid setting-up email template

        # Check contract state before delivery
        self.assertFalse(contract.is_auto_pay)
        self.assertEqual(contract.date_start, NO_DATE)

        # Simulate delivery
        lead.delivery_date = date(2018, 1, 1)

        # Check results: contract started but is_auto_pay unchanged
        self.assertEqual(contract.date_start, date(2018, 1, 1))
        self.assertFalse(contract.is_auto_pay)

        # Simulate delivery again: happens when we send a new device
        # Contract start date should not change again!
        lead.delivery_date = date(2017, 1, 1)
        self.assertEqual(contract.date_start, date(2018, 1, 1))
