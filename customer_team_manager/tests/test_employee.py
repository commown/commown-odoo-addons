from odoo.exceptions import AccessError, ValidationError

from .common import CustomerTeamAbstractTC


class EmployeeTC(CustomerTeamAbstractTC):
    "Test class for employee behaviour"

    def test_name_get(self):
        "Employee display name should be a concatenation of first and last names"

        empl = self.create_employee(firstname="J", lastname="C", email="jc@test.coop")
        self.assertEqual(empl.display_name, "J C")

    def test_create_automatic_company(self):
        "Employee creation by a customer should set its company"

        empl = self.create_employee(firstname="J", lastname="C", email="jc@test.coop")

        self.assertEqual(empl.sudo().company, self.company)

        with self.assertRaises(AccessError):
            empl.company

    def test_create_with_partner(self):
        "Creation by an internal user should set partner email"

        # Create an employee using the admin user
        partner = self.user.partner_id
        partner.email = "partner@test.coop"

        attrs = {"firstname": "First", "lastname": "Last", "phone": "060000000000"}
        empl = self.create_employee(
            sudo=False, partner=partner.id, company=self.company.id, **attrs
        )

        self.assertEqual(empl.email, "partner@test.coop")

    def test_write_email(self):
        "Managers can overwrite the employee email, not customers"

        partner = self.user.partner_id
        attrs = {f: partner[f] for f in ("firstname", "lastname", "email")}
        empl = self.create_employee(
            sudo=False, partner=partner.id, company=self.company.id, **attrs
        )

        self.assertNotEqual(empl.portal_status, "not_granted")  # test pre-requisite

        # Check setting the email using a sale manager does not raise:
        empl.email = "i_know_what_i_am_doing@test.coop"

        empl_seen_by_customer = empl.sudo(self.user.id)
        with self.assertRaises(ValidationError) as err:
            empl_seen_by_customer.email = "raises_error@test.coop"
        self.assertEqual(
            err.exception.name,
            "Employee is now active: its email cannot be modified anymore!",
        )

    def test_write_active_false_revokes(self):
        "Setting an employee as inactive should revoke is portal access"

        empl = self.create_employee(firstname="J", lastname="C", email="jc@test.coop")
        self._grant_portal_access(empl)
        self.assertEqual(empl.portal_status, "never_connected")

        empl.active = False
        self.assertEqual(empl.portal_status, "not_granted")

    def test_grant_and_revoke_portal_access(self):
        "Customer can grant and revoke portal access"

        role_accounting = self.env.ref("customer_team_manager.customer_role_accounting")
        empl = self.create_employee(
            firstname="J",
            lastname="C",
            email="jc@test.coop",
            roles=[(6, 0, role_accounting.ids)],
        )
        self.assertEqual(empl.portal_status, "not_granted")

        self._grant_portal_access(empl)
        self.assertEqual(empl.portal_status, "never_connected")

        empl.action_revoke_portal_access()
        self.assertEqual(empl.portal_status, "not_granted")

        self._grant_portal_access(empl)
        self.assertEqual(empl.portal_status, "never_connected")

        self.simulate_user_login(empl.sudo().partner.user_ids)
        self.assertEqual(empl.portal_status, "already_connected")

        empl.action_revoke_portal_access()
        self.assertEqual(empl.portal_status, "not_granted")

    def test_ui_customer_default_company_and_role(self):
        "Creating an employee from a customer should set its company and employee role"

        attrs = dict(firstname="F", lastname="L", email="a@b.c")
        empl = self.create_by_form("employee", **attrs)

        self.assertEqual(empl.sudo().company, self.company)

        user_role = self.env.ref("customer_team_manager.customer_role_user")
        self.assertEqual(empl.roles, user_role)

    def test_ui_internal_user_onchange_company(self):
        """Creating an employee with an internal user should work

        This test covers the onchange company code.
        """

        attrs = dict(
            {"firstname": "F", "lastname": "L", "email": "a@b.c"},
            partner=self.user.partner_id,
            company=self.company,
        )
        empl = self.create_by_form("employee", sudo=False, **attrs)
        self.assertEqual(empl.sudo().company, self.company)

    def has_attachment(self, entity):
        self.env.cr.execute(
            "SELECT id FROM ir_attachment WHERE res_model=%s AND res_id=%s",
            [entity._name, entity.id],
        )
        return bool(self.env.cr.fetchall())

    def test_write_and_unlink_with_image(self):
        empl = self.create_employee(firstname="J", lastname="C", email="jc@test.coop")
        old_image = empl.image_medium

        self.assertTrue(self.has_attachment(empl))
        empl.image_medium = False
        self.assertFalse(self.has_attachment(empl))

        empl.image_medium = old_image
        self.assertTrue(self.has_attachment(empl))
        empl.sudo().unlink()
        self.assertFalse(self.has_attachment(empl))

    def test_unlink_not_granted_to_customers(self):
        "Even group_customer_admin members are not granted unlink permission"
        empl = self.create_employee(firstname="J", lastname="C", email="jc@test.coop")
        _empl = empl.sudo(self.user)

        with self.assertRaises(AccessError) as err:
            _empl.unlink()
        self.assertIn("customer_team_manager.employee", err.exception.name)
        self.assertIn("Operation: unlink", err.exception.name)

    def test_write_with_role_error(self):
        user_role = self.env.ref("customer_team_manager.customer_role_user")
        empl = self.create_employee(firstname="J", lastname="C", email="jc@test.coop")

        with self.assertRaises(ValidationError) as err:
            self.admin.write({"roles": [(6, 0, user_role.ids)]})
        self.assertEqual(err.exception.name, "At least one administrator is mandatory")

    def test_create_and_write_with_role_ok(self):
        admin = self.create_admin(firstname="J", lastname="C", email="jc@test.coop")
        self._grant_portal_access(admin)

        self.assertIsAdmin(admin)

        empl = self.create_employee(firstname="V", lastname="C", email="vc@test.coop")
        self._grant_portal_access(empl)
        self.assertIsUser(empl)

        admin_role = self.env.ref("customer_team_manager.customer_role_admin")
        empl.write({"roles": [(6, 0, admin_role.ids)]})
        self.assertIsAdmin(empl)

        user_role = self.env.ref("customer_team_manager.customer_role_user")
        admin.write({"roles": [(6, 0, user_role.ids)]})
        self.assertIsUser(admin)

    def test_sync_employee_to_partner(self):
        empl = self.create_employee(firstname="V", lastname="C", email="vc@test.coop")
        new_attrs = {
            "firstname": "V_",
            "lastname": "C_",
            "phone": "0102030405",
            "email": "toto@test.coop",
        }
        empl.update(new_attrs)

        partner = empl.sudo().partner
        for name, value in new_attrs.items():
            self.assertEqual(getattr(partner, name), value, name)

    def test_sync_partner_to_employee(self):
        empl = self.create_employee(firstname="V", lastname="C", email="vc@test.coop")
        self._grant_portal_access(empl)
        partner = empl.sudo().partner

        new_attrs = {
            "firstname": "V_",
            "lastname": "C_",
            "phone": "0102030405",
            "email": "toto@test.coop",
        }
        partner.update(new_attrs)

        for name, value in new_attrs.items():
            self.assertEqual(getattr(empl, name), value, name)
