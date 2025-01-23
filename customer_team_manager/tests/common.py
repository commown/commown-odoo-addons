from odoo.tests import SavepointCase
from odoo.tests.common import Form


class CustomerTeamManagerAbstractTC(SavepointCase):
    "Abstract class for present module's tests"

    @classmethod
    def setUpClass(cls):
        super(CustomerTeamManagerAbstractTC, cls).setUpClass()

        ref = cls.env.ref
        group_sale_manager = ref("sales_team.group_sale_manager")

        cls.customer_company = cls.env["res.partner"].create(
            {"name": "Test company", "is_company": True}
        )

        cls.customer_user_admin = ref("base.demo_user0")

        admin_role = cls.env.ref("customer_team_manager.customer_role_admin")
        cls.customer_partner_admin = cls.customer_user_admin.partner_id
        cls.customer_partner_admin.update(
            {
                "firstname": "F",
                "parent_id": cls.customer_company.id,
                "customer_roles": [(6, 0, admin_role.ids)],
            }
        )

        group_sale_manager.users |= cls.env.user | cls.env.ref("base.user_admin")

    def _model(self, model_name, sudo_as=None):
        model = self.env[model_name]
        if sudo_as:
            model = model.sudo(sudo_as)
        return model

    def create_team(self, sudo_as=None, **kwargs):
        return self._model("customer_team_manager.team", sudo_as).create(kwargs)

    def create_partner(self, sudo_as=None, **kwargs):
        return self._model("res.partner", sudo_as).create(kwargs)

    def create_by_form(self, model, sudo_as=None, **kwargs):
        if "." not in model:
            model = "customer_team_manager." + model
        form = Form(self._model(model, sudo_as))
        for field, value in kwargs.items():
            setattr(form, field, value)
        return form.save()

    def simulate_user_login(self, user):
        user.sudo(user.id)._update_last_login()
        user.invalidate_cache()
        self.assertEqual(user.state, "active")

    def assertIsAdmin(self, partner):
        user = partner.sudo().user_ids[0]
        self.assertTrue(user.has_group("base.group_portal"))
        self.assertTrue(user.has_group("customer_team_manager.group_customer_admin"))

    def assertIsUser(self, partner):
        user = partner.sudo().user_ids[0]
        self.assertTrue(user.has_group("base.group_portal"))
        self.assertFalse(user.has_group("customer_team_manager.group_customer_admin"))

    def _grant_portal_access(self, partner, passwd="admin"):
        "Use the admin user to grant portal access to given employee"
        _adm = self.env.ref("base.user_admin")
        wmod = self.env["customer_team_manager.portal_access_wizard"].sudo(_adm.id)
        wizard = wmod.create(
            {
                "customer_partners": [(6, 0, partner.ids)],
                "password": passwd,
            }
        )
        wizard.grant_portal_access()
        return wizard

    def count_seen_partners(self, sudo_as=False):
        return self._model("res.partner", sudo_as).search_count([])
