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
        "customer_manager_base.group_customer_admin",
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

        for rec in self:
            invalid_email_partners = rec.customer_partners.filtered(_has_invalid_email)
            emails = (rec.customer_partners - invalid_email_partners).mapped("email")
            email_domains |= {mail_ext(e) for e in emails}
            rec.info = self.env["ir.qweb"]._render(
                "customer_team_manager.portal_access_info",
                {
                    "valid_emails": emails,
                    "email_domains": email_domains,
                    "invalid_email_partners": invalid_email_partners,
                },
            )

    def grant_portal_access(self):
        "Use portal wizard to grant or remove portal access according to is_portal"
        if not any(self.env.user.has_group(g) for g in self.allowed_groups):
            raise UserError(_("You are not allowed to manage users."))

        partners = self.customer_partners.filtered(
            lambda e: e.portal_status == "not_granted"
        ).filtered(_has_valid_email)

        model = self.env["portal.wizard"].with_context(active_ids=partners.ids)
        wizard = model.sudo().create({})

        non_portal_users = wizard.user_ids.filtered(
            lambda user: user.partner_id in partners and not user.is_portal
        )

        # action_grant_access() requires only one user at a time (self.ensure_one())
        for user in non_portal_users:
            user.action_grant_access()

        for partner in partners:
            partner._reset_roles()

        return True

    @api.model_create_multi
    def create(self, vals_list):
        "Do not write the given password to the database"
        user = self.env.user.with_user(self.env.user.id)
        try:
            for vals in vals_list:
                user._check_credentials(
                    vals.pop("password", None), {"interactive": True}
                )
        except AccessDenied as err:
            raise UserError(_("Incorrect password.")) from err
        return super().create(vals_list)
