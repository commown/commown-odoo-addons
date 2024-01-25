from odoo.tests import SavepointCase

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
        admin_user1 = self.user
        admin_empl1 = admin_user1.partner_id.get_employees()
        empl1 = self.create_employee(
            firstname="F1",
            lastname="L1",
            email="e1@a.coop",
            sudo_as=admin_user1,
        )

        admin_user2 = self.user2
        admin_empl2 = admin_user2.partner_id.get_employees()
        empl2 = self.create_employee(
            firstname="F2",
            lastname="L2",
            email="e2@a.coop",
            sudo_as=admin_user2,
        )

        e_model = self.env["customer_team_manager.employee"]
        self.assertEqual(e_model.sudo(admin_user1.id).search([]), admin_empl1 | empl1)
        self.assertEqual(e_model.sudo(admin_user2.id).search([]), admin_empl2 | empl2)


class PortalInvoiceIrRulesTC(SavepointCase):
    "Test class for portal user invoice-related access rules"

    def setUp(self):
        super().setUp()
        self.inv = self.env.ref("l10n_generic_coa.demo_invoice_1")

        partner1 = self.inv.partner_id.child_ids[0]
        self.user1 = self._give_portal_access(partner1)

        partner2 = self.inv.partner_id.child_ids[1]
        self.user2 = self._give_portal_access(partner2)

        self.assertNotIn(partner1, self.inv.message_partner_ids)
        self.assertNotIn(partner2, self.inv.message_partner_ids)

    def _give_portal_access(self, partner):
        model = self.env["portal.wizard"].with_context(active_ids=[partner.id])
        portal_wizard = model.sudo().create({})
        portal_wizard.user_ids.update({"in_portal": True})
        portal_wizard.action_apply()
        self.assertTrue(partner.user_ids)
        return partner.user_ids[0]

    def seen_invoices(self, user):
        return self.env["account.invoice"].sudo(user).search([])

    def follow_invoice(self, partner):
        self.env["mail.followers"].create(
            {
                "res_id": self.inv.id,
                "res_model": self.inv._name,
                "partner_id": partner.id,
            }
        )

    def test_directly_followed_invoice(self):
        "Portal users who follow an invoice directly must have read access to it"
        self.assertNotIn(self.inv, self.seen_invoices(self.user1))

        self.follow_invoice(self.user1.partner_id)
        self.assertIn(self.inv, self.seen_invoices(self.user1))

    def test_in_accounting_group(self):
        self.assertNotIn(self.inv, self.seen_invoices(self.user1))
        self.assertNotIn(self.inv, self.seen_invoices(self.user2))

        accounting_grp = self.env.ref("customer_team_manager.group_customer_accounting")
        accounting_grp.users |= self.user2

        self.assertNotIn(self.inv, self.seen_invoices(self.user1))
        self.assertIn(self.inv, self.seen_invoices(self.user2))
