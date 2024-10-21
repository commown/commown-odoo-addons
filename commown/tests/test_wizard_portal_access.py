from odoo.addons.customer_team_manager.tests.common import CustomerTeamManagerAbstractTC


class WizardPortalAccessCustomerTeamManagerTC(CustomerTeamManagerAbstractTC):
    "Tests relative to customization of customer_team_manager's portal access wizard"

    def test_website_on_granted_employee(self):
        empl = self.create_partner(
            sudo_as=self.customer_user_admin,
            name="New Empl",
            email="employee@test.coop",
        )
        self._grant_portal_access(empl)

        b2b_website = self.env.ref("website_sale_b2b.b2b_website")
        self.assertEqual(empl.user_ids.website_id, b2b_website)
