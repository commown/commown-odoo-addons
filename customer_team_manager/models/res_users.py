from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model_create_multi
    def create(self, vals_list):
        "Add all customer roles to the first user of a company"

        result_multi = super().create(vals_list)

        for result in result_multi:
            if result.commercial_partner_id.is_company:
                if result.partner_id._is_the_only_company_user():
                    all_roles = self.env["customer_team_manager.customer_role"].search(
                        []
                    )
                    result.partner_id.customer_roles |= all_roles

        return result_multi
