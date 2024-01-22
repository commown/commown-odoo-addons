from odoo.tests import SavepointCase
from odoo.tests.common import Form


class CustomerTeamAbstractTC(SavepointCase):
    "Abstract class for present module's tests"

    def setUp(self):
        super().setUp()
        self.company = self.env["res.partner"].create(
            {"name": "Test company", "is_company": True}
        )

        self.user = self.env.ref("base.demo_user0")
        self.simulate_user_login(self.user)
        partner = self.user.partner_id
        partner.update({"parent_id": self.company.id, "firstname": "F"})

        self.env.ref("customer_team_manager.group_customer").users |= self.user
        self.env.ref("customer_team_manager.group_manager").users |= self.env.user

        admin_role = self.env.ref("customer_team_manager.customer_role_admin")
        self.admin = self.env["customer_team_manager.employee"].create(
            {
                "firstname": partner.firstname,
                "lastname": partner.lastname,
                "email": partner.email,
                "phone": partner.phone,
                "roles": [(6, 0, admin_role.ids)],
                "partner": partner.id,
                "company": partner.commercial_partner_id.id,
            }
        )

    def create_employee(self, sudo=True, sudo_as=None, **kwargs):
        user_role = self.env.ref("customer_team_manager.customer_role_user")
        kwargs.setdefault("roles", [(6, 0, user_role.ids)])
        model = self.env["customer_team_manager.employee"]
        if sudo:
            model = model.sudo(sudo_as or self.user.id)
        return model.create(kwargs)

    def create_admin(self, *args, **kwargs):
        admin_role = self.env.ref("customer_team_manager.customer_role_admin")
        kwargs.setdefault("roles", [(6, 0, admin_role.ids)])
        return self.create_employee(*args, **kwargs)

    def create_team(self, sudo=True, sudo_as=None, **kwargs):
        model = self.env["customer_team_manager.team"]
        if sudo:
            model = model.sudo(sudo_as or self.user.id)
        return model.create(kwargs)

    def create_by_form(self, model, sudo=True, sudo_as=None, **kwargs):
        if "." not in model:
            model = "customer_team_manager." + model
        model = self.env[model]
        if sudo:
            model = model.sudo(sudo_as or self.user.id)
        form = Form(model)
        for field, value in kwargs.items():
            setattr(form, field, value)
        return form.save()

    def simulate_user_login(self, user):
        user.sudo(user.id)._update_last_login()
        user.invalidate_cache()
        self.assertEqual(user.state, "active")

    def assertIsAdmin(self, employee):
        user = employee.sudo().partner.user_ids[0]
        self.assertTrue(user.has_group("base.group_portal"))
        self.assertTrue(user.has_group("customer_team_manager.group_customer_admin"))

    def assertIsUser(self, employee):
        user = employee.sudo().partner.user_ids[0]
        self.assertTrue(user.has_group("base.group_portal"))
        self.assertFalse(user.has_group("customer_team_manager.group_customer_admin"))
