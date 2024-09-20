import json

from odoo.exceptions import UserError

from .common import CustomerTeamAbstractTC


class ResPartnerTC(CustomerTeamAbstractTC):
    "Test class for partner methods"

    def create_partner(self, **kwargs):
        default = dict(
            firstname="F",
            lastname="L",
            email="a@b.com",
            parent_id=self.company.id,
        )
        return self.env["res.partner"].create(dict(default, **kwargs))

    def test_action_create_employee_error_wrong_type(self):
        partner = self.create_partner(type="other")

        with self.assertRaises(UserError) as err:
            partner.action_create_employee()

        expected_msg = "Partner 'F L' (id %d) is of type 'other', not 'contact'"
        self.assertEqual(err.exception.name, expected_msg % partner.id)

    def test_action_create_employee_error_is_company(self):
        partner = self.env.ref("base.res_partner_12")
        with self.assertRaises(UserError) as err:
            partner.action_create_employee()

        expected_msg = "Partner '%s' (id %d) is a company"
        self.assertEqual(err.exception.name, expected_msg % (partner.name, partner.id))

    def test_action_create_employee_error_several_admins_at_once(self):
        p1 = self.create_partner(email="p1@b.com")
        p2 = self.create_partner(email="p2@b.com")

        with self.assertRaises(UserError) as err:
            (p1 | p2).action_create_employee(admin=True)

        expected_msg = "Cannot create more than one admin at once!"
        self.assertEqual(err.exception.name, expected_msg)

    def test_action_create_employee_error_admin_has_no_user(self):
        partner = self.create_partner()

        with self.assertRaises(UserError) as err:
            partner.action_create_employee(admin=True)

        expected_msg = "Partner 'F L' (id %d) has no user yet"
        self.assertEqual(err.exception.name, expected_msg % partner.id)

    def info_notifs(self, user=None):
        user = user or self.env.user
        return self.env["bus.bus"].search(
            [("channel", "=", json.dumps(user.notify_info_channel_name))]
        )

    def test_action_create_employees_ok(self):
        "Create employees action must accomadate already existing and give feedback"

        # Create an pre-existing admin employee and a partner to become employee:
        admin = self.create_admin(firstname="J", lastname="C", email="jc@test.coop")
        self._grant_portal_access(admin)
        partner = self.create_partner()
        prev_notifs = self.info_notifs()

        # Select both and call the action
        (admin.sudo().partner | partner).action_create_employee()

        self.assertEqual(len(partner.get_employees()), 1)
        self.assertEqual(len(admin.sudo().partner.get_employees()), 1)

        new_notifs = self.info_notifs() - prev_notifs
        self.assertEqual(
            [json.loads(n.message)["message"] for n in new_notifs],
            [
                "<b>Created 1 employees:</b><br>"
                "- F L (Employee)<br>"
                "<br>"
                "<b>Already existing employee(s):</b><br>"
                "- J C (Administrator)"
            ],
        )

    def test_action_create_employees_nothing_done(self):
        "Create employees action must notify when nothing was done"

        admin = self.create_admin(firstname="J", lastname="C", email="jc@test.coop")
        self._grant_portal_access(admin)
        prev_notifs = self.info_notifs()

        # Select both and call the action
        admin.sudo().partner.action_create_employee()

        new_notifs = self.info_notifs() - prev_notifs
        self.assertEqual(
            [json.loads(n.message)["message"] for n in new_notifs],
            [
                "<b>No employee created!</b><br>"
                "<br>"
                "<b>Already existing employee(s):</b><br>"
                "- J C (Administrator)"
            ],
        )
