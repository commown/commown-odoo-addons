from odoo import _, api, fields, models
from odoo.exceptions import AccessDenied, UserError


class CustomerDedicatedGrantPortalAccessWizard(models.TransientModel):
    _name = "customer_team_manager.portal_access_wizard"
    _description = "Wizard for customers to grant portal access to colleagues"

    allowed_groups = (
        "sales_team.group_sale_manager",
        "customer_team_manager.group_customer_admin",
    )

    customer_partners = fields.Many2many(
        comodel_name="res.partner",
    )

    info = fields.Html(
        compute="_compute_info",
        store=False,
    )

    password = fields.Char(
        "Your password",
        help="We ask your password to enforce your company's security",
    )

    @api.depends("customer_partners")
    def _compute_info(self):
        template = self.env.ref("customer_team_manager.portal_access_info")
        mail_ext = lambda email: email.rsplit("@")[-1]
        for rec in self:
            email_domains = {mail_ext(self.env.user.login)} | {
                mail_ext(e) for e in self.mapped("customer_partners.email")
            }
            rec.info = template.render({"email_domains": email_domains})

    def _prepare_portal_wizard(self, partners):
        model = self.env["portal.wizard"].with_context(active_ids=partners.ids)
        wizard = model.sudo().create({})
        # Filter to avoid a crash when 2 partners have the same email:
        wizard.user_ids.filtered(lambda u: u.partner_id in partners).update(
            {"in_portal": True}
        )
        return wizard

    def grant_portal_access(self):
        "Use portal wizard to grant or remove portal access according to in_portal"
        if not any(self.env.user.has_group(g) for g in self.allowed_groups):
            raise UserError(_("You are not allowed to manage users."))

        partners = self.customer_partners.filtered(
            lambda e: e.portal_status == "not_granted"
        )

        wizard = self._prepare_portal_wizard(partners)
        wizard.action_apply()

        for partner in partners:
            partner._reset_roles()

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
