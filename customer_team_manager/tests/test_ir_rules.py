from .common import CustomerTeamAbstractTC


class TeamAndEmployeeIrRulesTC(CustomerTeamAbstractTC):
    "Test class for team-related ir_rules"

    def setUp(self):
        super().setUp()
        self.company2 = self.env["res.partner"].create(
            {"name": "Test company2", "is_company": True}
        )
        partner2 = self.user.partner_id.copy(
            {"firstname": "P2", "parent_id": self.company2.id}
        )
        self.user2 = self.user.copy({"login": "u2@a.coop", "partner_id": partner2.id})
        partner2.action_create_employee(admin=True)
        self.assertTrue(
            self.user2.has_group("customer_team_manager.group_customer_admin")
        )

    def test_see_own_teams_only(self):
        t_model = self.env["customer_team_manager.team"]

        admin_user1 = self.user
        team1 = self.create_team(name="team1", sudo_as=admin_user1)

        admin_user2 = self.user2
        team2 = self.create_team(name="team2", sudo_as=admin_user2)

        self.assertEqual(t_model.sudo(admin_user1.id).search([]), team1)
        self.assertEqual(t_model.sudo(admin_user2.id).search([]), team2)

    def test_see_own_employees_only(self):
        e_model = self.env["customer_team_manager.employee"]

        admin_user1 = self.user
        admin_empl1 = e_model.search([("partner.user_ids", "=", admin_user1.id)])
        empl1 = self.create_employee(
            firstname="F1",
            lastname="L1",
            email="e1@a.coop",
            sudo_as=admin_user1,
        )

        admin_user2 = self.user2
        admin_empl2 = e_model.search([("partner.user_ids", "=", admin_user2.id)])
        empl2 = self.create_employee(
            firstname="F2",
            lastname="L2",
            email="e2@a.coop",
            sudo_as=admin_user2,
        )

        self.assertEqual(e_model.sudo(admin_user1.id).search([]), admin_empl1 | empl1)
        self.assertEqual(e_model.sudo(admin_user2.id).search([]), admin_empl2 | empl2)
