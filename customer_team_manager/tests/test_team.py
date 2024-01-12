from odoo.exceptions import AccessError

from .common import CustomerTeamAbstractTC


class TeamTC(CustomerTeamAbstractTC):
    "Test class for team behaviour"

    def test_create_automatic_company(self):
        team = self.create_team(name="Test team")

        self.assertEqual(team.sudo().company, self.company)

        with self.assertRaises(AccessError):
            team.company

    def test_full_name(self):
        t1 = self.create_team(name="Team 1")
        t2 = self.create_team(name="Team 2", parent_team=t1.id)

        self.assertEqual(t2.display_name, "Team 1 / Team 2")

    def test_order(self):
        t1 = self.create_team(name="T1")
        t2 = self.create_team(name="T2")
        t3 = self.create_team(name="T3", parent_team=t2.id)
        t4 = self.create_team(name="T4", parent_team=t1.id)

        self.assertEqual(
            t1.search([]).mapped("full_name"),
            ["T1", "T1 / T4", "T2", "T2 / T3"],
        )

    def test_ui_customer_default_company(self):
        "Creating a team from a customer should set its company"

        team = self.create_by_form("team", name="T")
        self.assertEqual(team.sudo().company, self.company)

    def test_ui_internal_user_onchange_company(self):
        """Creating an employee with an internal user should work

        This test covers the onchange company code.
        """

        team = self.create_by_form("team", sudo=False, name="T", company=self.company)
        self.assertEqual(team.sudo().company, self.company)
