from lxml.html import fromstring

from odoo.exceptions import UserError

from .common import CustomerTeamManagerAbstractTC


class WizardGrantEmployeePortalAccessTC(CustomerTeamManagerAbstractTC):
    "Tests related to the customer_team_manager.portal_access_wizard model"

    def test_ok(self):
        admin = self.customer_user_admin
        admin.password = "admin"
        admin.login = "admin@test.org"

        empl1 = self.create_partner(sudo_as=admin, name="E1 L", email="e1@test.coop")
        empl2 = self.create_partner(sudo_as=admin, name="E2 L", email="e2@test.coop")
        empl3 = self.create_partner(sudo_as=admin, name="E3 L", email="e3@test.com")
        empl4 = self.create_partner(sudo_as=admin, name="E4 L", email="invalid")

        all_employees = empl1 | empl2 | empl3 | empl4

        wizard = self._grant_portal_access(empl1)
        self.assertEqual(
            all_employees.mapped("portal_status"),
            ["never_connected", "not_granted", "not_granted", "not_granted"],
        )

        wizard = self._grant_portal_access(all_employees, sudo_as=admin)

        self.assertEqual(
            all_employees.mapped("portal_status"),
            ["never_connected"] * 3 + ["not_granted"],
        )

        doc = fromstring(wizard.info)
        self.assertEqual(
            set(doc.xpath("//*[@id='grant-access-possible-fraud-warning']//li/text()")),
            {"test.com", "test.coop", "test.org"},
        )
        self.assertEqual(
            doc.xpath("//*[@id='grant-access-invalid-emails-info']//li/text()"),
            ["E4 L"],
        )

    def test_error_wrong_password(self):
        admin = self.customer_user_admin
        empl = self.create_partner(sudo_as=admin, name="E L", email="e@test.coop")

        with self.assertRaises(UserError) as err:
            self._grant_portal_access(empl, passwd="wrong password")

        self.assertEqual(err.exception.name, "Incorrect password.")

    def test_error_not_allowed(self):
        group_sale_manager = self.env.ref("sales_team.group_sale_manager")
        admin = self.customer_user_admin
        empl = self.create_partner(sudo_as=admin, name="E L", email="e@test.coop")

        with self.assertRaises(UserError) as err:
            self.env.ref("base.user_admin").groups_id -= group_sale_manager
            self._grant_portal_access(empl)

        self.assertEqual(err.exception.name, "You are not allowed to manage users.")
