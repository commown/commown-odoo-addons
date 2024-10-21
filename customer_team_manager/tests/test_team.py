from odoo.exceptions import AccessError

from .common import CustomerTeamManagerAbstractTC


class TeamTC(CustomerTeamManagerAbstractTC):
    "Test class for team behaviour"

    def test_create_automatic_company(self):
        team = self.create_team(sudo_as=self.customer_user_admin, name="Test team")

        self.assertEqual(team.sudo().customer_company, self.customer_company)

        with self.assertRaises(AccessError):
            team.customer_company

    def test_full_name(self):
        admin = self.customer_user_admin
        t1 = self.create_team(sudo_as=admin, name="Team 1")
        t2 = self.create_team(sudo_as=admin, name="Team 2", parent_team=t1.id)

        self.assertEqual(t2.display_name, "Team 1 / Team 2")

    def test_order(self):
        admin = self.customer_user_admin
        t1 = self.create_team(sudo_as=admin, name="T1")
        t2 = self.create_team(sudo_as=admin, name="T2")
        t3 = self.create_team(sudo_as=admin, name="T3", parent_team=t2.id)
        t4 = self.create_team(sudo_as=admin, name="T4", parent_team=t1.id)

        self.assertEqual(
            t1.search([]).mapped("full_name"),
            ["T1", "T1 / T4", "T2", "T2 / T3"],
        )

    def test_ui_customer_default_company(self):
        "Creating a team from a customer should set its company"

        admin = self.customer_user_admin
        team = self.create_by_form("team", sudo_as=admin, name="T")
        self.assertEqual(team.sudo().customer_company, self.customer_company)

    def test_ui_internal_user_onchange_company(self):
        """Creating an employee with an internal user should work

        This test covers the onchange company code.
        """

        company = self.customer_company
        team = self.create_by_form("team", name="T", customer_company=company)
        self.assertEqual(team.sudo().customer_company, company)
