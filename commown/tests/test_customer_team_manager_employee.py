from odoo.addons.customer_team_manager.tests.common import CustomerTeamAbstractTC


class EmployeeTC(CustomerTeamAbstractTC):
    def test_website_on_granted_employee(self):
        empl = self.create_employee(firstname="J", lastname="C", email="jc@test.coop")
        empl.action_grant_portal_access()

        b2b_website = self.env.ref("website_sale_b2b.b2b_website")
        self.assertEqual(empl.sudo().partner.user_ids.website_id, b2b_website)
