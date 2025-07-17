from odoo import models


class CustomerDedicatedGrantPortalAccessWizard(models.TransientModel):
    _inherit = "customer_team_manager.portal_access_wizard"

    def grant_portal_access(self):
        "Force the b2b website for users granted portal access by a customer admin"
        res = super().grant_portal_access()

        b2b_website_id = self.env.ref("website_sale_b2b.b2b_website").id
        self.customer_partners.filtered(
            lambda p: p.portal_status != "not_granted"
        ).user_ids.update({"website_id": b2b_website_id})

        return res
