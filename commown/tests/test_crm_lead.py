from datetime import date

from odoo.tests.common import at_install, post_install

from odoo.addons.product_rental.models.sale_order_line import NO_DATE
from odoo.addons.product_rental.tests.common import RentalSaleOrderTC


@at_install(False)
@post_install(True)
class CrmLeadTC(RentalSaleOrderTC):
    def setUp(self):
        super(CrmLeadTC, self).setUp()
        self.so = self.create_sale_order()
        self.so.team_id.default_perform_actions_on_delivery = True
        self.so.mapped("order_line.product_id").update(
            {
                "followup_sales_team_id": self.so.team_id.id,
            }
        )

    def test_default_action_on_delivery(self):
        team = self.so.team_id

        team.default_perform_actions_on_delivery = True
        lead = self._create_ra_leads()[0]

        self.assertTrue(lead.send_email_on_delivery)

    def test_default_no_action_on_delivery(self):
        team = self.so.team_id

        team.default_perform_actions_on_delivery = False
        lead = self._create_ra_leads()[0]

        self.assertFalse(lead.send_email_on_delivery)

    def _create_ra_leads(self):
        """Confirm the sale and return the its just-created risk-analysis leads
        related to a contract (some products do not have a contract).
        """
        self.so.action_confirm()
        return self.env["crm.lead"].search(
            [
                ("so_line_id.order_id", "=", self.so.id),
                ("contract_id", "!=", False),
            ]
        )

    def test_actions_on_delivery_set_contract_start_date(self):
        lead = self._create_ra_leads()[0]
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
