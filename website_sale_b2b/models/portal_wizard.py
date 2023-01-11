from odoo import api, fields, models


class PortalWizard(models.TransientModel):
    _inherit = "portal.wizard"

    @api.model
    def default_get(self, fields_list):
        result = super(PortalWizard, self).default_get(fields_list)
        if "user_ids" in fields_list:
            self._complete_user_changes(result["user_ids"])
        return result

    def _complete_user_changes(self, user_changes):
        for user_change in user_changes:
            if user_change[0] != 0:
                continue
            attrs = user_change[2]
            partner = self.env["res.partner"].browse(attrs["partner_id"])
            websites = partner.mapped("user_ids.website_id")
            attrs.update(
                {
                    "had_user": bool(partner.user_ids),
                    "website_id": bool(websites) and websites[0].id,
                }
            )


class PortalWizardUser(models.TransientModel):
    _inherit = "portal.wizard.user"

    had_user = fields.Boolean()

    website_id = fields.Many2one(
        "website",
        string="Website",
        help="Empty means all websites",
    )

    @api.multi
    def _create_user(self):
        user = super(PortalWizardUser, self)._create_user()
        user.website_id = self.website_id
        return user
