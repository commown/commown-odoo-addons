import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessDenied, UserError

# Cannot do much better without actually sending an email:
EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")


def _has_valid_email(partner):
    return isinstance(partner.email, str) and EMAIL_REGEX.fullmatch(partner.email)


def _has_invalid_email(partner):
    return not _has_valid_email(partner)


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
        def mail_ext(email):
            return email.rsplit("@")[-1]

        email_domains = set()
        if self.env["res.partner"]._current_user_is_customer_admin():
            email_domains.add(mail_ext(self.env.user.login))

        template = self.env.ref("customer_team_manager.portal_access_info")

        for rec in self:
            invalid_email_partners = rec.customer_partners.filtered(_has_invalid_email)
            emails = (rec.customer_partners - invalid_email_partners).mapped("email")
            email_domains |= {mail_ext(e) for e in emails}
            rec.info = template.render(
                {
                    "valid_emails": emails,
                    "email_domains": email_domains,
                    "invalid_email_partners": invalid_email_partners,
                }
            )

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
        ).filtered(_has_valid_email)

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
