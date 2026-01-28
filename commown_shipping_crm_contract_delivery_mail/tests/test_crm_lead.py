from datetime import date

from odoo.tests import tagged

from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


@tagged("-at_install", "post_install")
class CrmLeadTC(RentalSaleOrderTC):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.so1 = cls.create_sale_order()
        cls.so2 = cls.create_sale_order()

        cls.so1.team_id.default_perform_actions_on_delivery = True

        (cls.so1 | cls.so2).mapped("order_line.product_id").update(
            {"followup_sales_team_id": cls.so1.team_id.id}
        )

    def test_default_action_on_delivery_with_contract(self):
        # Case 1: default actions are enabled
        self.so1.team_id.default_perform_actions_on_delivery = True
        lead1 = self._create_ra_leads(self.so1).filtered("contract_id")[0]

        self.assertTrue(lead1.send_email_on_delivery)

        # Case 2: default actions are disabled
        self.so2.team_id.default_perform_actions_on_delivery = False
        lead2 = self._create_ra_leads(self.so2).filtered("contract_id")[0]

        self.assertFalse(lead2.send_email_on_delivery)

    def test_default_action_on_delivery_without_contract(self):
        "Even when team perform actions on delivery"
        # Remove all contract products from sale order to get leads without a contract
        self.so1.order_line.filtered("product_id.is_contract").unlink()

        self.so1.team_id.default_perform_actions_on_delivery = True
        lead = self._create_ra_leads(self.so1).filtered(lambda l: not l.contract_id)[0]

        self.assertFalse(lead.contract_id)  # Check pre-requisite
        self.assertFalse(lead.send_email_on_delivery)

        # Check delivery does not crash
        lead.delivery_date = date(2017, 1, 1)

    def _create_ra_leads(self, so):
        "Confirm the sale and return all its just-created risk-analysis leads"
        so.action_confirm()
        return self.env["crm.lead"].search([("so_line_id.order_id", "=", so.id)])
