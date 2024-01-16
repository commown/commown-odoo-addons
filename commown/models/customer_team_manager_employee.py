from odoo import models


class CustomerTeamManagerEmployee(models.Model):
    _inherit = "customer_team_manager.employee"

    def prepare_portal_wizard(self, in_portal):
        "Override to add the B2B website id as the employee user website"

        wizard = super().prepare_portal_wizard(in_portal)
        b2b_website_id = self.env.ref("website_sale_b2b.b2b_website").id
        wizard.user_ids.update({"website_id": b2b_website_id})
        return wizard
