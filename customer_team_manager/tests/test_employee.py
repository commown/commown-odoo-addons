from odoo.exceptions import AccessError, ValidationError

from .common import CustomerTeamAbstractTC


class EmployeeTC(CustomerTeamAbstractTC):
    "Test class for team behaviour"

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

        # Set user as active
        self.user.sudo(self.user.id)._update_last_login()
        self.user._compute_state()
        self.assertEqual(self.user.state, "active")

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
        empl.action_grant_portal_access()
        self.assertEqual(empl.portal_status, "never_connected")

        empl.active = False
        self.assertEqual(empl.portal_status, "not_granted")

    def test_grant_and_revoke_portal_access(self):
        "Customer can grant and revoke portal access"

        # Create employee and check status is Not granted
        empl = self.create_employee(firstname="J", lastname="C", email="jc@test.coop")
        empl_sudo = empl.sudo()  # compute_sudo is True for portal_status

        empl_sudo._compute_portal_status()
        self.assertEqual(empl_sudo.portal_status, "not_granted")

        # Grant employee and check status is Never connected
        empl.action_grant_portal_access()
        empl_sudo._compute_portal_status()
        self.assertEqual(empl_sudo.portal_status, "never_connected")

        # Simulate employee login and check status is Already connected
        user = empl_sudo.partner.user_ids[0]
        user.sudo(user.id)._update_last_login()
        user._compute_state()

        empl_sudo._compute_portal_status()
        self.assertEqual(empl_sudo.portal_status, "already_connected")

        # Revoke portal access and check status is Not granted
        empl.active = False  # should call action_revoke_portal_access
        empl_sudo._compute_portal_status()
        self.assertEqual(empl_sudo.portal_status, "not_granted")

    def test_ui_customer_default_company(self):
        "Creating an employee from a customer should set its company"

        attrs = dict(firstname="F", lastname="L", email="a@b.c")
        empl = self.create_by_form("employee", **attrs)
        self.assertEqual(empl.sudo().company, self.company)

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
        empl.unlink()
        self.assertFalse(self.has_attachment(empl))
