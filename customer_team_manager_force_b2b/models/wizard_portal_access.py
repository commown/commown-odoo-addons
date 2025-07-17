from odoo import models


class CustomerDedicatedGrantPortalAccessWizard(models.TransientModel):
    _inherit = "customer_team_manager.portal_access_wizard"

    def _prepare_portal_wizard(self, partners):
        "Force the b2b website for users granted portal access by a customer admin"
        wizard = super()._prepare_portal_wizard(partners)
        b2b_website_id = self.env.ref("website_sale_b2b.b2b_website").id
        wizard.user_ids.update({"website_id": b2b_website_id})
        return wizard
