from odoo import api, fields, models


class PortalWizard(models.TransientModel):
    _inherit = "portal.wizard"

    @api.depends("partner_ids")
    def _compute_user_ids(self):
        res = super()._compute_user_ids()
        for portal_wizard_user in self.user_ids:
            partner = portal_wizard_user.partner_id
            websites = partner.mapped("user_ids.website_id")
            portal_wizard_user.update(
                {
                    "had_user": bool(partner.user_ids),
                    "website_id": bool(websites) and websites[0].id,
                }
            )
        return res


class PortalWizardUser(models.TransientModel):
    _inherit = "portal.wizard.user"

    had_user = fields.Boolean()

    website_id = fields.Many2one(
        "website",
        string="Website",
        help="Empty means all websites",
    )

    def _create_user(self):
        user = super(PortalWizardUser, self)._create_user()
        user.website_id = self.website_id
        return user
