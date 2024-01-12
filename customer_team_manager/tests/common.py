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
        self.user.partner_id.parent_id = self.company.id

        self.env.ref("customer_team_manager.group_customer").users |= self.user
        self.env.ref("customer_team_manager.group_manager").users |= self.env.user

    def create_employee(self, sudo=True, sudo_as=None, **kwargs):
        model = self.env["customer_team_manager.employee"]
        if sudo:
            model = model.sudo(sudo_as or self.user.id)
        return model.create(kwargs)

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
