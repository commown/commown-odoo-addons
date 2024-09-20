from odoo import _, api, fields, models
from odoo.exceptions import AccessDenied, UserError


class WizardGrantEmployeePortalAccess(models.TransientModel):
    _name = "customer_team_manager.portal_access_wizard"
    _description = "Wizard to grant portal access to employees"

    allowed_groups = (
        "sales_team.group_sale_manager",
        "customer_team_manager.group_customer_admin",
    )

    employees = fields.Many2many(
        comodel_name="customer_team_manager.employee",
        relation="customer_team_manager_employee_portal_access_wizard_rel",
    )

    info = fields.Html(
        compute="_compute_info",
        store=False,
    )

    password = fields.Char(
        "Your password",
        help="We ask your password to enforce your company's security",
    )

    @api.depends("employees")
    def _compute_info(self):
        template = self.env.ref("customer_team_manager.portal_access_info")
        for rec in self:
            email_domains = {e.rsplit("@")[-1] for e in rec.employees.mapped("email")}
            rec.info = template.render({"email_domains": email_domains})

    def grant_portal_access(self):
        "Use portal wizard to grant or remove portal access according to in_portal"
        if not any(self.env.user.has_group(g) for g in self.allowed_groups):
            raise UserError(_("You are not allowed to manage employees."))

        employees = self.employees.filtered(lambda e: e.portal_status == "not_granted")
        wizard = employees.prepare_portal_wizard(True)
        wizard.action_apply()
        for employee in employees:
            employee._reset_roles()

        return True

    @api.model
    def create(self, vals):
        "Do not write the given password to the database"
        user = self.env.user.sudo(self.env.user.id)
        try:
            user._check_credentials(vals.pop("password", None))
        except AccessDenied:
            raise UserError(_("Incorrect password."))
        return super().create(vals)
