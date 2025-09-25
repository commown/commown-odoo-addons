from odoo.exceptions import AccessError

from .common import CustomerTeamManagerAbstractTC


class TeamTC(CustomerTeamManagerAbstractTC):
    "Test class for team behaviour"

    def seen_teams(self, sudo_as=False):
        return self._model("customer_team_manager.team", sudo_as).search([])

    def test_create_automatic_company(self):
        team = self.create_team(sudo_as=self.customer_user_admin, name="Test team")

        self.assertEqual(team.sudo().customer_company, self.customer_company)

        with self.assertRaises(AccessError):
            team.customer_company  # pylint: disable=pointless-statement

    def test_read(self):
        "Portal users must see (only) their company's teams"
        c1 = self.customer_company
        team1 = self.create_team(sudo_as=self.customer_user_admin, name="Team1")
        empl1 = self.create_partner(
            name="Employee1", email="employee1@c1.coop", parent_id=c1.id
        )
        self._grant_portal_access(empl1)
        user1 = empl1.user_ids[0]

        c2 = self.customer_company.copy({"name": "Test company2"})
        team2 = self.create_team(name="Team2", customer_company=c2.id)
        empl2 = self.create_partner(
            name="Employee2", email="employee2@c2.coop", parent_id=c2.id
        )
        self._grant_portal_access(empl2)
        user2 = empl2.user_ids[0]

        self.assertEqual(self.seen_teams(self.customer_user_admin), team1)
        self.assertEqual(self.seen_teams(user1), team1)
        self.assertEqual(self.seen_teams(user2), team2)

    def test_full_name(self):
        admin = self.customer_user_admin
        t1 = self.create_team(sudo_as=admin, name="Team 1")
        t2 = self.create_team(sudo_as=admin, name="Team 2", parent_team=t1.id)

        self.assertEqual(t2.display_name, "Team 1 / Team 2")

    def test_order(self):
        admin = self.customer_user_admin
        t1 = self.create_team(sudo_as=admin, name="T1")
        t2 = self.create_team(sudo_as=admin, name="T2")
        self.create_team(sudo_as=admin, name="T3", parent_team=t2.id)
        self.create_team(sudo_as=admin, name="T4", parent_team=t1.id)

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
        team = self.create_by_form(
            "customer_team_manager.team", name="T", customer_company=company
        )
        self.assertEqual(team.sudo().customer_company, company)
